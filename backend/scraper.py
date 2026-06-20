"""
scraper.py - Core scraping module for fitgirl-repacks.site.
Uses requests + BeautifulSoup. No headless browser needed.
"""

import re
import os
import hashlib
import urllib.request
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import concurrent.futures
import threading
import time

from backend.config import BASE_URL, DATA_DIR, HEADERS, REQUEST_TIMEOUT, CACHE_TTL, CACHE_TTL_LONG
from backend import cache
from backend.catalog import requirements_service
from backend.catalog.title_matcher import compare_titles, normalize_title, title_tokens
from backend.official_sources import resolve_official_links

AZ_INDEX_CACHE_KEY = "arcadia_az_game_index"
AZ_INDEX_PROGRESS_KEY = "arcadia_az_game_index_progress"
AZ_INDEX_TTL = 30 * 24 * 60 * 60
AZ_PAGE_CACHE_PREFIX = "arcadia_az_page"
AZ_PAGE_TTL = 60 * 60
GAME_METADATA_OVERRIDES_KEY = "arcadia_game_metadata_overrides"
GAME_METADATA_OVERRIDES_TTL = AZ_INDEX_TTL
AZ_REFRESH_INTERVAL = 6 * 60 * 60
AZ_PAGE_SIZE = 48
AZ_INDEX_WORKERS = 6
COVER_WORKERS = 6
GALLERY_MEDIA_DIR = os.path.join(DATA_DIR, "gallery_media")
_index_lock = threading.Lock()
_index_job = {
    "running": False,
    "page": 0,
    "max_pages": 0,
    "total": 0,
    "message": "Not started",
    "updated_at": 0,
    "error": "",
    "done": False,
}

COVER_HYDRATE_PROGRESS_KEY = "arcadia_cover_hydrate_progress"
_cover_lock = threading.Lock()
_cover_job = {
    "running": False,
    "processed": 0,
    "total": 0,
    "updated": 0,
    "message": "Not started",
    "updated_at": 0,
    "error": "",
}

def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title


def _normalize_match_title(title: str) -> str:
    return normalize_title(title)
    title = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", title or "")
    title = re.sub(
        r"(?i)\b(build|v\d[\w.\-+]*|multi\d+|dlc|bonus|bonus(es)?|repack|deluxe|ultimate|edition|complete|digital|gold|goty|remaster(ed)?|remake|enhanced|definitive)\b",
        " ",
        title,
    )
    title = title.translate(str.maketrans({"™": " ", "®": " "}))
    title = title.replace(":", " ")
    title = re.sub(r"[^a-zA-Z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip().lower()


def _match_tokens(title: str) -> set[str]:
    return set(title_tokens(title))
    noise = {"a", "an", "and", "the", "of", "for", "with", "edition", "game"}
    return {token for token in _normalize_match_title(title).split() if token and token not in noise}


def _title_confidence(source: str, candidate: str) -> int:
    return compare_titles(source, candidate).score
    source_norm = _normalize_match_title(source)
    candidate_norm = _normalize_match_title(candidate)
    if not source_norm or not candidate_norm:
        return 0
    if source_norm == candidate_norm:
        return 100
    source_compact = re.sub(r"\s+", "", source_norm)
    candidate_compact = re.sub(r"\s+", "", candidate_norm)
    source_tokens = _match_tokens(source)
    candidate_tokens = _match_tokens(candidate)
    overlap = source_tokens & candidate_tokens
    if not overlap:
        return 0
    token_ratio = len(overlap) / max(1, min(len(source_tokens), len(candidate_tokens)))
    union_ratio = len(overlap) / max(1, len(source_tokens | candidate_tokens))
    compact_score = 0
    if len(source_compact) >= 8 and len(candidate_compact) >= 8:
        if source_compact in candidate_compact or candidate_compact in source_compact:
            compact_score = 32
        else:
            compact_score = int((1 - min(1, abs(len(source_compact) - len(candidate_compact)) / max(len(source_compact), len(candidate_compact)))) * 12)
    short_title = min(len(source_tokens), len(candidate_tokens)) <= 2
    required_ratio = 1.0 if short_title else 0.75
    if token_ratio < required_ratio:
        return 0
    return min(99, int(token_ratio * 46) + int(union_ratio * 22) + compact_score)


def _requirements_with_meta(reqs: dict | None, source: str, confidence: str = "high", status: str = "available") -> dict:
    return requirements_service.requirements_with_meta(reqs, source, confidence, status)
    value = dict(reqs or {})
    value["requirements_source"] = source
    value["requirements_confidence"] = confidence
    value["requirements_status"] = status
    value["requirements_checked_at"] = int(time.time())
    return value


def _title_bucket(title: str) -> str:
    cleaned = (title or "").strip()
    if not cleaned:
        return "0-9"
    ch = cleaned[0].lower()
    if "a" <= ch <= "z":
        return ch
    return "0-9"


def _game_bucket(game: dict) -> str:
    return _title_bucket(game.get("title", ""))


def _az_page_url(page: int) -> str:
    base = urljoin(BASE_URL, "all-my-repacks-a-z/")
    return base if page <= 1 else f"{base}?lcp_page0={page}#lcp_instance_0"


def _parse_az_page(page: int) -> dict:
    soup = _fetch(_az_page_url(page))
    content = soup.select_one(".entry-content") or soup
    games = []
    seen = set()
    for li in content.select("li"):
        a = li.select_one("a[href]")
        title = _clean_title(li.get_text(" ", strip=True))
        if not a or not title:
            continue
        href = urljoin(BASE_URL, a.get("href", ""))
        if "all-my-repacks-a-z" in href.lower() or re.fullmatch(r"\\d+|next page|previous page", title.lower()):
            continue
        slug = href.rstrip("/").split("/")[-1]
        key = slug or title.lower()
        if key in seen:
            continue
        seen.add(key)
        games.append({
            "title": title,
            "url": href,
            "slug": slug,
            "date": "",
            "category": "",
            "tags": [],
            "summary": "",
            "thumbnail": "",
            "source": "FitGirl Repacks",
            "letter": _title_bucket(title),
        })
    next_href = f"lcp_page0={page + 1}"
    has_next = bool(soup.select_one(f"a[href*=\"{next_href}\"]"))
    return {"page": page, "games": games, "has_next": has_next}


def _get_az_page(page: int, force: bool = False) -> dict:
    key = f"{AZ_PAGE_CACHE_PREFIX}_{page}"
    if not force:
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached
    result = _parse_az_page(page)
    cache.set(key, result, AZ_PAGE_TTL)
    return result


def _cache_gallery_image(slug: str, url: str) -> str:
    if not slug or not url or url.startswith(("/api/", "data:")):
        return url
    try:
        parsed = requests.utils.urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        safe_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", slug).strip("-") or "game"
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        folder = os.path.join(GALLERY_MEDIA_DIR, safe_slug)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, f"cover-{digest}{ext}")
        rel = os.path.relpath(target, DATA_DIR).replace("\\", "/")
        if os.path.exists(target):
            return f"/api/offline/media/{rel}"
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS.get("User-Agent", "Mozilla/5.0")})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read(6 * 1024 * 1024)
        with open(target, "wb") as f:
            f.write(data)
        return f"/api/offline/media/{rel}"
    except Exception:
        return url


