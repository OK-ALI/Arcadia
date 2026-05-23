"""
downloader.py - Built-in libtorrent download manager for Arcadia Core.

This manager keeps torrent work in-process through libtorrent. There is no
external downloader child process, RPC port, or legacy session file involved.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import atexit
import re
import ctypes
import threading
import requests
from pathlib import Path
from typing import Any

try:
    import libtorrent as lt
except Exception as exc:  # pragma: no cover - surfaced through engine_info
    lt = None
    LIBTORRENT_IMPORT_ERROR = str(exc)
else:
    LIBTORRENT_IMPORT_ERROR = ""

from backend.config import DATA_DIR
from backend.download_capture import (
    file_url_name,
    filename_from_content_disposition,
    safe_filename,
    safe_join_file,
    validate_capture_url,
)


STATE_FILE = os.path.join(DATA_DIR, "downloads_state.json")
RESUME_DIR = os.path.join(DATA_DIR, "resume_data")
DEFAULT_DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
TEMP_TORRENT_DIR = os.path.join(DATA_DIR, "temp_torrents")
PRIORITY_RANK = {
    "Urgent": 0,
    "High": 1,
    "Normal": 2,
    "Low": 3,
    "Paused": 4,
}
LT_FILE_PRIORITY = 4


def _now() -> float:
    return time.time()


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _normalize_path(path: str | None) -> str:
    value = str(path or "").strip().strip('"')
    return os.path.abspath(os.path.expanduser(value)) if value else ""


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: str, data):
    _ensure_dir(os.path.dirname(path))
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _parse_info_hash(magnet: str) -> str:
    marker = "btih:"
    lower = magnet.lower()
    idx = lower.find(marker)
    if idx == -1:
        return hashlib.sha1(magnet.encode("utf-8")).hexdigest()
    value = magnet[idx + len(marker):].split("&", 1)[0].split("%", 1)[0]
    return value.strip().lower() or hashlib.sha1(magnet.encode("utf-8")).hexdigest()


def _human_state(status) -> str:
    if not status:
        return "queued"
    if getattr(status, "paused", False):
        return "paused"
    state = int(getattr(status, "state", 0))
    if getattr(status, "is_seeding", False):
        return "completed"
    if state in {3, 4}:
        return "downloading"
    if state in {1, 2}:
        return "metadata"
    if state == 5:
        return "completed"
    if state == 6:
        return "checking"
    if state == 7:
        return "error"
    return "queued"


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_uint32),
        ("BatteryFullLifeTime", ctypes.c_uint32),
    ]


def _battery_status() -> dict[str, Any]:
    try:
        status = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            percent = int(status.BatteryLifePercent)
            has_battery = percent != 255
            return {
                "has_battery": has_battery,
                "percent": percent if has_battery else None,
                "plugged_in": int(status.ACLineStatus) == 1,
            }
    except Exception:
        pass
    return {"has_battery": False, "percent": None, "plugged_in": True}


class HTTPDownloadWorker(threading.Thread):
    def __init__(self, item: dict, manager: DownloaderManager):
        super().__init__(daemon=True)
        self.item = item
        self.manager = manager
        self.url = item["magnet"]
        self.save_path = item["save_path"]
        self.filename = item["title"]
        self.info_hash = item["info_hash"]
        self.stop_event = threading.Event()
        self.error = ""
        
    def run(self):
        try:
            os.makedirs(self.save_path, exist_ok=True)
            self.filename = safe_filename(self.filename)
            dest_file = self.item.get("file_path") or safe_join_file(self.save_path, self.filename)
            self.item["file_path"] = dest_file
            
            completed = self.item.get("completed_length", 0)
            headers = {"User-Agent": "Mozilla/5.0"}
            if completed > 0 and os.path.exists(dest_file):
                headers["Range"] = f"bytes={completed}-"
                mode = "ab"
            else:
                completed = 0
                mode = "wb"
                
            resp = requests.get(self.url, headers=headers, stream=True, timeout=15, allow_redirects=True)
            if completed > 0 and resp.status_code != 206:
                completed = 0
                mode = "wb"
            
            if completed == 0:
                total_len = int(resp.headers.get("Content-Length", 0))
                self.item["total_length"] = total_len
                disp = resp.headers.get("Content-Disposition", "")
                header_name = filename_from_content_disposition(disp)
                if header_name:
                    self.filename = header_name
                    self.item["title"] = self.filename
                    dest_file = safe_join_file(self.save_path, self.filename)
                    self.item["file_path"] = dest_file
                self.item["files"] = [{
                    "index": "1",
                    "path": self.filename,
                    "name": self.filename,
                    "length": total_len,
                    "completed_length": 0,
                    "selected": True,
                    "state": "Selected"
                }]
            
            resp.raise_for_status()
            
            last_time = time.time()
            last_bytes = completed
            self.item["status"] = "downloading"
            
            with open(dest_file, mode) as f:
                for chunk in resp.iter_content(chunk_size=524288):
                    if self.stop_event.is_set():
                        break
                    if chunk:
                        f.write(chunk)
                        completed += len(chunk)
                        self.item["completed_length"] = completed
                        if self.item.get("files"):
                            self.item["files"][0]["completed_length"] = completed
                        
                        now = time.time()
                        diff = now - last_time
                        if diff >= 1.0:
                            speed = int((completed - last_bytes) / diff)
                            self.item["download_speed"] = speed
                            last_bytes = completed
                            last_time = now
                            self.manager._save_state()
                            
            self.item["download_speed"] = 0
            if self.stop_event.is_set():
                self.item["status"] = "paused"
            else:
                self.item["status"] = "completed"
                self.item["completed_at"] = time.time()
                if self.item.get("files"):
                    self.item["files"][0]["completed_length"] = completed
                    self.item["files"][0]["state"] = "Downloaded"
            self.manager._save_state()
        except Exception as e:
            self.error = str(e)
            self.item["status"] = "error"
            self.item["last_error"] = str(e)
            self.item["download_speed"] = 0
            self.manager._save_state()
        finally:
            self.manager.http_threads.pop(self.info_hash, None)

    def stop(self):
        self.stop_event.set()


class DownloaderManager:
    def __init__(self):
        _ensure_dir(DATA_DIR)
        _ensure_dir(DEFAULT_DOWNLOAD_DIR)
        _ensure_dir(RESUME_DIR)
        _ensure_dir(TEMP_TORRENT_DIR)
        self.session = None
        self.handles: dict[str, Any] = {}
        self.http_threads: dict[str, HTTPDownloadWorker] = {}
        self.state = self._load_state()
        self.battery_guard_active = False
        self._migrate_state()
        atexit.register(self.shutdown)

    def _load_state(self) -> dict[str, Any]:
        state = _read_json(STATE_FILE, {})
        state.setdefault("settings", {
            "max_active_downloads": 3,
            "download_limit": "0",
            "upload_limit": "0",
            "default_save_path": DEFAULT_DOWNLOAD_DIR,
        })
        state.setdefault("downloads", [])
        state.setdefault("prepared", {})
        state.setdefault("battery_guard", {"paused": False, "message": ""})
        return state

    def _migrate_state(self):
        settings = self.state.setdefault("settings", {})
        default_path = str(settings.get("default_save_path") or "")
        if "GamesDownloader_from_fitgirl" in default_path:
            settings["default_save_path"] = DEFAULT_DOWNLOAD_DIR
        settings.setdefault("engine", "libtorrent")
        self.state["prepared"] = {}
        for item in self.state.get("downloads", []):
            if "already registered" in str(item.get("last_error", "")).lower():
                item["last_error"] = ""
            item.pop("gid", None)
            item.setdefault("engine", "libtorrent")
            if item.get("priority") == "Paused" or item.get("status") == "paused":
                item["user_paused"] = True
        self._save_state()

    def _save_state(self):
        _write_json(STATE_FILE, self.state)


    def _resume_path(self, info_hash: str) -> str:
        safe = re.sub(r"[^a-fA-F0-9]", "", info_hash or "") or hashlib.sha1(str(info_hash).encode("utf-8")).hexdigest()
        return os.path.join(RESUME_DIR, f"{safe.lower()}.fastresume")

    def _read_resume_data(self, info_hash: str):
        if lt is None:
            return None
        path = self._resume_path(info_hash)
        if not os.path.exists(path):
            return None
        try:
            data = Path(path).read_bytes()
            return lt.read_resume_data(data)
        except Exception:
            return None

    def _write_resume_data(self, info_hash: str, data: bytes):
        try:
            _ensure_dir(RESUME_DIR)
            Path(self._resume_path(info_hash)).write_bytes(bytes(data))
        except Exception:
            pass

    def _drain_alerts(self, timeout: float = 0.2):
        if not self.session:
            return
        end = time.time() + timeout
        while time.time() <= end:
            try:
                alerts = self.session.pop_alerts()
            except Exception:
                return
            for alert in alerts:
                if lt and isinstance(alert, lt.save_resume_data_alert):
                    try:
                        info_hash = str(alert.handle.info_hash()).lower()
                        self._write_resume_data(info_hash, lt.write_resume_data_buf(alert.params))
                    except Exception:
                        pass
                elif lt and isinstance(alert, lt.save_resume_data_failed_alert):
                    try:
                        item = self._download_by_hash(str(alert.handle.info_hash()).lower())
                        if item:
                            item["last_error"] = str(alert.message())
                    except Exception:
                        pass
            if time.time() >= end:
                break
            time.sleep(0.05)

    def save_resume_data(self, wait: bool = False):
        if not self.session:
            return
        for info_hash, handle in list(self.handles.items()):
            try:
                if handle and handle.is_valid():
                    handle.save_resume_data(lt.torrent_handle.save_info_dict)
            except Exception:
                pass
        self._drain_alerts(2.0 if wait else 0.15)
        self._save_state()

    def shutdown(self):
        for info_hash, worker in list(self.http_threads.items()):
            worker.stop()
        for info_hash, worker in list(self.http_threads.items()):
            worker.join(timeout=1.0)
        self.save_resume_data(wait=True)

    def _apply_battery_guard(self):
        battery = _battery_status()
        guard = self.state.setdefault("battery_guard", {"paused": False, "message": ""})
        if battery.get("has_battery") and not battery.get("plugged_in") and battery.get("percent") is not None and battery["percent"] < 20:
            message = f"Downloads paused: battery is {battery['percent']}%."
            guard.update({"paused": True, "message": message, "battery": battery})
            for item in self.state.get("downloads", []):
                handle = self.handles.get(item.get("info_hash"))
                if handle:
                    try:
                        handle.pause()
                    except Exception:
                        pass
                if item.get("status") in {"downloading", "queued", "metadata", "checking"}:
                    item["status"] = "paused"
                    item["battery_paused"] = True
                    item["user_paused"] = True
                    item["last_error"] = message
            return True
        if guard.get("paused"):
            guard.update({"paused": False, "message": "", "battery": battery})
        return False

    def _download_by_hash(self, info_hash: str) -> dict[str, Any] | None:
        wanted = (info_hash or "").lower()
        for item in self.state["downloads"]:
            if str(item.get("info_hash", "")).lower() == wanted:
                return item
        return None

    def _pause_handle(self, handle):
        if not handle:
            return
        try:
            if lt and hasattr(lt, "torrent_flags"):
                handle.unset_flags(lt.torrent_flags.auto_managed)
        except Exception:
            pass
        try:
            handle.pause()
        except Exception:
            pass

    def _resume_handle(self, handle):
        if not handle:
            return
        try:
            if lt and hasattr(lt, "torrent_flags"):
                handle.unset_flags(lt.torrent_flags.auto_managed)
        except Exception:
            pass
        try:
            handle.resume()
        except Exception:
            pass

    def _is_user_paused(self, item: dict[str, Any]) -> bool:
        return bool(item.get("user_paused")) or item.get("priority") == "Paused"

    def ensure_engine(self):
        if lt is None:
            raise RuntimeError(f"libtorrent is not available: {LIBTORRENT_IMPORT_ERROR}")
        if self.session is not None:
            return
        settings_pack = {
            "listen_interfaces": "0.0.0.0:6881,[::]:6881",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "alert_mask": int(lt.alert.category_t.error_notification) | int(lt.alert.category_t.status_notification),
            "active_downloads": int(self.state["settings"].get("max_active_downloads", 3) or 3),
            "active_seeds": 2,
            "active_limit": max(4, int(self.state["settings"].get("max_active_downloads", 3) or 3) + 2),
        }
        self.session = lt.session(settings_pack)
        try:
            self.session.add_dht_router("router.bittorrent.com", 6881)
            self.session.add_dht_router("router.utorrent.com", 6881)
            self.session.add_dht_router("dht.transmissionbt.com", 6881)
        except Exception:
            pass
        self._apply_speed_limits()
        self._restore_download_handles()

    def _apply_speed_limits(self):
        if not self.session:
            return
        down = self._limit_to_bytes(self.state["settings"].get("download_limit"))
        up = self._limit_to_bytes(self.state["settings"].get("upload_limit"))
        try:
            self.session.apply_settings({
                "download_rate_limit": down,
                "upload_rate_limit": up,
                "active_downloads": int(self.state["settings"].get("max_active_downloads", 3) or 3),
            })
        except Exception:
            pass

    def _limit_to_bytes(self, value: str | int | None) -> int:
        raw = str(value or "0").strip().lower()
        if raw in {"", "0", "unlimited"}:
            return 0
        mult = 1024
        if raw.endswith("mb") or raw.endswith("m"):
            mult = 1024 * 1024
        number = raw.rstrip("kbps/mbs ").rstrip("km")
        try:
            return max(0, int(float(number) * mult))
        except ValueError:
            return 0

    def engine_info(self) -> dict[str, Any]:
        return {
            "available": lt is not None,
            "path": "libtorrent in-process engine",
            "running": self.session is not None,
            "version": getattr(lt, "version", "") if lt else "",
            "engine": "libtorrent",
            "error": LIBTORRENT_IMPORT_ERROR,
        }

    def _add_magnet(self, magnet: str, save_path: str):
        self.ensure_engine()
        save_path = _normalize_path(save_path or self.state["settings"].get("default_save_path") or DEFAULT_DOWNLOAD_DIR)
        info_hash = _parse_info_hash(magnet)
        handle = self.handles.get(info_hash)
        if handle and handle.is_valid():
            return handle
        resume_params = self._read_resume_data(info_hash)
        if resume_params:
            params = resume_params
            if save_path:
                params.save_path = save_path
        else:
            params = lt.parse_magnet_uri(magnet)
            params.save_path = save_path
        _ensure_dir(params.save_path)
        handle = self.session.add_torrent(params)
        self.handles[info_hash] = handle
        return handle

    def _start_http_download(self, item: dict):
        info_hash = item.get("info_hash")
        if not info_hash:
            return
        worker = self.http_threads.get(info_hash)
        if worker and worker.is_alive():
            return
        item["status"] = "downloading"
        worker = HTTPDownloadWorker(item, self)
        self.http_threads[info_hash] = worker
        worker.start()

    def _stop_http_download(self, info_hash: str):
        worker = self.http_threads.pop(info_hash, None)
        if worker:
            worker.stop()

    def _restore_download_handles(self):
        for item in self.state.get("downloads", []):
            if item.get("engine") == "http":
                if not self._is_user_paused(item) and item.get("status") in {"downloading", "queued"}:
                    self._start_http_download(item)
                else:
                    item["status"] = "paused"
                continue

            magnet = item.get("magnet")
            if not magnet:
                continue
            try:
                handle = self._add_magnet(magnet, item.get("save_path") or self.state["settings"].get("default_save_path") or DEFAULT_DOWNLOAD_DIR)
                self._apply_file_selection(handle, item.get("selected_file_indexes", []))
                if self._is_user_paused(item) or item.get("status") == "paused":
                    item["user_paused"] = True
                    self._pause_handle(handle)
                else:
                    self._resume_handle(handle)
            except Exception as exc:
                item["last_error"] = str(exc)

    def _files_from_handle(self, handle, item: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return []
        selected = {str(x) for x in (item or {}).get("selected_file_indexes", [])}
        status = handle.status()
        info = handle.get_torrent_info()
        storage = info.files()
        priorities = list(handle.get_file_priorities()) if hasattr(handle, "get_file_priorities") else []
        progress = []
        try:
            progress = list(handle.file_progress())
        except Exception:
            progress = []
        files = []
        for i in range(storage.num_files()):
            index = str(i + 1)
            size = int(storage.file_size(i))
            path = storage.file_path(i)
            priority = int(priorities[i]) if i < len(priorities) else LT_FILE_PRIORITY
            completed = int(progress[i]) if i < len(progress) else 0
            is_selected = priority > 0 or index in selected
            if completed >= size and size > 0:
                state = "Downloaded"
            elif is_selected:
                state = "Selected"
            elif completed:
                state = "Partial"
            else:
                state = "Not selected"
            files.append({
                "index": index,
                "path": path,
                "name": os.path.basename(path) or path,
                "length": size,
                "completed_length": completed,
                "selected": is_selected,
                "state": state,
            })
        return files

    def _torrent_name(self, handle, fallback: str) -> str:
        try:
            if handle and handle.is_valid() and handle.has_metadata():
                return handle.get_torrent_info().name() or fallback
        except Exception:
            pass
        return fallback

    def _prepared_payload(self, prepared: dict[str, Any]) -> dict[str, Any]:
        handle = self.handles.get(prepared.get("info_hash"))
        if handle and handle.is_valid():
            prepared["files"] = self._files_from_handle(handle)
            prepared["title"] = self._torrent_name(handle, prepared.get("title", "Prepared Download"))
            prepared["metadata_ready"] = bool(prepared["files"])
            self._save_state()
        return {
            "mode": prepared.get("mode", "new"),
            "prepared_id": prepared.get("prepared_id"),
            "info_hash": prepared.get("info_hash"),
            "title": prepared.get("title"),
            "save_path": prepared.get("save_path"),
            "files": prepared.get("files", []),
            "engine": self.engine_info(),
            "metadata_ready": bool(prepared.get("files")),
            "metadata_status": "ready" if prepared.get("files") else "loading",
        }

    def prepare_download(self, slug: str, title: str, magnet: str, save_path: str | None = None) -> dict[str, Any]:
        validate_capture_url(magnet)
        info_hash = _parse_info_hash(magnet)
        existing = self._download_by_hash(info_hash)
        if existing:
            handle = self.handles.get(info_hash)
            if not handle:
                handle = self._add_magnet(existing.get("magnet") or magnet, existing.get("save_path") or save_path or DEFAULT_DOWNLOAD_DIR)
            files = self._files_from_handle(handle, existing)
            return {
                "mode": "update",
                "info_hash": info_hash,
                "existing": existing,
                "files": files,
                "engine": self.engine_info(),
                "metadata_ready": bool(files),
                "metadata_status": "ready" if files else "loading",
            }

        target_dir = _normalize_path(save_path or self.state["settings"].get("default_save_path") or DEFAULT_DOWNLOAD_DIR)
        handle = self._add_magnet(magnet, target_dir)
        deadline = time.time() + 12
        files = []
        while time.time() < deadline:
            files = self._files_from_handle(handle)
            if files:
                break
            time.sleep(0.5)
        prepared_id = hashlib.sha1(f"{info_hash}:{time.time()}".encode("utf-8")).hexdigest()[:16]
        prepared = {
            "mode": "new",
            "prepared_id": prepared_id,
            "slug": slug,
            "title": self._torrent_name(handle, title),
            "magnet": magnet,
            "info_hash": info_hash,
            "save_path": target_dir,
            "files": files,
            "created_at": _now(),
            "metadata_ready": bool(files),
        }
        self.state["prepared"][prepared_id] = prepared
        self._save_state()
        return self._prepared_payload(prepared)

    def prepare_torrent_file_url(self, url: str, save_path: str | None = None, slug: str | None = None) -> dict[str, Any]:
        meta = validate_capture_url(url)
        if meta["type"] != "torrent_file":
            raise ValueError("Expected an HTTP/HTTPS .torrent URL.")
        if lt is None:
            raise RuntimeError(f"libtorrent is not available: {LIBTORRENT_IMPORT_ERROR}")
        self.ensure_engine()
        _ensure_dir(TEMP_TORRENT_DIR)
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        torrent_path = os.path.join(TEMP_TORRENT_DIR, f"{digest}.torrent")
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20, allow_redirects=True)
            response.raise_for_status()
            if len(response.content) > 20 * 1024 * 1024:
                raise ValueError("Torrent file is too large.")
            Path(torrent_path).write_bytes(response.content)
            info = lt.torrent_info(torrent_path)
        except Exception as exc:
            raise ValueError(f"Could not load torrent file: {exc}") from exc

        info_hash = str(info.info_hash()).lower()
        existing = self._download_by_hash(info_hash)
        target_dir = _normalize_path(save_path or self.state["settings"].get("default_save_path") or DEFAULT_DOWNLOAD_DIR)
        if existing:
            handle = self.handles.get(info_hash)
            if not handle:
                params = lt.add_torrent_params()
                params.ti = info
                params.save_path = existing.get("save_path") or target_dir
                handle = self.session.add_torrent(params)
                self.handles[info_hash] = handle
                self._pause_handle(handle)
            files = self._files_from_handle(handle, existing)
            return {
                "mode": "update",
                "info_hash": info_hash,
                "existing": existing,
                "files": files,
                "engine": self.engine_info(),
                "metadata_ready": bool(files),
                "metadata_status": "ready" if files else "loading",
            }

        params = lt.add_torrent_params()
        params.ti = info
        params.save_path = target_dir
        _ensure_dir(params.save_path)
        handle = self.session.add_torrent(params)
        self.handles[info_hash] = handle
        self._pause_handle(handle)
        try:
            handle.prioritize_files([0 for _ in range(info.num_files())])
        except Exception:
            pass
        files = self._files_from_handle(handle)
        prepared_id = hashlib.sha1(f"{info_hash}:{time.time()}".encode("utf-8")).hexdigest()[:16]
        prepared = {
            "mode": "new",
            "prepared_id": prepared_id,
            "slug": slug or "direct-torrent",
            "title": self._torrent_name(handle, info.name() or "Torrent Download"),
            "magnet": url,
            "info_hash": info_hash,
            "save_path": target_dir,
            "files": files,
            "created_at": _now(),
            "metadata_ready": bool(files),
            "torrent_file": torrent_path,
        }
        self.state["prepared"][prepared_id] = prepared
        self._save_state()
        return self._prepared_payload(prepared)

    def prepare_status(self, prepared_id: str) -> dict[str, Any]:
        prepared = self.state.get("prepared", {}).get(prepared_id)
        if not prepared:
            raise ValueError("Prepared download expired. Please prepare it again.")
        return self._prepared_payload(prepared)

    def _apply_file_selection(self, handle, selected_indexes: list[str]):
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return
        selected = {int(x) - 1 for x in selected_indexes if str(x).isdigit()}
        info = handle.get_torrent_info()
        priorities = [LT_FILE_PRIORITY if i in selected else 0 for i in range(info.num_files())]
        handle.prioritize_files(priorities)

    def confirm_download(
        self,
        prepared_id: str | None,
        info_hash: str,
        selected_indexes: list[str],
        save_path: str,
        priority: str,
        queue_position: str = "normal",
    ) -> dict[str, Any]:
        if self._apply_battery_guard():
            raise ValueError(self.state.get("battery_guard", {}).get("message") or "Downloads are paused because battery is low.")
        selected_indexes = [str(i) for i in selected_indexes if str(i)]
        if not selected_indexes:
            raise ValueError("Select at least one file before adding the download.")
        save_path = _normalize_path(save_path)
        self.ensure_engine()
        existing = self._download_by_hash(info_hash)
        if existing:
            handle = self.handles.get(info_hash)
            if not handle:
                handle = self._add_magnet(existing.get("magnet", ""), existing.get("save_path") or save_path)
            merged = sorted(set(existing.get("selected_file_indexes", [])) | set(selected_indexes), key=lambda x: int(x))
            existing["selected_file_indexes"] = merged
            existing["priority"] = priority
            existing["save_path"] = save_path or existing.get("save_path")
            existing["updated_at"] = _now()
            self._apply_file_selection(handle, merged)
            if priority == "Paused":
                existing["user_paused"] = True
                self._pause_handle(handle)
            else:
                existing["user_paused"] = False
                self._resume_handle(handle)
            existing["last_error"] = ""
            self._save_state()
            return existing

        prepared = self.state["prepared"].pop(prepared_id or "", None)
        if not prepared:
            raise ValueError("Prepared download expired. Please prepare it again.")
        handle = self.handles.get(info_hash)
        if not handle:
            if prepared.get("torrent_file"):
                params = lt.add_torrent_params()
                params.ti = lt.torrent_info(prepared["torrent_file"])
                params.save_path = _normalize_path(save_path or prepared.get("save_path") or DEFAULT_DOWNLOAD_DIR)
                _ensure_dir(params.save_path)
                handle = self.session.add_torrent(params)
                self.handles[info_hash] = handle
            else:
                handle = self._add_magnet(prepared["magnet"], save_path or prepared.get("save_path") or DEFAULT_DOWNLOAD_DIR)
        files = self._files_from_handle(handle, {"selected_file_indexes": selected_indexes})
        if not files:
            self.state["prepared"][prepared_id or ""] = prepared
            raise ValueError("Torrent metadata is still loading. Please wait for the file list to appear.")
        self._apply_file_selection(handle, selected_indexes)
        if priority == "Paused":
            self._pause_handle(handle)
        else:
            self._resume_handle(handle)
        item = {
            "id": info_hash,
            "info_hash": info_hash,
            "slug": prepared.get("slug", ""),
            "title": self._torrent_name(handle, prepared.get("title", "Download")),
            "magnet": prepared.get("magnet", ""),
            "save_path": _normalize_path(save_path or prepared.get("save_path") or DEFAULT_DOWNLOAD_DIR),
            "selected_file_indexes": selected_indexes,
            "priority": priority,
            "manual_order": self._next_order(priority),
            "status": "paused" if priority == "Paused" else "queued",
            "user_paused": priority == "Paused",
            "files": files,
            "engine": "libtorrent",
            "created_at": _now(),
            "updated_at": _now(),
            "completed_at": None,
            "last_error": "",
        }
        self.state["downloads"].append(item)
        self._sort_downloads()
        self.save_resume_data(wait=False)
        self._save_state()
        return item

    def add_http_download(
        self,
        url: str,
        save_path: str | None = None,
        slug: str | None = None,
        priority: str = "Normal",
        start_paused: bool = False,
    ) -> dict[str, Any]:
        if self._apply_battery_guard():
            raise ValueError(self.state.get("battery_guard", {}).get("message") or "Downloads are paused because battery is low.")
        meta = validate_capture_url(url)
        if meta["type"] != "http_file":
            raise ValueError("Expected a direct HTTP/HTTPS file URL.")
        if priority not in PRIORITY_RANK:
            priority = "Normal"
        info_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
        existing = self._download_by_hash(info_hash)
        if existing:
            if existing.get("status") == "paused" and not start_paused:
                existing["user_paused"] = False
                existing["status"] = "queued"
                self._start_http_download(existing)
            return existing

        filename = file_url_name(url)

        target_dir = _normalize_path(save_path or self.state["settings"].get("default_save_path") or DEFAULT_DOWNLOAD_DIR)
        _ensure_dir(target_dir)
        file_path = safe_join_file(target_dir, filename)

        item = {
            "id": info_hash,
            "info_hash": info_hash,
            "slug": slug or "",
            "title": filename,
            "magnet": url,
            "save_path": target_dir,
            "file_path": file_path,
            "selected_file_indexes": ["1"],
            "priority": "Paused" if start_paused else priority,
            "manual_order": self._next_order("Paused" if start_paused else priority),
            "status": "paused" if start_paused else "queued",
            "user_paused": bool(start_paused),
            "files": [{
                "index": "1",
                "path": filename,
                "name": filename,
                "length": 0,
                "completed_length": 0,
                "selected": True,
                "state": "Selected"
            }],
            "engine": "http",
            "created_at": _now(),
            "updated_at": _now(),
            "completed_at": None,
            "last_error": "",
            "completed_length": 0,
            "total_length": 0,
        }
        self.state["downloads"].append(item)
        self._sort_downloads()
        if not start_paused:
            self._start_http_download(item)
        self._save_state()
        return item

    def _next_order(self, priority: str) -> int:
        orders = [int(x.get("manual_order", 0)) for x in self.state["downloads"] if x.get("priority") == priority]
        return (max(orders) + 1) if orders else 1

    def _sort_downloads(self):
        self.state["downloads"].sort(key=lambda x: (
            PRIORITY_RANK.get(x.get("priority", "Normal"), 2),
            int(x.get("manual_order", 0)),
            float(x.get("created_at", 0)),
        ))

    def list_status(self) -> dict[str, Any]:
        engine = self.engine_info()
        if engine["available"]:
            try:
                self.ensure_engine()
            except Exception as exc:
                engine["last_error"] = str(exc)
        battery_paused = self._apply_battery_guard()
        for item in self.state["downloads"]:
            if item.get("engine") == "http":
                info_hash = item.get("info_hash")
                item["seeders"] = 0
                item["connections"] = 0
                item["upload_speed"] = 0
                if not item.get("files"):
                    filename = item.get("title", "download")
                    item["files"] = [{
                        "index": "1",
                        "path": filename,
                        "name": filename,
                        "length": item.get("total_length", 0),
                        "completed_length": item.get("completed_length", 0),
                        "selected": True,
                        "state": "Selected" if item.get("status") != "completed" else "Downloaded"
                    }]
                if battery_paused or self._is_user_paused(item):
                    self._stop_http_download(info_hash)
                    item["status"] = "paused"
                    item["download_speed"] = 0
                    if battery_paused:
                        item["battery_paused"] = True
                    continue
                
                worker = self.http_threads.get(info_hash)
                if worker and worker.is_alive():
                    item["status"] = "downloading"
                else:
                    if item.get("status") in {"downloading", "queued"}:
                        self._start_http_download(item)
                    elif item.get("status") == "completed" and not item.get("completed_at"):
                        item["completed_at"] = _now()
                        if item.get("files"):
                            item["files"][0]["state"] = "Downloaded"
                continue

            if battery_paused:
                continue
            handle = self.handles.get(item.get("info_hash"))
            if not handle or not handle.is_valid():
                if item.get("magnet"):
                    try:
                        handle = self._add_magnet(item["magnet"], item.get("save_path") or DEFAULT_DOWNLOAD_DIR)
                    except Exception as exc:
                        item["last_error"] = str(exc)
                        continue
                else:
                    continue
            if self._is_user_paused(item) or item.get("battery_paused"):
                self._pause_handle(handle)
                status = handle.status()
                item["status"] = "paused"
                item["download_speed"] = 0
                item["upload_speed"] = 0
                item["seeders"] = int(getattr(status, "num_seeds", 0) or 0)
                item["connections"] = int(getattr(status, "num_peers", 0) or 0)
                item["total_length"] = int(getattr(status, "total_wanted", 0) or getattr(status, "total", 0) or item.get("total_length", 0) or 0)
                item["completed_length"] = int(getattr(status, "total_wanted_done", 0) or item.get("completed_length", 0) or 0)
                item["files"] = self._files_from_handle(handle, item) or item.get("files", [])
                continue
            status = handle.status()
            item["status"] = _human_state(status)
            item["total_length"] = int(getattr(status, "total_wanted", 0) or getattr(status, "total", 0) or 0)
            item["completed_length"] = int(getattr(status, "total_wanted_done", 0) or 0)
            item["download_speed"] = int(getattr(status, "download_rate", 0) or 0)
            item["upload_speed"] = int(getattr(status, "upload_rate", 0) or 0)
            item["seeders"] = int(getattr(status, "num_seeds", 0) or 0)
            item["connections"] = int(getattr(status, "num_peers", 0) or 0)
            item["files"] = self._files_from_handle(handle, item) or item.get("files", [])
            if item["status"] == "completed" and not item.get("completed_at"):
                item["completed_at"] = _now()
        self._sort_downloads()
        self.save_resume_data(wait=False)
        self._save_state()
        return {"engine": self.engine_info(), "settings": self.state["settings"], "downloads": self.state["downloads"], "battery_guard": self.state.get("battery_guard", {})}

    def control(self, info_hash: str, action: str) -> dict[str, Any]:
        item = self._download_by_hash(info_hash)
        if not item:
            raise ValueError("Download not found.")
        
        if item.get("engine") == "http":
            if action == "pause":
                self._stop_http_download(info_hash)
                item["status"] = "paused"
                item["user_paused"] = True
                item["download_speed"] = 0
            elif action in {"resume", "retry"}:
                if self._apply_battery_guard():
                    raise ValueError(self.state.get("battery_guard", {}).get("message") or "Downloads are paused because battery is low.")
                item["user_paused"] = False
                item.pop("battery_paused", None)
                item["last_error"] = ""
                self._start_http_download(item)
            elif action == "remove":
                self._stop_http_download(info_hash)
                self.state["downloads"] = [x for x in self.state["downloads"] if x.get("info_hash") != info_hash]
            elif action == "delete-files":
                self._stop_http_download(info_hash)
                dest_file = item.get("file_path") or safe_join_file(item.get("save_path") or DEFAULT_DOWNLOAD_DIR, item.get("title") or "download")
                try:
                    save_root = os.path.abspath(item.get("save_path") or DEFAULT_DOWNLOAD_DIR)
                    dest_file = os.path.abspath(dest_file)
                    if os.path.commonpath([save_root, dest_file]) == save_root and os.path.exists(dest_file):
                        os.remove(dest_file)
                except OSError:
                    pass
                self.state["downloads"] = [x for x in self.state["downloads"] if x.get("info_hash") != info_hash]
            elif action == "open-folder":
                save_path = item.get("save_path")
                if save_path and os.path.exists(save_path):
                    os.startfile(save_path)
            else:
                raise ValueError("Unknown download action.")
            self._save_state()
            return item

        self.ensure_engine()
        handle = self.handles.get(info_hash)
        if not handle and item.get("magnet"):
            handle = self._add_magnet(item["magnet"], item.get("save_path") or DEFAULT_DOWNLOAD_DIR)
        if action == "pause":
            self._pause_handle(handle)
            item["status"] = "paused"
            item["user_paused"] = True
            item["download_speed"] = 0
            item["upload_speed"] = 0
        elif action in {"resume", "retry"}:
            if self._apply_battery_guard():
                raise ValueError(self.state.get("battery_guard", {}).get("message") or "Downloads are paused because battery is low.")
            item["user_paused"] = False
            self._resume_handle(handle)
            item["status"] = "queued"
            item.pop("battery_paused", None)
            item["last_error"] = ""
        elif action == "remove":
            if handle and handle.is_valid() and self.session:
                self.session.remove_torrent(handle)
            self.handles.pop(info_hash, None)
            try:
                os.remove(self._resume_path(info_hash))
            except OSError:
                pass
            self.state["downloads"] = [x for x in self.state["downloads"] if x.get("info_hash") != info_hash]
        elif action == "delete-files":
            if handle and handle.is_valid() and self.session:
                self.session.remove_torrent(handle, lt.options_t.delete_files)
            self.handles.pop(info_hash, None)
            try:
                os.remove(self._resume_path(info_hash))
            except OSError:
                pass
            self.state["downloads"] = [x for x in self.state["downloads"] if x.get("info_hash") != info_hash]
        elif action == "open-folder":
            save_path = item.get("save_path")
            if save_path and os.path.exists(save_path):
                os.startfile(save_path)
        else:
            raise ValueError("Unknown download action.")
        self.save_resume_data(wait=False)
        self._save_state()
        return item

    def set_priority(self, info_hash: str, priority: str) -> dict[str, Any]:
        if priority not in PRIORITY_RANK:
            raise ValueError("Invalid priority.")
        item = self._download_by_hash(info_hash)
        if not item:
            raise ValueError("Download not found.")
        item["priority"] = priority
        item["manual_order"] = self._next_order(priority)
        item["updated_at"] = _now()
        handle = self.handles.get(info_hash)
        if handle:
            if priority == "Paused":
                item["user_paused"] = True
                self._pause_handle(handle)
                item["status"] = "paused"
            else:
                item["user_paused"] = False
                self._resume_handle(handle)
        self._sort_downloads()
        self.save_resume_data(wait=False)
        self._save_state()
        return item

    def reorder(self, info_hash: str, direction: str) -> list[dict[str, Any]]:
        self._sort_downloads()
        item = self._download_by_hash(info_hash)
        if not item:
            raise ValueError("Download not found.")
        same = [x for x in self.state["downloads"] if x.get("priority") == item.get("priority")]
        idx = same.index(item)
        swap_idx = idx - 1 if direction == "up" else idx + 1
        if 0 <= swap_idx < len(same):
            other = same[swap_idx]
            item["manual_order"], other["manual_order"] = other.get("manual_order", 0), item.get("manual_order", 0)
        self._sort_downloads()
        self._save_state()
        return self.state["downloads"]

    def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        current = self.state["settings"]
        for key in ("max_active_downloads", "download_limit", "upload_limit", "default_save_path"):
            if key in settings:
                value = settings[key]
                if key == "default_save_path" and value:
                    value = _normalize_path(value)
                current[key] = value
        current["engine"] = "libtorrent"
        if current.get("default_save_path"):
            _ensure_dir(current["default_save_path"])
        self._apply_speed_limits()
        self._save_state()
        return current

    def pause_all(self):
        self.ensure_engine()
        for item in self.state["downloads"]:
            handle = self.handles.get(item.get("info_hash"))
            self._pause_handle(handle)
            if item.get("status") in {"downloading", "queued", "metadata"}:
                item["status"] = "paused"
            item["user_paused"] = True
        self.save_resume_data(wait=False)
        self._save_state()

    def resume_all(self):
        self.ensure_engine()
        if self._apply_battery_guard():
            return
        for item in self.state["downloads"]:
            handle = self.handles.get(item.get("info_hash"))
            if handle and item.get("priority") != "Paused":
                self._resume_handle(handle)
            if item.get("status") == "paused" and item.get("priority") != "Paused":
                item["status"] = "queued"
                item["user_paused"] = False
                item.pop("battery_paused", None)
                if "battery is" in str(item.get("last_error", "")).lower():
                    item["last_error"] = ""
        self.save_resume_data(wait=False)
        self._save_state()

    def clear_completed(self):
        self.state["downloads"] = [x for x in self.state["downloads"] if x.get("status") != "completed"]
        self._save_state()

    def export_state(self) -> str:
        raw = json.dumps(self.state, ensure_ascii=False).encode("utf-8")
        return base64.b64encode(raw).decode("ascii")

    def import_state(self, payload: str):
        data = json.loads(base64.b64decode(payload.encode("ascii")).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid import payload.")
        self.state = data
        self.state.setdefault("downloads", [])
        self.state.setdefault("settings", {})
        self.state.setdefault("prepared", {})
        self._migrate_state()


manager = DownloaderManager()




