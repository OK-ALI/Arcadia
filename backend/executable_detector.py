"""
Executable detection helpers for Arcadia's local game library.

The detector only scans inside a user-selected or download-completed install
folder and returns scored candidates. It intentionally avoids installers,
redistributables, crash reporters, uninstallers, and helper tools.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


EXCLUDED_DIR_PARTS = {
    "_commonredist",
    "commonredist",
    "redist",
    "redistributable",
    "directx",
    "dx",
    "vc",
    "vcredist",
    "support",
    "installer",
    "installers",
    "__installer",
    "engine",
    "binaries/thirdparty",
}

EXCLUDED_NAME_PARTS = {
    "unins",
    "uninstall",
    "setup",
    "install",
    "installer",
    "crash",
    "report",
    "reporter",
    "benchmark",
    "config",
    "settings",
    "launcher_helper",
    "helper",
    "server",
    "dedicated",
    "redistributable",
    "vcredist",
    "dxsetup",
}


def _tokens(value: str) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return {part for part in cleaned.split() if len(part) > 1}


def _safe_root(path: str | None) -> str:
    root = os.path.abspath(os.path.expanduser(str(path or "").strip().strip('"')))
    if not root or not os.path.isdir(root):
        raise ValueError("Install folder does not exist.")
    return root


def _is_excluded(path: str, root: str) -> bool:
    rel = os.path.relpath(path, root).replace("\\", "/").lower()
    name = os.path.splitext(os.path.basename(path))[0].lower()
    if any(part in rel for part in EXCLUDED_DIR_PARTS):
        return True
    return any(part in name for part in EXCLUDED_NAME_PARTS)


def _score(path: str, root: str, title: str = "", slug: str = "") -> int:
    rel = os.path.relpath(path, root)
    depth = len(Path(rel).parts)
    name = os.path.splitext(os.path.basename(path))[0]
    name_tokens = _tokens(name)
    wanted = _tokens(title) | _tokens(slug)

    score = 40
    if wanted and name_tokens:
        overlap = len(name_tokens & wanted)
        score += min(35, overlap * 12)
        if name.lower().replace(" ", "-") in str(slug or "").lower():
            score += 12
    score += max(0, 18 - depth * 4)
    try:
        size_mb = os.path.getsize(path) / (1024 * 1024)
    except OSError:
        size_mb = 0
    if size_mb >= 50:
        score += 18
    elif size_mb >= 10:
        score += 10
    elif size_mb < 2:
        score -= 12
    if "win64" in rel.lower() or "x64" in rel.lower():
        score += 4
    return score


def detect_executables(
    install_path: str | None,
    title: str = "",
    slug: str = "",
    max_depth: int = 5,
    max_results: int = 8,
) -> dict[str, Any]:
    root = _safe_root(install_path)
    candidates: list[dict[str, Any]] = []

    for current_root, dirs, files in os.walk(root):
        rel_root = os.path.relpath(current_root, root)
        depth = 0 if rel_root == "." else len(Path(rel_root).parts)
        if depth >= max_depth:
            dirs[:] = []
        dirs[:] = [
            d for d in dirs
            if not any(part in os.path.join(rel_root, d).replace("\\", "/").lower() for part in EXCLUDED_DIR_PARTS)
        ]
        for filename in files:
            if not filename.lower().endswith(".exe"):
                continue
            path = os.path.abspath(os.path.join(current_root, filename))
            if not path.startswith(root) or _is_excluded(path, root):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            candidates.append({
                "path": path,
                "name": filename,
                "relative_path": os.path.relpath(path, root),
                "size": size,
                "score": _score(path, root, title, slug),
            })

    candidates.sort(key=lambda item: (-int(item["score"]), len(item["relative_path"]), item["name"].lower()))
    candidates = candidates[:max_results]
    selected = ""
    confidence = "none"
    if candidates:
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        if int(top["score"]) >= 68 and (not second or int(top["score"]) - int(second["score"]) >= 14):
            selected = str(top["path"])
            confidence = "high"
        elif len(candidates) == 1 and int(top["score"]) >= 54:
            selected = str(top["path"])
            confidence = "medium"
        else:
            confidence = "multiple"

    return {
        "install_path": root,
        "selected": selected,
        "confidence": confidence,
        "candidates": candidates,
    }