def _is_cached_media(url: str) -> bool:
    return str(url or "").startswith("/api/offline/media/")


def _get_game_metadata_overrides() -> dict:
    data = cache.get(GAME_METADATA_OVERRIDES_KEY)
    return data if isinstance(data, dict) else {}


def _save_game_metadata_overrides(data: dict):
    cache.set(GAME_METADATA_OVERRIDES_KEY, data, GAME_METADATA_OVERRIDES_TTL)


def _update_cached_index_metadata(slug: str, fields: dict) -> bool:
    if not slug or not fields:
        return False
    index = _normalized_index(_get_cached_az_index())
    if not index:
        return False
    changed = False
    for game in index:
        if game.get("slug") != slug:
            continue
        for field, value in fields.items():
            if value not in (None, "") and game.get(field) != value:
                game[field] = value
                changed = True
    if changed:
        cache.set(AZ_INDEX_CACHE_KEY, index, AZ_INDEX_TTL)
    return changed


def _remember_game_artwork(slug: str, image: str, source: str = "Arcadia Catalog", update_index: bool = True) -> bool:
    if not slug or not image:
        return False
    overrides = _get_game_metadata_overrides()
    entry = dict(overrides.get(slug) or {})
    entry["thumbnail"] = image
    entry["cover"] = image
    entry["artwork_source"] = source
    entry["artwork_cached_at"] = int(time.time())
    overrides[slug] = entry
    _save_game_metadata_overrides(overrides)
    if update_index:
        _update_cached_index_metadata(slug, {"thumbnail": image, "cover": image})
    return True


def _remember_game_requirements(slug: str, reqs: dict, update_index: bool = True) -> bool:
    if not slug or not isinstance(reqs, dict):
        return False
    status = str(reqs.get("requirements_status") or "").lower()
    if reqs.get("pending") or status == "checking":
        return False
    stable_reqs = dict(reqs)
    stable_reqs.pop("pending", None)
    overrides = _get_game_metadata_overrides()
    entry = dict(overrides.get(slug) or {})
    entry["requirements"] = stable_reqs
    entry["requirements_cached_at"] = int(time.time())
    overrides[slug] = entry
    _save_game_metadata_overrides(overrides)
    if update_index:
        _update_cached_index_metadata(slug, {"requirements": stable_reqs})
    return True


def _apply_game_metadata_override(game: dict, overrides: dict | None = None) -> dict:
    item = dict(game or {})
    slug = item.get("slug")
    if not slug:
        return item
    entry = (overrides or _get_game_metadata_overrides()).get(slug)
    if not isinstance(entry, dict):
        return item

    cached_artwork = entry.get("thumbnail") or entry.get("cover")
    current_artwork = item.get("thumbnail") or item.get("cover")
    if cached_artwork and (not current_artwork or _is_cached_media(cached_artwork) or not _is_cached_media(current_artwork)):
        item["thumbnail"] = cached_artwork
        item["cover"] = entry.get("cover") or cached_artwork
        if entry.get("artwork_source"):
            item["artwork_source"] = entry["artwork_source"]

    cached_requirements = entry.get("requirements")
    if isinstance(cached_requirements, dict):
        current_requirements = item.get("requirements") or {}
        current_status = str(current_requirements.get("requirements_status") or "").lower()
        if (
            not requirements_service.has_real_requirements(current_requirements)
            or current_requirements.get("pending")
            or current_status in {"", "checking", "unavailable"}
        ):
            item["requirements"] = dict(cached_requirements)
    return item


def _merge_game_metadata_overrides(games: list[dict]) -> list[dict]:
    overrides = _get_game_metadata_overrides()
    if not overrides:
        return [dict(game or {}) for game in games]
    return [_apply_game_metadata_override(game, overrides) for game in games]


def prepare_card_games(games: list[dict], include_requirements: bool = False) -> list[dict]:
    prepared = _merge_game_metadata_overrides(games or [])
    if include_requirements:
        prepared = [{**game, "requirements": _display_requirements(game)} for game in prepared]
    return prepared


def _get_page_cover_only(slug: str) -> str:
    """Fetch only the page artwork without doing full detail/requirements work."""
    if not slug:
        return ""
    try:
        soup = _fetch(f"{BASE_URL}{slug}/")
        content = soup.select_one(".entry-content")
        if content:
            return _best_page_image(soup, content)
    except Exception:
        return ""
    return ""


def _set_index_progress(**kwargs):
    with _index_lock:
        _index_job.update(kwargs)
        _index_job["updated_at"] = time.time()
        cache.set(AZ_INDEX_PROGRESS_KEY, dict(_index_job), AZ_INDEX_TTL)


def _get_cached_az_index() -> list:
    cached = cache.get(AZ_INDEX_CACHE_KEY)
    if isinstance(cached, list):
        return cached
    return []


def _sort_key(game: dict) -> str:
    return (game.get("title", "") or "").lower()


def _normalized_index(index: list[dict]) -> list[dict]:
    changed = False
    normalized = []
    for game in index:
        item = dict(game)
        bucket = _game_bucket(item)
        if item.get("letter") != bucket:
            item["letter"] = bucket
            changed = True
        normalized.append(item)
    normalized.sort(key=_sort_key)
    normalized = _merge_game_metadata_overrides(normalized)
    if changed:
        cache.set(AZ_INDEX_CACHE_KEY, normalized, AZ_INDEX_TTL)
    return normalized


def _bucket_rank(bucket: str) -> int:
    if bucket == "0-9":
        return 0
    if bucket and len(bucket) == 1 and "a" <= bucket <= "z":
        return ord(bucket) - ord("a") + 1
    return 0


