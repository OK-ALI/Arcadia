"""
Own & Play library service.

This module keeps install-state, executable linking, download enrollment, and
launch/playtime orchestration out of the storage and downloader modules.
"""

from __future__ import annotations

import os
import re
import time
import requests
from difflib import SequenceMatcher
from typing import Any

from backend import cache as app_cache, scraper
from backend.executable_detector import detect_executables
from backend.game_launcher import get_launch_session, launch_executable
from backend.offline_library import _folder_size_bytes, library as offline_library


INSTALL_FIELDS = {
    "install_status",
    "install_path",
    "executable_path",
    "executable_candidates",
    "install_size_bytes",
    "install_size_scanned_at",
    "last_played_at",
    "playtime_seconds",
    "launch_count",
    "library_source",
    "artwork_source",
    "artwork_path",
    "manual_artwork_path",
    "platform_app_id",
    "epic_catalog_item_id",
    "epic_namespace",
    "epic_app_name",
    "matched_catalog_slug",
    "matched_catalog_title",
    "matched_catalog_score",
    "matched_catalog_reason",
}

CATALOG_METADATA_FIELDS = {
    "genres",
    "companies",
    "languages",
    "original_size",
    "repack_size",
    "date",
    "requirements",
    "steam_page",
    "official_site",
}

PLATFORM_METADATA_FIELDS = {
    "genres",
    "companies",
    "languages",
    "date",
    "requirements",
    "steam_page",
}

_TITLE_NOISE = {
    "arcadia",
    "deluxe",
    "digital",
    "edition",
    "enhanced",
    "epic",
    "games",
    "goty",
    "library",
    "local",
    "premium",
    "repack",
    "steam",
    "the",
    "ultimate",
}


def _now() -> float:
    return time.time()


def _entry(slug: str) -> dict[str, Any] | None:
    return offline_library.state.get("games", {}).get(slug)


