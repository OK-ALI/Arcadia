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

PREFERRED_DIR_PARTS = {
    "bin",
    "binaries",
    "win64",
    "win32",
    "x64",
    "shipping",
    "game",
}

HELPER_NAME_PARTS = {
    "launcher",
    "helper",
    "config",
    "settings",
    "tool",
    "editor",
    "server",
    "dedicated",
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


def _score_details(path: str, root: str, title: str = "", slug: str = "") -> dict[str, Any]:
    rel = os.path.relpath(path, root)
    depth = len(Path(rel).parts)
    name = os.path.splitext(os.path.basename(path))[0]
    name_l = name.lower()
    rel_l = rel.replace("\\", "/").lower()
    name_tokens = _tokens(name)
    wanted = _tokens(title) | _tokens(slug)

    score = 40
    reasons: list[str] = []
    if wanted and name_tokens:
        overlap = len(name_tokens & wanted)
        if overlap:
            score += min(38, overlap * 13)
            reasons.append("matches game title")
        compact_name = re.sub(r"[^a-z0-9]+", "", name_l)
        compact_slug = re.sub(r"[^a-z0-9]+", "", str(slug or "").lower())
        if compact_name and compact_slug and (compact_name in compact_slug or compact_slug in compact_name):
            score += 12
            reasons.append("matches catalog slug")
    root_bonus = max(0, 18 - depth * 4)
    score += root_bonus
    if depth <= 2:
        reasons.append("near install root")
    if any(part in rel_l for part in PREFERRED_DIR_PARTS):
        score += 8
        reasons.append("inside game binary folder")
    try:
        size_mb = os.path.getsize(path) / (1024 * 1024)
    except OSError:
        size_mb = 0
    if size_mb >= 50:
        score += 18
        reasons.append("large game executable")
    elif size_mb >= 10:
        score += 10
        reasons.append("normal executable size")
    elif size_mb < 2:
        score -= 12
        reasons.append("very small helper-sized file")
    if "win64" in rel_l or "x64" in rel_l:
        score += 4
        reasons.append("64-bit build")
    if any(part in name_l for part in HELPER_NAME_PARTS):
        score -= 18
        reasons.append("launcher/helper naming")
    confidence = "low"
    if score >= 78:
        confidence = "high"
    elif score >= 62:
        confidence = "medium"
    return {
        "score": score,
        "confidence": confidence,
        "reasons": reasons[:4] or ["safe executable candidate"],
    }


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
            score_details = _score_details(path, root, title, slug)
            candidates.append({
                "path": path,
                "name": filename,
                "relative_path": os.path.relpath(path, root),
                "size": size,
                "score": score_details["score"],
                "confidence": score_details["confidence"],
                "reasons": score_details["reasons"],
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
        if candidates:
            candidates[0]["recommended"] = True

    return {
        "install_path": root,
        "selected": selected,
        "confidence": confidence,
        "candidates": candidates,
    }