def _collect_letter_from_source(letter: str, page: int, page_size: int, max_pages: int = 140) -> dict:
    """Cold-cache fallback that scans enough A-Z source pages for any letter."""
    collected = []
    has_next = True
    source_page = 1
    target_count = page * page_size
    target_rank = _bucket_rank(letter)
    passed_target = False

    while source_page <= max_pages and has_next:
        direct = _get_az_page(source_page)
        games = direct.get("games", [])
        for game in games:
            bucket = _game_bucket(game)
            if bucket == letter:
                collected.append(game)
            elif collected and _bucket_rank(bucket) > target_rank:
                passed_target = True
        has_next = bool(direct.get("has_next"))
        if len(collected) >= target_count and (passed_target or not has_next):
            break
        if collected and passed_target:
            break
        source_page += 1

    return {
        "games": collected,
        "has_next_source": has_next and not passed_target,
        "source_page": source_page,
    }


def _merge_games(indexed: list[dict], seen: set[str], games: list[dict]) -> int:
    added = 0
    by_key = {
        game.get("slug") or game.get("url") or game.get("title", "").lower(): game
        for game in indexed
    }
    for game in games:
        key = game.get("slug") or game.get("url") or game.get("title", "").lower()
        if not key:
            continue
        if key in by_key:
            existing = by_key[key]
            for field in ("title", "url", "source", "category", "date", "summary"):
                if game.get(field):
                    existing[field] = game[field]
            existing["letter"] = _game_bucket(existing)
            if not existing.get("thumbnail") and game.get("thumbnail"):
                existing["thumbnail"] = game["thumbnail"]
            continue
        game["letter"] = _game_bucket(game)
        indexed.append(game)
        by_key[key] = game
        seen.add(key)
        added += 1
    indexed.sort(key=_sort_key)
    return added


def _build_az_index(max_pages: int = 140, force: bool = False):
    if not force and _get_cached_az_index():
        _set_index_progress(running=False, done=True, message="Catalog index is already cached", total=len(_get_cached_az_index()))
        return
    indexed = list(_get_cached_az_index()) if force else []
    seen = {game.get("slug") or game.get("url") or game.get("title", "").lower() for game in indexed}
    _set_index_progress(running=True, done=False, page=0, max_pages=max_pages, total=len(indexed), error="", message="Starting catalog refresh" if force else "Starting catalog index")
    try:
        for start_page in range(1, max_pages + 1, AZ_INDEX_WORKERS):
            pages = list(range(start_page, min(max_pages, start_page + AZ_INDEX_WORKERS - 1) + 1))
            _set_index_progress(page=pages[-1], message=f"Scraping A-Z pages {pages[0]}-{pages[-1]}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(AZ_INDEX_WORKERS, len(pages))) as executor:
                results = list(executor.map(lambda page: _get_az_page(page, force=force), pages))
            results.sort(key=lambda item: item.get("page", 0))
            added = 0
            empty_tail = 0
            for result in results:
                page_games = result.get("games", [])
                if page_games:
                    empty_tail = 0
                    added += _merge_games(indexed, seen, page_games)
                else:
                    empty_tail += 1
            cache.set(AZ_INDEX_CACHE_KEY, indexed, AZ_INDEX_TTL)
            _set_index_progress(total=len(indexed), message=f"Indexed {len(indexed)} games (+{added})")
            last_result = results[-1] if results else {}
            if empty_tail >= 2 or (pages[-1] > 1 and not last_result.get("has_next")):
                break
        _set_index_progress(running=False, done=True, total=len(indexed), message=f"Indexed {len(indexed)} games")
    except Exception as exc:
        _set_index_progress(running=False, done=False, error=str(exc), message="Catalog indexing failed")


def start_library_index(force: bool = False, max_pages: int = 140) -> dict:
    should_start = False
    refresh_force = force
    with _index_lock:
        if _index_job.get("running"):
            return dict(_index_job)
        cached = _get_cached_az_index()
        if cached and not force:
            _index_job.update({
                "running": False,
                "done": True,
                "page": _index_job.get("page", 0),
                "max_pages": max_pages,
                "total": len(cached),
                "message": "Catalog index is cached",
                "error": "",
                "updated_at": time.time(),
            })
            return dict(_index_job)
        else:
            _index_job.update({
                "running": True,
                "done": False,
                "page": 0,
                "max_pages": max_pages,
                "total": 0,
                "message": "Catalog indexing queued",
                "error": "",
                "updated_at": time.time(),
            })
            should_start = True
    if not should_start:
        return get_library_index_status()
    thread = threading.Thread(target=_build_az_index, kwargs={"max_pages": max_pages, "force": refresh_force}, daemon=True)
    thread.start()
    return get_library_index_status()



def _set_cover_progress(**kwargs):
    with _cover_lock:
        _cover_job.update(kwargs)
        _cover_job["updated_at"] = time.time()
        cache.set(COVER_HYDRATE_PROGRESS_KEY, dict(_cover_job), AZ_INDEX_TTL)


def get_cover_hydration_status() -> dict:
    cached = cache.get(COVER_HYDRATE_PROGRESS_KEY) or {}
    index = _normalized_index(_get_cached_az_index())
    cached_count = len([game for game in index if game.get("thumbnail") or game.get("cover")])
    with _cover_lock:
        status = {**cached, **_cover_job}
    status["cached"] = cached_count
    status["indexed"] = len(index)
    status["percent"] = round((cached_count / len(index)) * 100) if index else 0
    return status


def _hydrate_cover_batch(limit: int = 36, slugs: list[str] | None = None):
    index = _normalized_index(_get_cached_az_index())
    requested = {str(slug).strip() for slug in (slugs or []) if str(slug).strip()}
    visible_pending = [
        game for game in index
        if game.get("slug") in requested and not _is_cached_media(game.get("thumbnail") or game.get("cover"))
    ]
    other_pending = [
        game for game in index
        if game.get("slug") and not _is_cached_media(game.get("thumbnail") or game.get("cover")) and game.get("slug") not in requested
    ]
    if requested:
        by_slug = {game.get("slug"): game for game in index}
        pending = visible_pending[:limit]
        for slug in requested:
            if slug not in by_slug:
                pending.append({"slug": slug, "thumbnail": ""})
        pending = pending[:limit]
    else:
        pending = (visible_pending + other_pending)[:limit]
    if not pending:
        _set_cover_progress(running=False, processed=0, total=0, updated=0, message="Game artwork is up to date", error="")
        return
    _set_cover_progress(running=True, processed=0, total=len(pending), updated=0, message="Loading game artwork", error="")
    updated = 0
    by_slug = {game.get("slug"): game for game in index}
    def _load(game):
        try:
            cover = _get_page_cover_only(game["slug"])
            if cover:
                return game["slug"], _cache_gallery_image(game["slug"], cover)
        except Exception:
            return game.get("slug"), ""
        return game.get("slug"), ""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(COVER_WORKERS, len(pending))) as executor:
            for processed, result in enumerate(executor.map(_load, pending), start=1):
                slug, cover = result
                if cover and slug in by_slug:
                    by_slug[slug]["thumbnail"] = cover
                    by_slug[slug]["cover"] = cover
                    _remember_game_artwork(slug, cover, update_index=False)
                    updated += 1
                _set_cover_progress(processed=processed, updated=updated, message=f"Loaded artwork for {updated} games")
        cache.set(AZ_INDEX_CACHE_KEY, index, AZ_INDEX_TTL)
        _set_cover_progress(running=False, processed=len(pending), total=len(pending), updated=updated, message=f"Loaded artwork for {updated} games", error="")
    except Exception as exc:
        _set_cover_progress(running=False, error=str(exc), message="Artwork loading failed")