def _clean_match_title(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("™", " ").replace("®", " ").replace("’", "'")
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.sub(r"(?i)\b(v|ver|version|build)\s*[\d][\w.\-]*", " ", text)
    text = re.sub(r"(?i)\b\d+\s*(dlc|dlcs|bonus|bonuses)\b", " ", text)
    text = re.sub(r"(?i)\b(repack|lossless|fitgirl|dodi|multi\d*|unlocker|steam library|epic games|local install)\b", " ", text)
    text = re.sub(r"(?i)\b(digital deluxe|deluxe|ultimate|gold|complete|premium|goty|collector'?s?)\s+edition\b", " ", text)
    text = re.sub(r"(?i)\b(edition|remastered|remake|enhanced|definitive)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _title_tokens(value: str) -> set[str]:
    return {
        token
        for token in _clean_match_title(value).split()
        if token and token not in _TITLE_NOISE and not token.isdigit()
    }


def _metadata_missing(game: dict[str, Any]) -> bool:
    return any(not game.get(field) for field in ("genres", "companies", "languages", "original_size", "repack_size", "date"))


def _catalog_candidates() -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    try:
        for game in app_cache.get_cached_games():
            slug = str(game.get("slug") or "")
            if slug:
                candidates[slug] = game
    except Exception:
        pass
    try:
        for game in scraper._get_cached_az_index():
            slug = str(game.get("slug") or "")
            if slug:
                current = candidates.get(slug, {})
                candidates[slug] = {**game, **current}
    except Exception:
        pass
    return list(candidates.values())


def _search_catalog_candidates(title: str) -> list[dict[str, Any]]:
    query = _clean_match_title(title) or str(title or "").strip()
    if not query or len(query) < 3:
        return []
    try:
        result = scraper.search_games(query, page=1)
    except Exception:
        return []
    games = result.get("games") if isinstance(result, dict) else []
    return games if isinstance(games, list) else []


def _catalog_match_score(source_slug: str, source_title: str, candidate: dict[str, Any]) -> int:
    candidate_slug = str(candidate.get("slug") or "")
    candidate_title = str(candidate.get("title") or "")
    source_compact = _compact(_clean_match_title(source_title) or source_slug)
    candidate_compact = _compact(_clean_match_title(candidate_title) or candidate_slug)
    source_slug_compact = _compact(source_slug)
    candidate_slug_compact = _compact(candidate_slug)
    if source_slug_compact and source_slug_compact == candidate_slug_compact:
        return 100
    if source_compact and candidate_compact and source_compact == candidate_compact:
        return 98
    score = 0
    if source_compact and candidate_compact:
        shorter, longer = sorted((source_compact, candidate_compact), key=len)
        if len(shorter) >= 8 and shorter in longer:
            score += 84
        score += int(SequenceMatcher(None, source_compact, candidate_compact).ratio() * 45)
    source_tokens = _title_tokens(f"{source_title} {source_slug}")
    candidate_tokens = _title_tokens(f"{candidate_title} {candidate_slug}")
    if source_tokens and candidate_tokens:
        overlap = source_tokens & candidate_tokens
        if overlap:
            score += int((len(overlap) / max(1, min(len(source_tokens), len(candidate_tokens)))) * 45)
    return min(score, 99)


def _find_catalog_slug(entry: dict[str, Any]) -> tuple[str, int]:
    game = entry.get("game", {})
    user = _ensure_user(entry)
    stored = str(user.get("matched_catalog_slug") or "")
    if stored:
        return stored, int(user.get("matched_catalog_score") or 0)
    slug = str(entry.get("slug") or game.get("slug") or "")
    if slug and not slug.startswith("local-"):
        return slug, 100
    title = str(game.get("title") or "")
    matches = []
    candidates = _catalog_candidates()
    if not candidates:
        candidates = _search_catalog_candidates(title)
    for candidate in candidates:
        score = _catalog_match_score(slug, title, candidate)
        if score >= 82:
            matches.append((score, candidate))
    if not matches and candidates:
        for candidate in _search_catalog_candidates(title):
            score = _catalog_match_score(slug, title, candidate)
            if score >= 82:
                matches.append((score, candidate))
    if not matches:
        return "", 0
    matches.sort(key=lambda item: item[0], reverse=True)
    score, candidate = matches[0]
    return str(candidate.get("slug") or ""), score


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\s+([,;:])", r"\1", text)
    text = re.sub(r"([,;:])(?=\S)", r"\1 ", text)
    return re.sub(r"\s+", " ", text).strip()


def _steam_app_metadata(appid: str) -> dict[str, Any]:
    appid = str(appid or "").strip()
    if not appid:
        return {}
    cache_key = f"steam_app_metadata:v2:{appid}"
    cached = app_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic,genres,developers,publishers,release_date,pc_requirements"
    try:
        response = requests.get(url, timeout=8, headers={"User-Agent": "Arcadia Core"})
        response.raise_for_status()
        payload = response.json() or {}
    except Exception:
        return {}
    wrapper = payload.get(appid) if isinstance(payload, dict) else {}
    data = wrapper.get("data") if isinstance(wrapper, dict) and wrapper.get("success") else {}
    if not isinstance(data, dict):
        return {}
    developers = data.get("developers") if isinstance(data.get("developers"), list) else []
    publishers = data.get("publishers") if isinstance(data.get("publishers"), list) else []
    companies = []
    for name in developers + publishers:
        name = str(name or "").strip()
        if name and name not in companies:
            companies.append(name)
    genres = [
        str(item.get("description") or "").strip()
        for item in data.get("genres", [])
        if isinstance(item, dict) and item.get("description")
    ]
    requirements = {}
    pc_requirements = data.get("pc_requirements") if isinstance(data.get("pc_requirements"), dict) else {}
    if pc_requirements:
        minimum = _strip_html(pc_requirements.get("minimum", ""))
        recommended = _strip_html(pc_requirements.get("recommended", ""))
        try:
            requirements = scraper._parse_requirements_text("\n".join([minimum, recommended]))
        except Exception:
            requirements = {"minimum": minimum, "recommended": recommended}
    metadata = {
        "genres": ", ".join(genres),
        "companies": ", ".join(companies),
        "languages": _strip_html(data.get("supported_languages", "")),
        "date": (data.get("release_date") or {}).get("date", "") if isinstance(data.get("release_date"), dict) else "",
        "requirements": requirements,
        "steam_page": f"https://store.steampowered.com/app/{appid}/",
    }
    metadata = {key: value for key, value in metadata.items() if value}
    app_cache.set(cache_key, metadata, ttl=7 * 24 * 60 * 60)
    return metadata


def _enrich_entry_from_platform(entry: dict[str, Any]) -> bool:
    game = entry.setdefault("game", {})
    user = _ensure_user(entry)
    source = str(user.get("library_source") or "").lower()
    appid = str(user.get("platform_app_id") or "").strip()
    if source != "steam" and not appid:
        return False
    metadata = _steam_app_metadata(appid)
    changed = False
    for field in ("genres", "companies", "languages"):
        if game.get(field):
            cleaned = _strip_html(str(game.get(field)))
            if cleaned and cleaned != game.get(field):
                game[field] = cleaned
                changed = True
    if not metadata:
        if changed:
            entry["updated_at"] = _now()
            offline_library._save()
        return changed
    for field in PLATFORM_METADATA_FIELDS:
        if not game.get(field) and metadata.get(field):
            game[field] = metadata[field]
            changed = True
    if changed:
        entry["updated_at"] = _now()
        offline_library._save()
    return changed


def _enrich_entry_from_catalog(entry: dict[str, Any]) -> bool:
    game = entry.setdefault("game", {})
    if not _metadata_missing(game):
        return False
    catalog_slug, score = _find_catalog_slug(entry)
    if not catalog_slug:
        return False
    try:
        details = scraper.get_game_details(catalog_slug)
    except Exception:
        details = None
    if not isinstance(details, dict):
        return False
    changed = False
    for field in CATALOG_METADATA_FIELDS:
        if not game.get(field) and details.get(field):
            game[field] = details[field]
            changed = True
    for field in ("cover", "thumbnail", "cover_cached", "thumbnail_cached", "screenshots", "features", "summary", "url", "source", "category", "tags"):
        if not game.get(field) and details.get(field):
            game[field] = details[field]
            changed = True
    user = _ensure_user(entry)
    if catalog_slug and not user.get("matched_catalog_slug"):
        user["matched_catalog_slug"] = catalog_slug
        user["matched_catalog_title"] = details.get("title", "")
        user["matched_catalog_score"] = score
        user["matched_catalog_reason"] = "metadata match"
        changed = True
    if changed:
        entry["updated_at"] = _now()
        offline_library._save()
    return changed


def _ensure_user(entry: dict[str, Any], source: str = "saved") -> dict[str, Any]:
    user = entry.setdefault("user", {})
    user.setdefault("notes", "")
    user.setdefault("custom_tags", [])
    user.setdefault("favorite", False)
    user.setdefault("install_status", "backlog")
    user.setdefault("install_path", "")
    user.setdefault("executable_path", "")
    user.setdefault("executable_candidates", [])
    user.setdefault("install_size_bytes", 0)
    user.setdefault("install_size_scanned_at", None)
    user.setdefault("last_played_at", None)
    user.setdefault("playtime_seconds", 0)
    user.setdefault("launch_count", 0)
    user.setdefault("library_source", source)
    user.setdefault("artwork_source", "")
    user.setdefault("artwork_path", "")
    user.setdefault("manual_artwork_path", "")
    user.setdefault("platform_app_id", "")
    user.setdefault("epic_catalog_item_id", "")
    user.setdefault("epic_namespace", "")
    user.setdefault("epic_app_name", "")
    user.setdefault("matched_catalog_slug", "")
    user.setdefault("matched_catalog_title", "")
    user.setdefault("matched_catalog_score", 0)
    user.setdefault("matched_catalog_reason", "")
    return user


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    game = dict(entry.get("game", {}))
    user = _ensure_user(entry)
    slug = game.get("slug") or ""
    session = get_launch_session(slug) if slug else None
    if game.get("cover_cached"):
        game["cover"] = game["cover_cached"]
        game["thumbnail"] = game.get("thumbnail_cached") or game["cover_cached"]
    artwork_path = user.get("manual_artwork_path") or user.get("artwork_path") or ""
    if artwork_path:
        game["cover"] = artwork_path
        game["thumbnail"] = artwork_path
    game["artwork_source"] = user.get("artwork_source") or ("arcadia_cache" if game.get("cover_cached") else "placeholder")
    game["offline_user"] = user
    game["offline_saved_at"] = entry.get("saved_at")
    game["offline_updated_at"] = entry.get("updated_at")
    game["library"] = {
        "install_status": user.get("install_status", "backlog"),
        "install_path": user.get("install_path", ""),
        "executable_path": user.get("executable_path", ""),
        "executable_candidates": user.get("executable_candidates", []),
        "last_played_at": user.get("last_played_at"),
        "playtime_seconds": int(user.get("playtime_seconds") or 0),
        "launch_count": int(user.get("launch_count") or 0),
        "library_source": user.get("library_source", "saved"),
        "artwork_source": user.get("artwork_source") or game.get("artwork_source"),
        "artwork_path": user.get("manual_artwork_path") or user.get("artwork_path", ""),
        "manual_artwork_path": user.get("manual_artwork_path", ""),
        "platform_app_id": user.get("platform_app_id", ""),
        "epic_catalog_item_id": user.get("epic_catalog_item_id", ""),
        "epic_namespace": user.get("epic_namespace", ""),
        "epic_app_name": user.get("epic_app_name", ""),
        "matched_catalog_slug": user.get("matched_catalog_slug", ""),
        "matched_catalog_title": user.get("matched_catalog_title", ""),
        "matched_catalog_score": user.get("matched_catalog_score", 0),
        "matched_catalog_reason": user.get("matched_catalog_reason", ""),
        "running": bool(session),
        "running_pid": session.get("pid") if session else None,
        "running_started_at": session.get("started_at") if session else None,
    }
    install_path = user.get("install_path") or ""
    if user.get("install_status") == "installed" and install_path:
        install_size = int(user.get("install_size_bytes") or 0)
        if install_size <= 0:
            install_size = _folder_size_bytes(install_path)
        game["library"]["installed_size_bytes"] = install_size
        game["library"]["installed_size_gb"] = round(install_size / (1024**3), 2)
        game["library"]["installed_size_scanned_at"] = user.get("install_size_scanned_at")
    else:
        game["library"]["installed_size_bytes"] = 0
        game["library"]["installed_size_gb"] = 0
        game["library"]["installed_size_scanned_at"] = None
    return game


def upgrade_all_entries() -> None:
    changed = False
    for entry in offline_library.state.get("games", {}).values():
        before = dict(entry.get("user", {}))
        _ensure_user(entry)
        changed = changed or before != entry.get("user", {})
    if changed:
        offline_library._save()


def list_games() -> list[dict[str, Any]]:
    upgrade_all_entries()
    games = [_public_entry(entry) for entry in offline_library.state.get("games", {}).values()]
    games.sort(key=lambda x: x.get("offline_updated_at") or 0, reverse=True)
    return games


def get_game(slug: str) -> dict[str, Any] | None:
    entry = _entry(slug)
    if not entry:
        return None
    _ensure_user(entry)
    _enrich_entry_from_catalog(entry)
    _enrich_entry_from_platform(entry)
    offline_library._save()
    return _public_entry(entry)


def remove_game(slug: str) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    title = (entry.get("game") or {}).get("title") or slug
    del offline_library.state["games"][slug]
    offline_library._save()
    return {"success": True, "slug": slug, "title": title}


def save_game(game: dict[str, Any], source: str = "saved") -> dict[str, Any]:
    entry = offline_library.save_game(game)
    user = _ensure_user(entry, source)
    user["library_source"] = user.get("library_source") or source
    offline_library._save()
    return entry


def update_user_data(slug: str, data: dict[str, Any]) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    user = _ensure_user(entry)
    allowed = {
        "notes",
        "custom_tags",
        "favorite",
        "install_status",
        "install_path",
        "executable_path",
        "executable_candidates",
        "install_size_bytes",
        "install_size_scanned_at",
        "last_played_at",
        "playtime_seconds",
        "launch_count",
        "library_source",
        "artwork_source",
        "artwork_path",
        "manual_artwork_path",
        "platform_app_id",
        "epic_catalog_item_id",
        "epic_namespace",
        "epic_app_name",
        "matched_catalog_slug",
        "matched_catalog_title",
        "matched_catalog_score",
        "matched_catalog_reason",
    }
    for key in allowed:
        if key in data:
            user[key] = data[key]
    if user.get("install_status") == "installed" and user.get("executable_path") and not os.path.exists(user["executable_path"]):
        user["install_status"] = "missing"
    entry["updated_at"] = _now()
    offline_library._save()
    return entry


def link_game(slug: str, install_path: str, executable_path: str | None = None, source: str = "manual") -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        game = scraper.get_game_details(slug)
        if not game:
            raise ValueError("Game is not saved in My Library.")
        entry = save_game(game, source=source)
    user = _ensure_user(entry, source)
    game = entry.get("game", {})
    detected = detect_executables(install_path, game.get("title", ""), slug)
    selected = os.path.abspath(executable_path) if executable_path else detected.get("selected", "")
    if selected:
        selected = os.path.abspath(selected)
        root = os.path.abspath(detected["install_path"])
        if not selected.lower().endswith(".exe") or not os.path.exists(selected):
            raise ValueError("Selected executable does not exist.")
        try:
            inside_root = os.path.commonpath([root, selected]) == root
        except ValueError:
            inside_root = False
        if not inside_root:
            raise ValueError("Selected executable must be inside the install folder.")

    user["install_path"] = detected["install_path"]
    user["executable_candidates"] = detected.get("candidates", [])
    if source and source not in {"manual", "saved"}:
        user["library_source"] = source
    else:
        user["library_source"] = user.get("library_source") or source
    user["install_size_bytes"] = _folder_size_bytes(detected["install_path"])
    user["install_size_scanned_at"] = _now()
    if selected:
        user["executable_path"] = selected
        user["install_status"] = "installed"
    elif detected.get("candidates"):
        user["executable_path"] = ""
        user["install_status"] = "unlinked"
    else:
        user["executable_path"] = ""
        user["install_status"] = "missing"
    entry["updated_at"] = _now()
    offline_library._save()
    return {"entry": entry, "game": _public_entry(entry), "detection": detected}


def mark_backlog(slug: str) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    user = _ensure_user(entry)
    user["install_status"] = "backlog"
    user["install_path"] = ""
    user["executable_path"] = ""
    user["executable_candidates"] = []
    user["install_size_bytes"] = 0
    user["install_size_scanned_at"] = None
    entry["updated_at"] = _now()
    offline_library._save()
    return entry


def open_install_folder(slug: str) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    user = _ensure_user(entry)
    install_path = user.get("install_path") or ""
    if not install_path or not os.path.isdir(install_path):
        user["install_status"] = "missing"
        offline_library._save()
        raise ValueError("Install folder is missing.")
    os.startfile(install_path)
    return {"success": True, "install_path": install_path}


def launch_game(slug: str) -> dict[str, Any]:
    entry = _entry(slug)
    if not entry:
        raise ValueError("Game is not saved in My Library.")
    user = _ensure_user(entry)
    executable_path = user.get("executable_path") or ""
    if not executable_path or not os.path.exists(executable_path):
        user["install_status"] = "missing"
        entry["updated_at"] = _now()
        offline_library._save()
        raise ValueError("Linked executable is missing.")
    session = get_launch_session(slug)
    if session:
        user["install_status"] = "installed"
        entry["updated_at"] = _now()
        offline_library._save()
        return {"success": True, "already_running": True, "launch": session, "game": _public_entry(entry)}

    def _finished(elapsed: float):
        current = _entry(slug)
        if not current:
            return
        current_user = _ensure_user(current)
        current_user["playtime_seconds"] = int(current_user.get("playtime_seconds") or 0) + int(elapsed)
        current["updated_at"] = _now()
        offline_library._save()

    result = launch_executable(executable_path, session_key=slug, on_finished=_finished)
    user["launch_count"] = int(user.get("launch_count") or 0) + 1
    user["last_played_at"] = result["started_at"]
    user["install_status"] = "installed"
    entry["updated_at"] = _now()
    offline_library._save()
    return {"success": True, "launch": result, "game": _public_entry(entry)}


def enroll_completed_download(download_item: dict[str, Any]) -> dict[str, Any] | None:
    slug = str(download_item.get("slug") or "").strip()
    if not slug or slug == "direct-torrent" or download_item.get("status") != "completed":
        return None
    if download_item.get("library_enrolled_at"):
        return None

    game = get_game(slug)
    if not game:
        details = scraper.get_game_details(slug)
        if not details:
            return None
        save_game(details, source="arcadia_download")

    save_path = download_item.get("save_path") or ""
    if not save_path or not os.path.isdir(save_path):
        return None
    linked = link_game(slug, save_path, source="arcadia_download")
    return linked


def enroll_completed_downloads(downloads: list[dict[str, Any]]) -> list[str]:
    enrolled = []
    for item in downloads:
        try:
            result = enroll_completed_download(item)
            if result:
                item["library_enrolled_at"] = _now()
                enrolled.append(str(item.get("info_hash") or item.get("id") or ""))
        except Exception as exc:
            item["library_enroll_error"] = str(exc)
    if enrolled:
        offline_library._save()
    return enrolled
