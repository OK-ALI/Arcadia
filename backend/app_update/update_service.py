"""GitHub Releases based in-app update support."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import requests

from backend.config import APP_VERSION, DATA_DIR, GITHUB_REPO, HEADERS, REQUEST_TIMEOUT

UPDATE_DIR = os.path.join(DATA_DIR, "updates")
UPDATE_STATE_FILE = os.path.join(UPDATE_DIR, "update_state.json")
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
INSTALLER_ASSET_NAME = "ArcadiaCoreSetup.exe"


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int


def current_version() -> str:
    return APP_VERSION


def _parse_version(value: str) -> Version:
    text = str(value or "").strip().lower().lstrip("v")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return Version(0, 0, 0)
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _is_newer(latest: str, installed: str = APP_VERSION) -> bool:
    return _parse_version(latest) > _parse_version(installed)


def _read_state() -> dict[str, Any]:
    try:
        with open(UPDATE_STATE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state(state: dict[str, Any]) -> None:
    os.makedirs(UPDATE_DIR, exist_ok=True)
    with open(UPDATE_STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _asset_from_release(release: dict[str, Any]) -> dict[str, Any]:
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.lower() == INSTALLER_ASSET_NAME.lower() or name.lower().endswith("setup.exe"):
            return {
                "name": name,
                "size": int(asset.get("size") or 0),
                "download_url": asset.get("browser_download_url") or "",
            }
    return {}


def _public_state(update: dict[str, Any] | None = None, *, error: str = "") -> dict[str, Any]:
    state = _read_state()
    if update:
        state.update(update)
    state.setdefault("current_version", APP_VERSION)
    state.setdefault("latest_version", "")
    state.setdefault("update_available", False)
    state.setdefault("release_url", "")
    state.setdefault("release_notes", "")
    state.setdefault("asset", {})
    state.setdefault("downloaded", False)
    state.setdefault("installer_path", "")
    state.setdefault("last_checked_at", 0)
    if error:
        state["error"] = error
    return state


def check_for_updates(force: bool = False) -> dict[str, Any]:
    state = _read_state()
    now = int(time.time())
    if not force and state.get("last_checked_at") and now - int(state.get("last_checked_at") or 0) < 1800:
        return _public_state()
    try:
        response = requests.get(GITHUB_RELEASES_URL, headers={**HEADERS, "Accept": "application/vnd.github+json"}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        release = response.json() or {}
        if release.get("prerelease") or release.get("draft"):
            update = {
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "update_available": False,
                "last_checked_at": now,
                "message": "Latest GitHub release is not a stable release.",
            }
            _write_state(update)
            return _public_state(update)
        tag = str(release.get("tag_name") or release.get("name") or "")
        latest_version = tag.lstrip("v")
        update_available = _is_newer(latest_version)
        asset = _asset_from_release(release)
        update = {
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "update_available": update_available,
            "release_url": release.get("html_url") or "",
            "release_notes": str(release.get("body") or "")[:12000] if update_available else "",
            "published_at": release.get("published_at") or "",
            "asset": asset if update_available else {},
            "last_checked_at": now,
            "error": "",
        }
        existing_path = state.get("installer_path") or ""
        update["downloaded"] = bool(existing_path and os.path.exists(existing_path) and state.get("latest_version") == latest_version)
        update["installer_path"] = existing_path if update["downloaded"] else ""
        _write_state(update)
        return _public_state(update)
    except Exception as exc:
        return _public_state({"last_checked_at": now}, error=f"Could not check for updates: {exc}")


def download_update() -> dict[str, Any]:
    state = check_for_updates(force=True)
    if not state.get("update_available"):
        return _public_state(state, error="No newer stable update is available.")
    asset = state.get("asset") or {}
    url = asset.get("download_url") or ""
    if not url:
        return _public_state(state, error="The GitHub release does not include an installer asset.")
    os.makedirs(UPDATE_DIR, exist_ok=True)
    latest = str(state.get("latest_version") or "latest").replace("/", "-")
    installer_path = os.path.join(UPDATE_DIR, f"ArcadiaCoreSetup-v{latest}.exe")
    try:
        with requests.get(url, headers=HEADERS, timeout=max(REQUEST_TIMEOUT, 30), stream=True) as response:
            response.raise_for_status()
            with open(installer_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        fh.write(chunk)
        state.update({
            "downloaded": True,
            "installer_path": installer_path,
            "downloaded_at": int(time.time()),
            "error": "",
        })
        _write_state(state)
        return _public_state(state)
    except Exception as exc:
        return _public_state(state, error=f"Could not download update: {exc}")


def launch_installer(active_downloads: int = 0) -> dict[str, Any]:
    state = _public_state()
    installer_path = state.get("installer_path") or ""
    if not installer_path or not os.path.exists(installer_path):
        return _public_state(state, error="Update installer has not been downloaded yet.")
    try:
        subprocess.Popen([installer_path], close_fds=True)
        state.update({
            "installer_launched_at": int(time.time()),
            "active_downloads_when_launched": int(active_downloads or 0),
            "error": "",
        })
        _write_state(state)
        return {"success": True, **_public_state(state)}
    except Exception as exc:
        return _public_state(state, error=f"Could not launch installer: {exc}")