def start_cover_hydration(limit: int = 36, slugs: list[str] | None = None) -> dict:
    with _cover_lock:
        if _cover_job.get("running"):
            return dict(_cover_job)
        _cover_job.update({"running": True, "processed": 0, "total": 0, "updated": 0, "message": "Artwork loading queued", "error": "", "updated_at": time.time()})
    threading.Thread(target=_hydrate_cover_batch, kwargs={"limit": limit, "slugs": slugs or []}, daemon=True).start()
    return get_cover_hydration_status()


def hydrate_visible_artwork(slugs: list[str], limit: int = 24) -> dict:
    """Fetch artwork for the currently visible gallery page and return it."""
    clean_slugs = []
    for slug in slugs or []:
        value = str(slug or "").strip()
        if value and value not in clean_slugs:
            clean_slugs.append(value)
    clean_slugs = clean_slugs[: max(1, min(48, int(limit or 24)))]
    if not clean_slugs:
        return {"artwork": {}}

    index = _normalized_index(_get_cached_az_index())
    by_slug = {game.get("slug"): game for game in index if game.get("slug")}
    results: dict[str, str] = {}
    meta: dict[str, dict] = {}

    def _load(slug: str) -> tuple[str, str, str]:
        game = by_slug.get(slug) or {}
        cached = game.get("thumbnail") or game.get("cover")
        if cached:
            if _is_cached_media(cached):
                return slug, cached, "cached"
            return slug, _cache_gallery_image(slug, cached), "cached-source"
        cover = _get_page_cover_only(slug)
        return slug, _cache_gallery_image(slug, cover) if cover else "", "source-page" if cover else "missing"

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(clean_slugs))) as executor:
        for slug, cover, source in executor.map(_load, clean_slugs):
            if cover:
                results[slug] = cover
                meta[slug] = {"source": source, "cached": _is_cached_media(cover)}
                _remember_game_artwork(slug, cover, update_index=False)
                if slug in by_slug:
                    by_slug[slug]["thumbnail"] = cover
                    by_slug[slug]["cover"] = cover
                else:
                    _update_cached_index_artwork(slug, cover)

    if results and index:
        cache.set(AZ_INDEX_CACHE_KEY, index, AZ_INDEX_TTL)
    return {"artwork": results, "meta": meta}

def get_library_index_status() -> dict:
    cached_progress = cache.get(AZ_INDEX_PROGRESS_KEY) or {}
    cached_index = _normalized_index(_get_cached_az_index())
    with _index_lock:
        status = {**cached_progress, **_index_job}
    status["total"] = max(int(status.get("total") or 0), len(cached_index))
    status["cached"] = bool(cached_index)
    status["artwork_cached"] = len([g for g in cached_index if g.get("thumbnail") or g.get("cover")])
    status["letters"] = sorted({_game_bucket(g) for g in cached_index})
    return status

def _image_url(img) -> str:
    if not img:
        return ""
    for attr in ("data-src", "data-lazy-src", "data-original", "data-full-url", "data-large-file", "data-medium-file", "src"):
        value = img.get(attr, "")
        if value:
            return value
    srcset = img.get("data-srcset", "") or img.get("srcset", "")
    if srcset:
        candidates = [part.strip().split(" ", 1)[0] for part in srcset.split(",") if part.strip()]
        if candidates:
            return candidates[-1]
    return ""


def _is_site_logo(url: str, alt: str = "") -> bool:
    value = f"{url} {alt}".lower()
    blocked = (
        "cropped-icon",
        "fitgirl",
        "logo",
        "avatar",
        "favicon",
        "blank",
        "placeholder",
        "spacer",
        "loader",
        "transparent",
        "gravatar",
    )
    return not url or any(token in value for token in blocked)


def _image_candidate_score(url: str, img=None, source: str = "content") -> int:
    if not url or _is_site_logo(url, img.get("alt", "") if img else ""):
        return -100
    parsed = requests.utils.urlparse(url)
    path = parsed.path.lower()
    if path and not re.search(r"\.(jpe?g|png|webp|gif)$", path):
        return -15
    text = " ".join([
        source,
        path,
        img.get("alt", "") if img else "",
        " ".join(img.get("class", [])) if img and isinstance(img.get("class"), list) else "",
        img.get("title", "") if img else "",
    ]).lower()
    score = 0
    if source == "meta":
        score += 75
    if source == "linked-image":
        score += 35
    if any(token in text for token in ("cover", "poster", "box", "vertical", "portrait", "game-box", "featured")):
        score += 45
    if any(token in text for token in ("screenshot", "screen", "gallery", "thumb")):
        score += 12
    if any(token in text for token in ("button", "banner", "repack", "setup", "download")):
        score -= 20
    try:
        width = int(str(img.get("width") or "0").strip() or 0) if img else 0
        height = int(str(img.get("height") or "0").strip() or 0) if img else 0
        if width >= 250 and height >= 250:
            score += 20
        if height > width:
            score += 18
        if width > height * 2:
            score -= 12
    except (TypeError, ValueError):
        pass
    return score


