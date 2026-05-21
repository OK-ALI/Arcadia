"""
offline_library.py - Durable offline game library and local planning metadata.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR


LIBRARY_FILE = os.path.join(DATA_DIR, "offline_library.json")
MEDIA_DIR = os.path.join(DATA_DIR, "offline_media")


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return value[:80] or "asset"


def _size_gb(size: str) -> float:
    if not size:
        return 0.0
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*([GMK]B)", size, re.I)
    if not match:
        return 0.0
    value = float(match.group(1).replace(",", "."))
    unit = match.group(2).upper()
    if unit == "MB":
        return value / 1024
    if unit == "KB":
        return value / (1024 * 1024)
    return value


class OfflineLibrary:
    def __init__(self):
        os.makedirs(MEDIA_DIR, exist_ok=True)
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        state = _read_json(LIBRARY_FILE, {})
        state.setdefault("games", {})
        state.setdefault("settings", {"auto_save_viewed_games": True, "cache_media": True})
        return state

    def _save(self):
        _write_json(LIBRARY_FILE, self.state)

    def _cache_url(self, slug: str, url: str) -> str:
        if not url or url.startswith("data:"):
            return url
        parsed = urllib.parse.urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        folder = os.path.join(MEDIA_DIR, _safe_name(slug))
        os.makedirs(folder, exist_ok=True)
        name = _safe_name(os.path.basename(parsed.path) or "image") + ext
        target = os.path.join(folder, name)
        rel = os.path.relpath(target, DATA_DIR).replace("\\", "/")
        if os.path.exists(target):
            return f"/api/offline/media/{rel}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read(8 * 1024 * 1024)
            with open(target, "wb") as f:
                f.write(data)
            return f"/api/offline/media/{rel}"
        except Exception:
            return url

    def save_game(self, game: dict[str, Any], cache_media: bool | None = None) -> dict[str, Any]:
        if not game or not game.get("slug"):
            raise ValueError("Cannot save game without a slug.")
        slug = game["slug"]
        current = self.state["games"].get(slug, {})
        metadata = current.get("user", {})
        saved = {**current.get("game", {}), **game}
        should_cache = self.state["settings"].get("cache_media", True) if cache_media is None else cache_media
        if should_cache:
            if saved.get("cover"):
                saved["cover_cached"] = self._cache_url(slug, saved["cover"])
            if saved.get("thumbnail"):
                saved["thumbnail_cached"] = self._cache_url(slug, saved["thumbnail"])
            screenshots = []
            for shot in saved.get("screenshots", [])[:12]:
                shot = dict(shot)
                if shot.get("thumb"):
                    shot["thumb_cached"] = self._cache_url(slug, shot["thumb"])
                screenshots.append(shot)
            if screenshots:
                saved["screenshots"] = screenshots

        self.state["games"][slug] = {
            "slug": slug,
            "game": saved,
            "user": {
                "notes": metadata.get("notes", ""),
                "custom_tags": metadata.get("custom_tags", []),
                "favorite": metadata.get("favorite", False),
                "install_status": metadata.get("install_status", "backlog"),
            },
            "saved_at": current.get("saved_at") or time.time(),
            "updated_at": time.time(),
        }
        self._save()
        return self.state["games"][slug]

    def list_games(self) -> list[dict[str, Any]]:
        games = []
        for entry in self.state["games"].values():
            game = dict(entry.get("game", {}))
            game["offline_user"] = entry.get("user", {})
            game["offline_saved_at"] = entry.get("saved_at")
            game["offline_updated_at"] = entry.get("updated_at")
            if game.get("cover_cached"):
                game["cover"] = game["cover_cached"]
                game["thumbnail"] = game.get("thumbnail_cached") or game["cover_cached"]
            games.append(game)
        games.sort(key=lambda x: x.get("offline_updated_at") or 0, reverse=True)
        return games

    def get_game(self, slug: str) -> dict[str, Any] | None:
        entry = self.state["games"].get(slug)
        if not entry:
            return None
        game = dict(entry.get("game", {}))
        game["offline_user"] = entry.get("user", {})
        if game.get("cover_cached"):
            game["cover"] = game["cover_cached"]
            game["thumbnail"] = game.get("thumbnail_cached") or game["cover_cached"]
        return game

    def update_user_data(self, slug: str, data: dict[str, Any]) -> dict[str, Any]:
        entry = self.state["games"].get(slug)
        if not entry:
            raise ValueError("Game is not saved offline.")
        user = entry.setdefault("user", {})
        for key in ("notes", "custom_tags", "favorite", "install_status"):
            if key in data:
                user[key] = data[key]
        entry["updated_at"] = time.time()
        self._save()
        return entry

    def stats(self, downloads: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        games = self.list_games()
        repack_total = sum(_size_gb(g.get("repack_size", "")) for g in games)
        original_total = sum(_size_gb(g.get("original_size", "")) for g in games)
        downloaded = [d for d in (downloads or []) if d.get("status") == "completed"]
        remaining = [d for d in (downloads or []) if d.get("status") not in {"completed", "removed"}]
        media_files = 0
        media_size = 0
        for root, _, files in os.walk(MEDIA_DIR):
            media_files += len(files)
            for filename in files:
                try:
                    media_size += os.path.getsize(os.path.join(root, filename))
                except OSError:
                    pass
        return {
            "saved_games": len(games),
            "repack_total_gb": round(repack_total, 2),
            "original_total_gb": round(original_total, 2),
            "bandwidth_saved_gb": round(max(original_total - repack_total, 0), 2),
            "completed_downloads": len(downloaded),
            "remaining_queue": len(remaining),
            "media_files": media_files,
            "media_size_mb": round(media_size / (1024 * 1024), 2),
        }

    def export_library(self) -> str:
        raw = json.dumps(self.state, ensure_ascii=False).encode("utf-8")
        return base64.b64encode(raw).decode("ascii")

    def import_library(self, payload: str):
        data = json.loads(base64.b64decode(payload.encode("ascii")).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid library import.")
        data.setdefault("games", {})
        data.setdefault("settings", {})
        self.state = data
        self._save()

    def prune_media(self) -> dict[str, Any]:
        referenced = set()
        for entry in self.state["games"].values():
            game = entry.get("game", {})
            for key in ("cover_cached", "thumbnail_cached"):
                value = game.get(key, "")
                if value.startswith("/api/offline/media/"):
                    referenced.add(value.rsplit("/", 1)[-1])
            for shot in game.get("screenshots", []):
                value = shot.get("thumb_cached", "")
                if value.startswith("/api/offline/media/"):
                    referenced.add(value.rsplit("/", 1)[-1])

        removed = 0
        for root, _, files in os.walk(MEDIA_DIR):
            for filename in files:
                if filename not in referenced:
                    try:
                        os.remove(os.path.join(root, filename))
                        removed += 1
                    except OSError:
                        pass
        for child in Path(MEDIA_DIR).iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True) if not any(child.iterdir()) else None
        return {"removed": removed}


library = OfflineLibrary()
