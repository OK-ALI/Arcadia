"""
Download capture helpers for Arcadia Core.

This module owns URL validation, filename safety, and metadata probing so the
downloader can focus on executing confirmed tasks.
"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

import requests

MAX_CAPTURE_URL_LENGTH = 4096
MAX_FILENAME_LENGTH = 180
PROBE_TIMEOUT = 12


def safe_filename(value: str | None, fallback: str = "download") -> str:
    name = unquote(str(value or "").strip()).replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f]+", "", name)
    name = re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .")
    if not name:
        name = fallback
    if len(name) > MAX_FILENAME_LENGTH:
        root, ext = os.path.splitext(name)
        name = f"{root[:MAX_FILENAME_LENGTH - len(ext)]}{ext}" if ext else root[:MAX_FILENAME_LENGTH]
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    if name.split(".", 1)[0].lower() in reserved:
        name = f"_{name}"
    return name or fallback


def filename_from_content_disposition(value: str | None) -> str:
    raw = str(value or "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", raw, re.IGNORECASE)
    if match:
        return safe_filename(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', raw, re.IGNORECASE)
    return safe_filename(match.group(1)) if match else ""


def file_url_name(url: str, fallback: str = "download") -> str:
    parsed = urlparse(url)
    return safe_filename(os.path.basename(parsed.path), fallback=fallback)


def safe_join_file(root: str, filename: str) -> str:
    safe_root = os.path.abspath(root)
    target = os.path.abspath(os.path.join(safe_root, safe_filename(filename)))
    if os.path.commonpath([safe_root, target]) != safe_root:
        raise ValueError("Unsafe download filename.")
    return target


def validate_capture_url(url: str) -> dict[str, Any]:
    value = str(url or "").strip()
    if not value:
        raise ValueError("URL parameter is required.")
    if len(value) > MAX_CAPTURE_URL_LENGTH:
        raise ValueError("URL is too long.")
    if value.startswith("magnet:"):
        if not value.lower().startswith("magnet:?"):
            raise ValueError("Invalid magnet link.")
        return {"url": value, "scheme": "magnet", "type": "magnet", "host": ""}
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only http, https, and magnet links are supported.")
    lower_path = parsed.path.lower()
    return {
        "url": value,
        "scheme": parsed.scheme,
        "type": "torrent_file" if lower_path.endswith(".torrent") else "http_file",
        "host": parsed.netloc.lower(),
    }


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def probe_url(url: str) -> dict[str, Any]:
    meta = validate_capture_url(url)
    if meta["type"] == "magnet":
        return {
            **meta,
            "filename": "Torrent Download",
            "size": 0,
            "content_type": "application/x-bittorrent",
            "resumable": False,
            "warnings": ["Torrent metadata will load after confirmation."],
        }

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
    warnings: list[str] = []
    response = None
    try:
        response = requests.head(meta["url"], headers=headers, timeout=PROBE_TIMEOUT, allow_redirects=True)
        if response.status_code >= 400 or not response.headers:
            response = requests.get(meta["url"], headers={**headers, "Range": "bytes=0-0"}, timeout=PROBE_TIMEOUT, stream=True, allow_redirects=True)
    except requests.RequestException as exc:
        raise ValueError(f"Could not inspect URL: {exc}") from exc

    try:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ValueError(f"Could not inspect URL: {exc}") from exc
        final_url = response.url or meta["url"]
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
        disposition = response.headers.get("Content-Disposition", "")
        filename = filename_from_content_disposition(disposition) or file_url_name(final_url)
        size = int(response.headers.get("Content-Length") or 0)
        accept_ranges = response.headers.get("Accept-Ranges", "").lower()
        resumable = accept_ranges == "bytes" or response.status_code == 206
        if content_type.startswith("text/html") and not final_url.lower().endswith(".torrent"):
            warnings.append("This looks like a webpage, not a direct downloadable file.")
        return {
            **validate_capture_url(final_url),
            "original_url": meta["url"],
            "filename": filename,
            "size": size,
            "content_type": content_type or "unknown",
            "resumable": resumable,
            "warnings": warnings,
        }
    finally:
        response.close()