def _best_page_image(soup, content) -> str:
    candidates: list[tuple[int, int, str]] = []
    order = 0

    for selector in (
        'meta[property="og:image"]',
        'meta[property="og:image:secure_url"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
    ):
        meta = soup.select_one(selector) if soup else None
        url = meta.get("content", "") if meta else ""
        if url and not _is_site_logo(url):
            candidates.append((_image_candidate_score(url, None, "meta"), order, urljoin(BASE_URL, url)))
            order += 1
    if not content:
        candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return candidates[0][2] if candidates else ""

    for img in content.select("img"):
        url = _image_url(img)
        if not _is_site_logo(url, img.get("alt", "")):
            candidates.append((_image_candidate_score(url, img, "content"), order, urljoin(BASE_URL, url)))
            order += 1
        parent = img.find_parent("a")
        href = parent.get("href", "") if parent else ""
        if href and re.search(r"\.(jpe?g|png|webp|gif)(?:[?#].*)?$", href, re.I) and not _is_site_logo(href, img.get("alt", "")):
            candidates.append((_image_candidate_score(href, img, "linked-image"), order, urljoin(BASE_URL, href)))
            order += 1

    seen = set()
    unique = []
    for score, idx, url in candidates:
        key = url.split("?", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        unique.append((score, idx, url))
    unique.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return unique[0][2] if unique else ""


def _update_cached_index_artwork(slug: str, image: str) -> bool:
    if not slug or not image:
        return False
    _remember_game_artwork(slug, image, update_index=False)
    return _update_cached_index_metadata(slug, {"thumbnail": image, "cover": image})


def _fetch(url: str) -> BeautifulSoup:
    """Fetch a URL and return parsed BeautifulSoup object."""
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def _parse_article_card(article) -> dict | None:
    """Parse a single <article> element from search results or homepage."""
    title_el = article.select_one(".entry-title a")
    if not title_el:
        return None

    url = title_el.get("href", "")
    slug = url.rstrip("/").split("/")[-1] if url else ""

    # Date
    time_el = article.select_one("time.entry-date")
    date = time_el.get("datetime", "") if time_el else ""

    # Category
    cat_el = article.select_one(".cat-links a")
    category = cat_el.get_text(strip=True) if cat_el else ""

    # Tags
    tag_els = article.select(".tag-links a")
    tags = [t.get_text(strip=True) for t in tag_els]

    # Summary
    summary_el = article.select_one(".entry-summary p, .entry-content p")
    summary = ""
    if summary_el:
        summary = summary_el.get_text(strip=True)
        # Remove Continue reading suffix
        summary = re.sub(r"Continue reading.*$", "", summary).strip()

    # Thumbnail
    thumbnail = ""
    img_el = article.select_one(".entry-content img, .entry-summary img")
    if img_el:
        thumbnail = _image_url(img_el)
        if _is_site_logo(thumbnail, img_el.get("alt", "")):
            thumbnail = ""

    return {
        "title": title_el.get_text(strip=True),
        "url": url,
        "slug": slug,
        "date": date,
        "category": category,
        "tags": tags,
        "summary": summary,
        "thumbnail": thumbnail,
    }


def _extract_size_info(text: str) -> dict:
    """Extract original and repack sizes from game page text."""
    info = {"original_size": "", "repack_size": ""}

    orig_match = re.search(
        r"Original Size:\s*(?:<[^>]+>)?\s*([\d.,]+\s*[GMKT]B)",
        text, re.IGNORECASE
    )
    repack_match = re.search(
        r"Repack Size:\s*(?:<[^>]+>)?\s*(?:from\s+)?([\d.,]+\s*[GMKT]B)",
        text, re.IGNORECASE
    )

    if orig_match:
        info["original_size"] = orig_match.group(1).strip()
    if repack_match:
        info["repack_size"] = repack_match.group(1).strip()
    return info


def _html_to_requirement_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "lxml")
    return soup.get_text("\n", strip=True)


