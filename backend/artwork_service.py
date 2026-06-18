"""
Artwork hydration for My Library platform/local imports.

No API keys are required. Steam uses public CDN paths. Epic uses a best-effort
public catalog lookup when manifest IDs are available. Manual artwork is copied
into Arcadia app data through offline_library.
"""

from __future__ import annotations

import os
import re
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

from backend import cache as app_cache, library_service, scraper
from backend.offline_library import library as offline_library


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


_TITLE_NOISE = {
    "a",
    "an",
    "and",
    "bonus",
    "bonuses",
    "build",
    "content",
    "deluxe",
    "digital",
    "dlc",
    "dlcs",
    "edition",
    "fitgirl",
    "gold",
    "goty",
    "launcher",
    "lossless",
    "multi",
    "multiplayer",
    "origin",
    "pc",
    "premium",
    "repack",
    "remastered",
    "remake",
    "soundtrack",
    "steam",
    "the",
    "ultimate",
    "unlocker",
    "version",
    "windows",
}


def _clean_title(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("™", " ").replace("®", " ").replace("’", "'")
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.sub(r"(?i)\b(v|ver|version|build)\s*[\d][\w.\-]*", " ", text)
    text = re.sub(r"(?i)\b\d+\s*(dlc|dlcs|bonus|bonuses)\b", " ", text)
    text = re.sub(r"(?i)\b(repack|lossless|fitgirl|dodi|multi\d*|unlocker|bonus soundtrack|steam library|epic games|local install)\b", " ", text)
    text = re.sub(r"(?i)\b(digital deluxe|deluxe|ultimate|gold|complete|premium|goty|collector'?s?)\s+edition\b", " ", text)
    text = re.sub(r"(?i)\b(edition|remastered|remake|enhanced|definitive)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_tokens(value: str) -> set[str]:
    return {
        token
        for token in _clean_title(value).split()
        if token and token not in _TITLE_NOISE and not token.isdigit()
    }


def _catalog_match_score(source_slug: str, source_title: str, candidate: dict[str, Any]) -> tuple[int, list[str]]:
    candidate_slug = str(candidate.get("slug") or "")
    candidate_title = str(candidate.get("title") or "")
    source_compact = _normalize(_clean_title(source_title) or source_slug)
    source_slug_compact = _normalize(source_slug)
    candidate_compact = _normalize(_clean_title(candidate_title) or candidate_slug)
    candidate_slug_compact = _normalize(candidate_slug)
    source_tokens = _title_tokens(f"{source_title} {source_slug}")
    candidate_tokens = _title_tokens(f"{candidate_title} {candidate_slug}")
    reasons: list[str] = []
    score = 0

    if source_slug_compact and source_slug_compact == candidate_slug_compact:
        return 100, ["same catalog slug"]
    if source_compact and source_compact == candidate_compact:
        return 98, ["same cleaned title"]
    if source_compact and candidate_compact:
        shorter, longer = sorted((source_compact, candidate_compact), key=len)
        if len(shorter) >= 8 and shorter in longer:
            score += 86
            reasons.append("title contains catalog title")
        score += int(SequenceMatcher(None, source_compact, candidate_compact).ratio() * 45)
    if source_slug_compact and candidate_slug_compact:
        shorter_slug, longer_slug = sorted((source_slug_compact, candidate_slug_compact), key=len)
        if len(shorter_slug) >= 8 and shorter_slug in longer_slug:
            score += 18
            reasons.append("slug contains catalog slug")
    if source_tokens and candidate_tokens:
        overlap = source_tokens & candidate_tokens
        union = source_tokens | candidate_tokens
        if overlap:
            overlap_ratio = len(overlap) / max(1, min(len(source_tokens), len(candidate_tokens)))
            jaccard = len(overlap) / max(1, len(union))
            score += int(overlap_ratio * 45) + int(jaccard * 25)
            reasons.append("shared catalog title words")
    if len(source_tokens) >= 2 and source_tokens == candidate_tokens:
        score += 16
        reasons.append("same meaningful title tokens")
    return min(score, 99), reasons[:3] or ["possible title match"]


def _catalog_candidates() -> list[dict[str, Any]]:
    by_slug: dict[str, dict[str, Any]] = {}
    for game in app_cache.get_cached_games():
        slug = str(game.get("slug") or "")
        if slug:
            by_slug[slug] = game
    try:
        index = scraper._get_cached_az_index()
    except Exception:
        index = []
    for game in index:
        slug = str(game.get("slug") or "")
        if not slug:
            continue
        current = by_slug.get(slug, {})
        merged = {**game, **current}
        if not merged.get("thumbnail") and game.get("thumbnail"):
            merged["thumbnail"] = game["thumbnail"]
        if not merged.get("cover") and game.get("cover"):
            merged["cover"] = game["cover"]
        by_slug[slug] = merged
    return list(by_slug.values())


def _candidate_image(game: dict[str, Any]) -> str:
    image = game.get("cover_cached") or game.get("thumbnail_cached") or game.get("cover") or game.get("thumbnail") or ""
    if image:
        return str(image)
    screenshots = game.get("screenshots")
    if isinstance(screenshots, list):
        for screenshot in screenshots:
            if isinstance(screenshot, dict):
                image = screenshot.get("full") or screenshot.get("thumb") or ""
                if image:
                    return str(image)
            elif isinstance(screenshot, str) and screenshot:
                return screenshot
    return ""


def _hydrate_catalog_candidate_image(game: dict[str, Any]) -> str:
    image = _candidate_image(game)
    if image:
        return image
    slug = str(game.get("slug") or "")
    if not slug:
        return ""
    try:
        details = scraper.get_game_details(slug)
    except Exception:
        details = None
    if isinstance(details, dict):
        image = _candidate_image(details)
        if image:
            return image
    try:
        return scraper._get_page_cover_only(slug)
    except Exception:
        return ""


def _entry(slug: str) -> dict[str, Any] | None:
    return offline_library.state.get("games", {}).get(slug)


def _user(slug: str) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    return entry.setdefault("user", {})


def _set_artwork(slug: str, path: str, source: str, catalog_match: dict[str, Any] | None = None) -> dict[str, Any]:
    user = _user(slug)
    user["artwork_path"] = path
    user["artwork_source"] = source
    if source != "manual":
        user.setdefault("manual_artwork_path", "")
    if catalog_match:
        user["matched_catalog_slug"] = str(catalog_match.get("slug", ""))
        user["matched_catalog_title"] = str(catalog_match.get("title", ""))
        user["matched_catalog_score"] = int(catalog_match.get("score") or 0)
        user["matched_catalog_reason"] = ", ".join(catalog_match.get("reasons") or [])
    elif source != "arcadia_catalog":
        user["matched_catalog_slug"] = ""
        user["matched_catalog_title"] = ""
        user["matched_catalog_score"] = 0
        user["matched_catalog_reason"] = ""
    entry = _entry(slug)
    if entry:
        entry["updated_at"] = __import__("time").time()
    offline_library._save()
    return library_service.get_game(slug) or {}


def _steam_artwork(slug: str, appid: str) -> str:
    if not appid:
        return ""
    urls = [
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_hero.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
    ]
    for url in urls:
        cached = offline_library.cache_artwork_url(slug, url)
        if cached and cached != url:
            return cached
    return ""


def _epic_artwork(slug: str, namespace: str, catalog_id: str) -> str:
    if not namespace or not catalog_id:
        return ""
    url = f"https://store-content.ak.epicgames.com/api/en-US/content/products/{namespace}/{catalog_id}"
    try:
        response = requests.get(url, timeout=8, headers={"User-Agent": "Arcadia Core"})
        response.raise_for_status()
        data = response.json() or {}
    except Exception:
        return ""
    image_urls: list[str] = []
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    page_images = []
    if pages:
        page_images = pages[0].get("data", {}).get("product", {}).get("keyImages", []) if isinstance(pages[0], dict) else []
    for image in data.get("keyImages") or page_images or []:
        if isinstance(image, dict) and image.get("url"):
            image_urls.append(image["url"])
    image_urls.sort(key=lambda item: (("DieselGameBox" not in item), ("OfferImageTall" not in item), item))
    for image_url in image_urls:
        cached = offline_library.cache_artwork_url(slug, image_url)
        if cached and cached != image_url:
            return cached
    return ""


def _catalog_artwork(slug: str, title: str) -> tuple[str, dict[str, Any] | None]:
    if not _normalize(title) and not _normalize(slug):
        return "", None
    matches: list[tuple[int, dict[str, Any], list[str], str]] = []
    for game in _catalog_candidates():
        score, reasons = _catalog_match_score(slug, title, game)
        if score >= 82:
            image = _candidate_image(game)
            matches.append((score, game, reasons, image))
    if not matches:
        return "", None
    matches.sort(key=lambda item: (item[0], bool(item[3])), reverse=True)
    for best_score, best_game, best_reasons, image in matches[:5]:
        if not image:
            image = _hydrate_catalog_candidate_image(best_game)
        if image.startswith("/api/"):
            return image, {"slug": best_game.get("slug", ""), "title": best_game.get("title", ""), "score": best_score, "reasons": best_reasons}
        if image:
            cached = offline_library.cache_artwork_url(slug, image)
            if cached:
                return cached, {"slug": best_game.get("slug", ""), "title": best_game.get("title", ""), "score": best_score, "reasons": best_reasons}
    return "", None


def _steam_appid_from_install_path(install_path: str) -> str:
    marker = "\\steamapps\\common\\"
    normalized = os.path.abspath(install_path or "")
    lower = normalized.lower()
    if marker not in lower:
        return ""
    steamapps = normalized[: lower.index(marker) + len("\\steamapps")]
    install_dir = os.path.basename(normalized.rstrip("\\/"))
    try:
        manifests = Path(steamapps).glob("appmanifest_*.acf")
    except OSError:
        return ""
    for manifest in manifests:
        try:
            text = manifest.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        appid = re.search(r'"appid"\s+"([^"]+)"', text, re.I)
        installdir = re.search(r'"installdir"\s+"([^"]+)"', text, re.I)
        if appid and installdir and installdir.group(1).lower() == install_dir.lower():
            return appid.group(1)
    return ""


def _epic_ids_from_install_path(install_path: str) -> dict[str, str]:
    root = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    if not root.is_dir():
        return {}
    normalized = os.path.normcase(os.path.abspath(install_path or ""))
    for manifest in root.glob("*.item"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if os.path.normcase(os.path.abspath(data.get("InstallLocation") or "")) == normalized:
            return {
                "epic_catalog_item_id": data.get("CatalogItemId", ""),
                "epic_namespace": data.get("CatalogNamespace", ""),
                "epic_app_name": data.get("AppName", ""),
                "epic_display_name": data.get("DisplayName", ""),
                "epic_vault_thumbnail_url": data.get("VaultThumbnailUrl", ""),
            }
    return {}


def refresh_artwork(slugs: list[str] | None = None) -> dict[str, Any]:
    games = library_service.list_games()
    wanted = {str(slug) for slug in (slugs or []) if slug}
    if wanted:
        games = [game for game in games if game.get("slug") in wanted]
    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for game in games:
        slug = game.get("slug") or ""
        library = game.get("library") or game.get("offline_user") or {}
        if not slug:
            continue
        if library.get("manual_artwork_path"):
            skipped.append({"slug": slug, "reason": "manual artwork"})
            continue
        if not wanted and game.get("cover") and game.get("cover") != "/assets/game-cover-placeholder.png" and library.get("artwork_path"):
            skipped.append({"slug": slug, "reason": "already cached"})
            continue
        source = str(library.get("library_source") or "").lower()
        install_path = str(library.get("install_path") or "")
        path = ""
        artwork_source = ""
        catalog_match: dict[str, Any] | None = None
        epic_ids: dict[str, str] = {}
        normalized_install_path = install_path.lower().replace("/", "\\")
        is_steam_path = "\\steamapps\\common\\" in normalized_install_path
        is_epic_path = "\\epic games\\" in normalized_install_path or "\\epicgames\\" in normalized_install_path
        if install_path and is_steam_path and source not in {"steam", "arcadia_download"}:
            library_service.update_user_data(slug, {"library_source": "steam"})
            source = "steam"
        if is_epic_path and source not in {"epic", "arcadia_download"}:
            library_service.update_user_data(slug, {"library_source": "epic"})
            source = "epic"
        if source == "steam" or library.get("platform_app_id"):
            appid = str(library.get("platform_app_id") or "") or _steam_appid_from_install_path(install_path)
            if appid and not library.get("platform_app_id"):
                library_service.update_user_data(slug, {"platform_app_id": appid})
            path = _steam_artwork(slug, appid)
            artwork_source = "steam" if path else ""
        if not path and (source == "epic" or library.get("epic_catalog_item_id") or is_epic_path):
            if not library.get("epic_catalog_item_id"):
                epic_ids = _epic_ids_from_install_path(install_path)
                if epic_ids:
                    library_service.update_user_data(slug, epic_ids)
            path = _epic_artwork(
                slug,
                str(library.get("epic_namespace") or epic_ids.get("epic_namespace", "")),
                str(library.get("epic_catalog_item_id") or epic_ids.get("epic_catalog_item_id", "")),
            )
            artwork_source = "epic" if path else ""
            if not path and epic_ids.get("epic_vault_thumbnail_url"):
                path = offline_library.cache_artwork_url(slug, epic_ids["epic_vault_thumbnail_url"])
                artwork_source = "epic" if path else ""
        if not path:
            catalog_title = game.get("title", "") or epic_ids.get("epic_display_name", "")
            path, catalog_match = _catalog_artwork(slug, catalog_title)
            artwork_source = "arcadia_catalog" if path else ""
        if not path and epic_ids.get("epic_display_name"):
            path, catalog_match = _catalog_artwork(slug, epic_ids["epic_display_name"])
            artwork_source = "arcadia_catalog" if path else ""
        if path:
            _set_artwork(slug, path, artwork_source, catalog_match)
            item = {"slug": slug, "source": artwork_source, "path": path}
            if catalog_match:
                item["matched_catalog_slug"] = str(catalog_match.get("slug", ""))
                item["matched_catalog_title"] = str(catalog_match.get("title", ""))
                item["match_score"] = str(catalog_match.get("score", ""))
                item["match_reason"] = ", ".join(catalog_match.get("reasons") or [])
            updated.append(item)
        else:
            user = _user(slug)
            user.setdefault("artwork_source", "placeholder")
            skipped.append({"slug": slug, "reason": "placeholder"})
    offline_library._save()
    return {"success": True, "updated": updated, "skipped": skipped}


def set_manual_artwork(slug: str, file_path: str) -> dict[str, Any]:
    cached = offline_library.cache_artwork_file(slug, file_path)
    user = _user(slug)
    user["manual_artwork_path"] = cached
    user["artwork_path"] = cached
    user["artwork_source"] = "manual"
    offline_library._save()
    return {"success": True, "game": library_service.get_game(slug)}


def reset_artwork(slug: str) -> dict[str, Any]:
    user = _user(slug)
    user["manual_artwork_path"] = ""
    user["artwork_path"] = ""
    user["artwork_source"] = ""
    offline_library._save()
    result = refresh_artwork([slug])
    return {"success": True, "game": library_service.get_game(slug), "refresh": result}
