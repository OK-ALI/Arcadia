"""
Own & Play library service.

This module keeps install-state, executable linking, download enrollment, and
launch/playtime orchestration out of the storage and downloader modules.
"""

from __future__ import annotations

import os
import time
from typing import Any

from backend import scraper
from backend.executable_detector import detect_executables
from backend.game_launcher import get_launch_session, launch_executable
from backend.offline_library import library as offline_library


INSTALL_FIELDS = {
    "install_status",
    "install_path",
    "executable_path",
    "executable_candidates",
    "last_played_at",
    "playtime_seconds",
    "launch_count",
    "library_source",
}


def _now() -> float:
    return time.time()


def _entry(slug: str) -> dict[str, Any] | None:
    return offline_library.state.get("games", {}).get(slug)


def _ensure_user(entry: dict[str, Any], source: str = "saved") -> dict[str, Any]:
    user = entry.setdefault("user", {})
    user.setdefault("notes", "")
    user.setdefault("custom_tags", [])
    user.setdefault("favorite", False)
    user.setdefault("install_status", "backlog")
    user.setdefault("install_path", "")
    user.setdefault("executable_path", "")
    user.setdefault("executable_candidates", [])
    user.setdefault("last_played_at", None)
    user.setdefault("playtime_seconds", 0)
    user.setdefault("launch_count", 0)
    user.setdefault("library_source", source)
    return user


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    game = dict(entry.get("game", {}))
    user = _ensure_user(entry)
    slug = game.get("slug") or ""
    session = get_launch_session(slug) if slug else None
    if game.get("cover_cached"):
        game["cover"] = game["cover_cached"]
        game["thumbnail"] = game.get("thumbnail_cached") or game["cover_cached"]
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
        "running": bool(session),
        "running_pid": session.get("pid") if session else None,
        "running_started_at": session.get("started_at") if session else None,
    }
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
    offline_library._save()
    return _public_entry(entry)


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
        "last_played_at",
        "playtime_seconds",
        "launch_count",
        "library_source",
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
    user["library_source"] = user.get("library_source") or source
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