def _extract_req_value(text: str, names: tuple[str, ...]) -> str:
    escaped = "|".join(re.escape(name) for name in names)
    match = re.search(rf"(?:{escaped})\s*:?\s*([^\n\r]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip(" -:")


def _parse_requirements_text(text: str) -> dict:
    return requirements_service.parse_requirements_text(text)
    reqs = {"ram_min": 0, "ram_rec": 0, "space": 0, "cpu": "", "gpu": ""}
    if not text:
        return reqs

    ram_matches = re.findall(r"(?:Memory|RAM)\s*:?\s*(\d+(?:\.\d+)?)\s*GB", text, re.IGNORECASE)
    if not ram_matches:
        ram_matches = re.findall(r"(\d+(?:\.\d+)?)\s*GB\s*(?:RAM|Memory)", text, re.IGNORECASE)
    if ram_matches:
        reqs["ram_min"] = int(float(ram_matches[0]))
        reqs["ram_rec"] = int(float(ram_matches[1])) if len(ram_matches) > 1 else reqs["ram_min"]

    storage_match = re.search(
        r"(?:Storage|Disk Space|Free Space|Installation Space)\s*:?\s*(?:up to\s*)?(?:about\s*)?(\d+(?:\.\d+)?)\s*GB",
        text,
        re.IGNORECASE,
    )
    if storage_match:
        reqs["space"] = int(float(storage_match.group(1)))

    reqs["cpu"] = _extract_req_value(text, ("Processor", "CPU"))
    reqs["gpu"] = _extract_req_value(text, ("Graphics", "Video Card", "GPU"))
    return reqs


@cache.cached(ttl=CACHE_TTL_LONG)
def _fetch_steam_requirements(title: str, steam_page: str = "") -> dict:
    return requirements_service.fetch_steam_requirements(title, steam_page)
    """Fetch Steam PC requirements only when the store title matches confidently."""
    normalized = _normalize_match_title(title)
    if not normalized:
        return {}
    app_id = ""
    page_match = re.search(r"store\.steampowered\.com/app/(\d+)", steam_page or "")
    if page_match:
        app_id = page_match.group(1)
    else:
        try:
            search = requests.get(
                "https://store.steampowered.com/api/storesearch/",
                params={"term": normalized, "cc": "us", "l": "en"},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            search.raise_for_status()
            items = (search.json() or {}).get("items") or []
            for item in items[:5]:
                if _title_confidence(title, item.get("name", "")) >= 88:
                    app_id = str(item.get("id") or "")
                    break
        except Exception:
            return {}
    if not app_id:
        return {}

    try:
        details = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": app_id, "filters": "basic,pc_requirements", "cc": "us", "l": "en"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        details.raise_for_status()
        payload = (details.json() or {}).get(str(app_id), {})
        data = payload.get("data") or {}
        steam_name = (data.get("basic") or {}).get("name", "")
        if steam_name and _title_confidence(title, steam_name) < 88:
            return {}
        pc = data.get("pc_requirements") or {}
        minimum = _html_to_requirement_text(pc.get("minimum", ""))
        recommended = _html_to_requirement_text(pc.get("recommended", ""))
        combined = "\n".join(part for part in (minimum, recommended) if part)
        reqs = _parse_requirements_text(combined)
        if any([reqs.get("ram_min"), reqs.get("ram_rec"), reqs.get("cpu"), reqs.get("gpu")]):
            reqs["steam_page"] = f"https://store.steampowered.com/app/{app_id}/"
            return _requirements_with_meta(reqs, "Steam", "high", "available")
    except Exception:
        return {}
    return {}


@cache.cached(ttl=CACHE_TTL_LONG)
def _fetch_pcgamingwiki_requirements(title: str) -> dict:
    return requirements_service.fetch_pcgamingwiki_requirements(title)
    """Best-effort no-key PCGamingWiki requirements fallback for confident title matches."""
    normalized = _normalize_match_title(title)
    if not normalized:
        return {}
    try:
        search = requests.get(
            "https://www.pcgamingwiki.com/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": normalized,
                "format": "json",
                "utf8": 1,
                "srlimit": 5,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        search.raise_for_status()
        results = (search.json() or {}).get("query", {}).get("search") or []
        page_title = ""
        for item in results:
            candidate = item.get("title", "")
            if _title_confidence(title, candidate) >= 90:
                page_title = candidate
                break
        if not page_title:
            return {}
        page = requests.get(
            "https://www.pcgamingwiki.com/w/api.php",
            params={
                "action": "parse",
                "page": page_title,
                "prop": "wikitext",
                "format": "json",
                "utf8": 1,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        page.raise_for_status()
        wikitext = ((page.json() or {}).get("parse", {}).get("wikitext", {}) or {}).get("*", "")
        if not wikitext:
            return {}
        reqs = _parse_requirements_text(wikitext.replace("|", "\n").replace("=", ":"))
        if any([reqs.get("ram_min"), reqs.get("ram_rec"), reqs.get("cpu"), reqs.get("gpu")]):
            reqs["pcgamingwiki_page"] = f"https://www.pcgamingwiki.com/wiki/{quote_plus(page_title.replace(' ', '_'))}"
            return _requirements_with_meta(reqs, "PCGamingWiki", "medium", "available")
    except Exception:
        return {}
    return {}


def _display_requirements(game: dict | None = None) -> dict:
    return requirements_service.display_requirements(game)
    reqs = dict((game or {}).get("requirements") or {})
    has_real = any([
        int(reqs.get("ram_min") or 0) > 0,
        int(reqs.get("ram_rec") or 0) > 0,
        str(reqs.get("gpu") or "").strip(),
        str(reqs.get("cpu") or "").strip(),
    ])
    if has_real:
        reqs.setdefault("requirements_source", "Source Page")
        reqs.setdefault("requirements_confidence", "high")
        reqs.setdefault("requirements_status", "available")
        reqs.setdefault("requirements_checked_at", int(time.time()))
        return reqs
    return _requirements_with_meta({"pending": True}, "Arcadia", "low", "checking")


def hydrate_requirements(slugs: list[str], limit: int = 24) -> dict:
    """Fetch accurate requirements for visible gallery rows."""
    clean_slugs = []
    for slug in slugs or []:
        value = str(slug or "").strip()
        if value and value not in clean_slugs:
            clean_slugs.append(value)
    clean_slugs = clean_slugs[: max(1, min(48, int(limit or 24)))]
    index = _normalized_index(_get_cached_az_index())
    by_slug = {game.get("slug"): game for game in index if game.get("slug")}
    results = {}

    def _load(slug: str) -> tuple[str, dict]:
        existing = _display_requirements(by_slug.get(slug) or {})
        if not existing.get("pending"):
            return slug, existing
        details = get_game_details(slug) or {}
        display = requirements_service.resolve_requirements(
            details.get("title") or slug,
            details.get("requirements") or {},
            details.get("steam_page", ""),
        )
        return slug, display

    if clean_slugs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(clean_slugs))) as executor:
            for slug, reqs in executor.map(_load, clean_slugs):
                results[slug] = reqs
                if not reqs.get("pending"):
                    _remember_game_requirements(slug, reqs, update_index=False)
                if slug in by_slug and not reqs.get("pending"):
                    by_slug[slug]["requirements"] = reqs
                    if not by_slug[slug].get("thumbnail") and (by_slug[slug].get("cover") or by_slug[slug].get("thumbnail")):
                        by_slug[slug]["thumbnail"] = by_slug[slug].get("cover") or by_slug[slug].get("thumbnail")
        if index:
            cache.set(AZ_INDEX_CACHE_KEY, index, AZ_INDEX_TTL)

    return {"requirements": results}


@cache.cached(ttl=CACHE_TTL)
def search_games(query: str, page: int = 1) -> dict:
    """Search games on the site."""
    url = f"{BASE_URL}?s={quote_plus(query)}"
    if page > 1:
        url = f"{BASE_URL}page/{page}/?s={quote_plus(query)}"

    soup = _fetch(url)
    articles = soup.select("article")
    games = []
    for article in articles:
        card = _parse_article_card(article)
        if card:
            games.append(card)

    # Populate actual cover images in parallel
    def _populate_thumbnail(game):
        try:
            details = get_game_details(game["slug"])
            if details and details.get("cover"):
                game["thumbnail"] = details["cover"]
        except Exception:
            pass

    if games:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(games), 12)) as executor:
            list(executor.map(_populate_thumbnail, games))

    # Check for pagination
    has_next = bool(soup.select_one(".nav-links .nav-previous a, .pagination .next"))

    return {
        "query": query,
        "page": page,
        "games": games,
        "has_next": has_next,
        "has_prev": page > 1,
    }


def _merge_latest_to_index(games: list[dict]):
    if not games:
        return
    index = _get_cached_az_index()
    if not index:
        return
    seen = {game.get("slug") or game.get("url") or game.get("title", "").lower() for game in index}
    added = _merge_games(index, seen, games)
    if added > 0:
        cache.set(AZ_INDEX_CACHE_KEY, index, AZ_INDEX_TTL)
        _set_index_progress(total=len(index), message=f"Merged {added} new releases from homepage")


@cache.cached(ttl=CACHE_TTL)
def get_latest_repacks(page: int = 1) -> dict:
    """Get latest repacks from the homepage."""
    url = BASE_URL
    if page > 1:
        url = f"{BASE_URL}page/{page}/"

    soup = _fetch(url)
    articles = soup.select("article")
    games = []
    for article in articles:
        card = _parse_article_card(article)
        if card:
            games.append(card)

    # Populate actual cover images in parallel
    def _populate_thumbnail(game):
        try:
            details = get_game_details(game["slug"])
            if details and details.get("cover"):
                game["thumbnail"] = details["cover"]
        except Exception:
            pass

    if games:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(games), 12)) as executor:
            list(executor.map(_populate_thumbnail, games))

    if page == 1 and games:
        try:
            threading.Thread(target=_merge_latest_to_index, args=(games,), daemon=True).start()
        except Exception:
            pass

    next_link = soup.select_one(".nav-links .nav-previous a")
    has_next = bool(next_link)

    return {
        "page": page,
        "games": games,
        "has_next": has_next,
        "has_prev": page > 1,
    }


def get_games_library(letter: str = "all", page: int = 1, page_size: int = AZ_PAGE_SIZE) -> dict:
    """Return a paged A-Z library view backed by the full A-Z index."""
    letter = (letter or "all").strip().lower()
    page = max(1, int(page or 1))
    page_size = max(12, min(96, int(page_size or AZ_PAGE_SIZE)))
    valid_letters = {"all", "0-9", "#", *list("abcdefghijklmnopqrstuvwxyz")}
    if letter not in valid_letters:
        letter = "all"

    index = _normalized_index(_get_cached_az_index())
    progress = get_library_index_status()
    if not index:
        progress = start_library_index(force=False)
        collected = []
        if letter == "all":
            direct = _get_az_page(page)
            collected = direct.get("games", [])
            has_next = bool(direct.get("has_next"))
        else:
            direct = _collect_letter_from_source(letter, page, page_size)
            collected = direct.get("games", [])
            has_next = bool(direct.get("has_next_source"))
        total = len(collected)
        start = (page - 1) * page_size
        games = prepare_card_games(collected[start:start + page_size], include_requirements=True)
        return {
            "letter": letter,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "games": games,
            "has_next": bool(has_next or start + page_size < total),
            "has_prev": page > 1,
            "indexing": progress,
            "artwork": get_cover_hydration_status(),
        }

    filtered = index if letter == "all" else [g for g in index if _game_bucket(g) == letter]
    total = len(filtered)
    if letter == "all" and total < page * page_size:
        direct = _get_az_page(page)
        direct_games = direct.get("games", [])
        if direct_games:
            return {
                "letter": letter,
                "page": page,
                "page_size": page_size,
                "total": max(total, page * page_size),
                "total_pages": max(page + (1 if direct.get("has_next") else 0), 1),
                "games": prepare_card_games(direct_games[:page_size], include_requirements=True),
                "has_next": bool(direct.get("has_next")),
                "has_prev": page > 1,
                "indexing": progress,
                "artwork": get_cover_hydration_status(),
            }
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    start = (page - 1) * page_size
    games = prepare_card_games(filtered[start:start + page_size], include_requirements=True)
    return {
        "letter": letter,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "games": games,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "indexing": progress,
        "artwork": get_cover_hydration_status(),
    }

def get_game_details(slug: str, force_refresh: bool = False) -> dict | None:
    """Get full details for a specific game by its URL slug."""
    key = f"get_game_details:{slug}"
    if not force_refresh:
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

    url = f"{BASE_URL}{slug}/"
    try:
        soup = _fetch(url)
    except requests.HTTPError:
        return None

    article = soup.select_one("article")
    if not article:
        return None

    # Basic Info
    title_el = article.select_one(".entry-title")
    title = title_el.get_text(strip=True) if title_el else ""

    time_el = article.select_one("time.entry-date")
    date = time_el.get("datetime", "") if time_el else ""

    cat_els = article.select(".entry-meta .cat-links a")
    categories = [c.get_text(strip=True) for c in cat_els]

    tag_els = article.select("footer .tag-links a, .entry-meta .tag-links a")
    tags = list(dict.fromkeys(t.get_text(strip=True) for t in tag_els))  # Dedupe

    # Content Parsing
    content = article.select_one(".entry-content")
    content_html = str(content) if content else ""
    content_text = content.get_text("\n", strip=True) if content else ""

    # Cover image
    cover = ""
    if content:
        cover = _best_page_image(soup, content)
        if cover:
            cached_cover = _cache_gallery_image(slug, cover)
            _update_cached_index_artwork(slug, cached_cover)
            cover = cached_cover

    # Sizes
    sizes = _extract_size_info(content_html)

    # Parse System Requirements
    req_ram_min = 0
    req_ram_rec = 0
    req_space = 0
    req_cpu = ""
    req_gpu = ""

    if content_text:
        # Check RAM: "Minimum RAM: 8 GB" or "8 GB RAM" or "RAM: 8 GB"
        ram_matches = re.findall(r"(?:RAM|Memory):\s*(?:minimum\s+)?(?:of\s+)?(\d+)\s*GB", content_text, re.IGNORECASE)
        if ram_matches:
            req_ram_min = int(ram_matches[0])
            if len(ram_matches) > 1:
                req_ram_rec = int(ram_matches[1])
            else:
                req_ram_rec = req_ram_min
        else:
            ram_alt = re.findall(r"(\d+)\s*GB\s*RAM", content_text, re.IGNORECASE)
            if ram_alt:
                req_ram_min = int(ram_alt[0])
                if len(ram_alt) > 1:
                    req_ram_rec = int(ram_alt[1])
                else:
                    req_ram_rec = req_ram_min

        # Check Space: "Disk Space:\s*(\d+)\s*GB" or "Free Space: \d+ GB"
        space_match = re.search(r"(?:Disk Space|Free Space|Installation Space):\s*(?:up\s+to\s+)?(?:about\s+)?(\d+(?:\.\d+)?)\s*GB", content_text, re.IGNORECASE)
        if space_match:
            req_space = int(float(space_match.group(1)))
        else:
            orig_match = re.search(r"Original Size:\s*(?:from\s*)?(\d+(?:\.\d+)?)\s*GB", content_text, re.IGNORECASE)
            if orig_match:
                req_space = int(float(orig_match.group(1)))
            else:
                rep_match = re.search(r"Repack Size:\s*(?:from\s*)?(\d+(?:\.\d+)?)\s*GB", content_text, re.IGNORECASE)
                if rep_match:
                    req_space = int(float(rep_match.group(1)))

    # Parse CPU and GPU strings for display
    cpu_match = re.search(r"(?:Processor|CPU):\s*([^\n]+)", content_text, re.IGNORECASE)
    if cpu_match:
        req_cpu = cpu_match.group(1).strip()

    gpu_match = re.search(r"(?:Graphics|Video Card|GPU):\s*([^\n]+)", content_text, re.IGNORECASE)
    if gpu_match:
        req_gpu = gpu_match.group(1).strip()

    # Genres
    genres_match = re.search(r"Genres/Tags:\s*(.*?)(?:\n|Companies:)", content_text)
    genres = genres_match.group(1).strip() if genres_match else ", ".join(tags)

    # Companies
    companies_match = re.search(r"Companies:\s*(.*?)(?:\n|Languages:)", content_text)
    companies = companies_match.group(1).strip() if companies_match else ""

    # Languages
    lang_match = re.search(r"Languages:\s*(.*?)(?:\n|Original Size:)", content_text)
    languages = lang_match.group(1).strip() if lang_match else ""

    # Download Links
    direct_links = []
    torrent_links = []
    magnet_link = ""

    if content:
        for h3 in content.select("h3"):
            h3_text = h3.get_text()

            # Direct download links
            if "Direct Links" in h3_text:
                ul = h3.find_next_sibling("ul")
                if ul:
                    for li in ul.select("li"):
                        a = li.select_one("a")
                        if a:
                            direct_links.append({
                                "name": a.get_text(strip=True),
                                "url": a.get("href", ""),
                            })

            # Torrent links
            if "Torrent" in h3_text:
                ul = h3.find_next_sibling("ul")
                if ul:
                    for a in ul.select("a"):
                        href = a.get("href", "")
                        text = a.get_text(strip=True)
                        if href.startswith("magnet:"):
                            magnet_link = href
                            torrent_links.append({"name": "Magnet Link", "url": href})
                        elif any(s in href for s in ["1337x", "tapochek", "rutor"]):
                            torrent_links.append({"name": text, "url": href})
                        elif "torrent file" in text.lower() or ".torrent" in text.lower():
                            torrent_links.append({"name": text, "url": href})

    # Screenshots
    screenshots = []
    if content:
        for h3 in content.select("h3"):
            if "screenshot" in h3.get_text().lower():
                next_el = h3.find_next_sibling()
                if next_el:
                    for img in next_el.select("img"):
                        src = _image_url(img)
                        if src:
                            parent_a = img.find_parent("a")
                            screenshots.append({
                                "thumb": src,
                                "full": parent_a.get("href", src) if parent_a else src,
                            })
                break

    # Video preview
    video = ""
    if content:
        video_el = content.select_one("video source")
        if video_el:
            video = video_el.get("src", "")

    # Repack Features
    features = []
    if content:
        for h3 in content.select("h3"):
            if "Repack Features" in h3.get_text():
                ul = h3.find_next_sibling("ul")
                if ul:
                    features = [li.get_text(strip=True) for li in ul.select("li")]
                break

    # Spoilers / Expandable Sections
    description = ""
    file_list = ""
    if content:
        spoilers = content.select(".su-spoiler")
        for spoiler in spoilers:
            title_el = spoiler.select_one(".su-spoiler-title")
            content_el = spoiler.select_one(".su-spoiler-content")
            if title_el and content_el:
                title_text = title_el.get_text(strip=True).lower()
                content_text = content_el.get_text("\n", strip=True)
                
                # Classify based on title text
                if any(x in title_text for x in ["file list", "selective", "files", "download list", "rar"]):
                    file_list = content_text
                elif any(x in title_text for x in ["description", "about", "story", "summary"]):
                    description = content_text
                else:
                    # Fallback
                    if not description:
                        description = content_text
                    elif not file_list:
                        file_list = content_text

    result = {
        "title": title,
        "slug": slug,
        "url": url,
        "date": date,
        "categories": categories,
        "tags": tags,
        "cover": cover,
        "genres": genres,
        "companies": companies,
        "languages": languages,
        "original_size": sizes["original_size"],
        "repack_size": sizes["repack_size"],
        "direct_links": direct_links,
        "torrent_links": torrent_links,
        "magnet_link": magnet_link,
        "screenshots": screenshots,
        "video": video,
        "features": features,
        "description": description,
        "file_list": file_list,
        "requirements": {
            "ram_min": req_ram_min,
            "ram_rec": req_ram_rec,
            "space": req_space,
            "cpu": req_cpu,
            "gpu": req_gpu,
            "requirements_source": "Source Page",
            "requirements_confidence": "high",
            "requirements_status": "available" if any([req_ram_min, req_ram_rec, req_cpu, req_gpu]) else "checking",
            "requirements_checked_at": int(time.time()),
        }
    }
    result.update(resolve_official_links(result))
    result["requirements"] = requirements_service.resolve_requirements(
        title,
        result.get("requirements") or {},
        result.get("steam_page", ""),
    )
    _remember_game_requirements(slug, result["requirements"])
    if result["requirements"].get("steam_page") and not result.get("steam_page"):
        result["steam_page"] = result["requirements"]["steam_page"]

    # --- Game Updates ---
    updates = {"instructions": "", "links": []}
    if content:
        for h3 in content.select("h3"):
            if "game updates" in h3.get_text().lower():
                sibling = h3.find_next_sibling()
                if sibling:
                    updates["instructions"] = sibling.get_text("\n", strip=True)
                    for a in sibling.select("a"):
                        href = a.get("href", "")
                        text = a.get_text(strip=True)
                        if href and text:
                            is_source = bool(re.search(
                                r"(elamigos\.site|cs\.rin\.ru|rin\.ru|github\.com|wikipedia\.org|steam)", 
                                href.lower()
                            ))
                            if not is_source:
                                updates["links"].append({
                                    "name": text,
                                    "url": href
                                })
                break
    result["updates"] = updates

    # Save details cache with 12 hours TTL (43200 seconds)
    cache.set(key, result, 43200)
    return result


@cache.cached(ttl=CACHE_TTL_LONG)
def get_upcoming_repacks() -> list:
    """Get the list of upcoming repacks from the pinned post."""
    soup = _fetch(BASE_URL)

    for article in soup.select("article"):
        title_el = article.select_one(".entry-title a")
        if title_el and "Upcoming" in title_el.get_text():
            upcoming = []
            for span in article.select('span[style*="color: #339966"]'):
                text = span.get_text(strip=True).strip()
                if text:
                    upcoming.append(text)
            return upcoming

    return []


@cache.cached(ttl=CACHE_TTL)
def get_popular_repacks() -> list:
    """Get popular repacks of the week from the sidebar widget."""
    soup = _fetch(BASE_URL)

    popular = []
    widget = soup.select_one(".jetpack_top_posts_widget")
    if widget:
        for item in widget.select(".widget-grid-view-image a"):
            title = item.get("title", "")
            url = item.get("href", "")
            slug = url.rstrip("/").split("/")[-1] if url else ""
            img = item.select_one("img")
            thumbnail = _image_url(img) if img else ""
            if _is_site_logo(thumbnail, img.get("alt", "") if img else ""):
                thumbnail = ""

            if title:
                popular.append({
                    "title": title,
                    "url": url,
                    "slug": slug,
                    "thumbnail": thumbnail,
                })

    return popular


def extract_magnet_link(slug: str) -> str | None:
    """Extract the magnet link from a game page."""
    details = get_game_details(slug)
    if details and details.get("magnet_link"):
        return details["magnet_link"]
    return None








