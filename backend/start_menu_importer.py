"""
Start Menu installed-game discovery for Arcadia My Library.

The scanner is intentionally conservative: it only suggests shortcuts that
resolve to local executables and match games Arcadia already knows from the
library/cache. Nothing is imported until the user confirms the review list.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import winreg
from pathlib import Path
from typing import Any

from backend import cache as app_cache, library_service
from backend.executable_detector import detect_executables


EXCLUDED_NAME_PARTS = {
    "uninstall",
    "unins",
    "setup",
    "install",
    "installer",
    "repair",
    "redist",
    "redistributable",
    "directx",
    "vcredist",
    "manual",
    "readme",
    "support",
    "language",
    "changer",
    "selector",
    "configuration",
    "website",
    "url",
}

KNOWN_LAUNCHERS = {
    "steam",
    "epicgameslauncher",
    "goggalaxy",
    "ubisoftconnect",
    "eadesktop",
    "origin",
    "battle.net",
    "riotclientservices",
    "xbox",
}


def _tokens(value: str) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return {part for part in cleaned.split() if len(part) > 1}


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return cleaned[:90] or "local-game"


def _shortcut_roots() -> list[str]:
    roots = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    return [root for root in roots if root and os.path.isdir(root)]


def _shortcut_paths() -> list[str]:
    paths: list[str] = []
    for root in _shortcut_roots():
        for current_root, _, files in os.walk(root):
            for filename in files:
                if filename.lower().endswith(".lnk"):
                    paths.append(os.path.join(current_root, filename))
    return sorted(set(paths))


def _resolve_shortcuts(paths: list[str]) -> list[dict[str, Any]]:
    if not paths:
        return []
    resolved = _resolve_shortcuts_win32com(paths)
    if resolved:
        return resolved
    return _resolve_shortcuts_powershell(paths)


def _resolve_shortcuts_win32com(paths: list[str]) -> list[dict[str, Any]]:
    try:
        import win32com.client  # type: ignore
    except Exception:
        return []
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        items = []
        for path in paths:
            try:
                shortcut = shell.CreateShortcut(path)
                items.append({
                    "shortcut_path": path,
                    "target_path": shortcut.TargetPath,
                    "arguments": shortcut.Arguments,
                    "working_directory": shortcut.WorkingDirectory,
                    "icon_location": shortcut.IconLocation,
                })
            except Exception:
                continue
        return items
    except Exception:
        return []


def _resolve_shortcuts_powershell(paths: list[str]) -> list[dict[str, Any]]:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$raw = [Console]::In.ReadToEnd()
$paths = $raw | ConvertFrom-Json
$shell = New-Object -ComObject WScript.Shell
$items = foreach ($p in $paths) {
  try {
    $s = $shell.CreateShortcut($p)
    [pscustomobject]@{
      shortcut_path = $p
      target_path = $s.TargetPath
      arguments = $s.Arguments
      working_directory = $s.WorkingDirectory
      icon_location = $s.IconLocation
    }
  } catch {}
}
$items | ConvertTo-Json -Depth 4 -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            input=json.dumps(paths),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _known_games() -> list[dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    for game in library_service.list_games():
        slug = game.get("slug")
        if slug:
            games[slug] = {"slug": slug, "title": game.get("title") or slug}
    for game in app_cache.get_cached_games():
        slug = game.get("slug")
        if slug and slug not in games:
            games[slug] = {"slug": slug, "title": game.get("title") or slug}
    return list(games.values())


def _is_excluded(shortcut: dict[str, Any]) -> tuple[bool, str]:
    shortcut_name = Path(shortcut.get("shortcut_path") or "").stem
    target_path = os.path.abspath(str(shortcut.get("target_path") or ""))
    target_name = Path(target_path).stem
    haystack = _compact(" ".join([shortcut_name, target_name, target_path]))
    if not target_path.lower().endswith(".exe") or not os.path.exists(target_path):
        return True, "Shortcut target is not a local executable."
    if any(part in haystack for part in EXCLUDED_NAME_PARTS):
        return True, "Filtered as installer, support, redist, or utility shortcut."
    if _compact(target_name) in KNOWN_LAUNCHERS:
        return True, "Shortcut points to a game launcher instead of a game executable."
    return False, ""


def _install_path_for(shortcut: dict[str, Any]) -> str:
    target_path = os.path.abspath(str(shortcut.get("target_path") or ""))
    working = os.path.abspath(str(shortcut.get("working_directory") or ""))
    if working and os.path.isdir(working):
        try:
            if os.path.commonpath([working, target_path]) == working:
                return working
        except ValueError:
            pass
    return os.path.dirname(target_path)


def _score_match(shortcut: dict[str, Any], game: dict[str, Any]) -> tuple[int, list[str]]:
    shortcut_name = Path(shortcut.get("shortcut_path") or "").stem
    target_path = str(shortcut.get("target_path") or "")
    target_name = Path(target_path).stem
    parent_name = Path(target_path).parent.name
    source = " ".join([shortcut_name, target_name, parent_name])
    source_tokens = _tokens(source)
    title = game.get("title") or ""
    slug = game.get("slug") or ""
    wanted = _tokens(title) | _tokens(slug)
    reasons: list[str] = []
    score = 0
    compact_source = _compact(source)
    compact_title = _compact(title)
    compact_slug = _compact(slug)
    if compact_title and compact_title in compact_source:
        score += 72
        reasons.append("shortcut matches title")
    if compact_slug and compact_slug in compact_source:
        score += 64
        reasons.append("shortcut matches slug")
    if wanted and source_tokens:
        overlap = len(source_tokens & wanted)
        if overlap:
            score += min(42, overlap * 12)
            reasons.append("shared title words")
    if _compact(target_name) and (_compact(target_name) in compact_title or _compact(target_name) in compact_slug):
        score += 14
        reasons.append("executable name supports match")
    return score, reasons[:3] or ["possible catalog match"]


def _best_game_match(source: str, known_games: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int, list[str]]:
    best_game: dict[str, Any] | None = None
    best_score = 0
    best_reasons: list[str] = []
    fake = {"shortcut_path": source, "target_path": source}
    for game in known_games:
        score, reasons = _score_match(fake, game)
        if score > best_score:
            best_game = game
            best_score = score
            best_reasons = reasons
    return best_game, best_score, best_reasons


def _library_status() -> dict[str, str]:
    return {
        game.get("slug"): (game.get("library") or game.get("offline_user") or {}).get("install_status", "backlog")
        for game in library_service.list_games()
        if game.get("slug")
    }


def _match_from_install(
    install_dir: str,
    display_name: str,
    known_games: list[dict[str, Any]],
    library_status: dict[str, str],
    source: str,
    explicit_target: str = "",
    platform_id: str = "",
    platform_meta: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    quick_exes: list[str] = []
    try:
        for current_root, dirs, files in os.walk(install_dir):
            rel = os.path.relpath(current_root, install_dir)
            depth = 0 if rel == "." else len(Path(rel).parts)
            if depth >= 3:
                dirs[:] = []
            for filename in files:
                if filename.lower().endswith(".exe"):
                    quick_exes.append(os.path.splitext(filename)[0])
            if len(quick_exes) >= 14:
                break
    except OSError:
        pass
    source_text = " ".join([display_name, Path(install_dir).name, Path(install_dir).parent.name, platform_id, *quick_exes[:14]])
    best_game, best_score, best_reasons = _best_game_match(source_text, known_games)
    local_title = display_name or Path(install_dir).name
    is_local_only = not best_game or best_score < 42
    if is_local_only:
        best_game = {"slug": f"local-{_safe_slug(local_title)}", "title": local_title}
        best_score = 40
        best_reasons = ["local installed game"]
    slug = best_game.get("slug") or ""
    try:
        detected = detect_executables(install_dir, best_game.get("title", ""), slug, max_depth=6)
    except Exception:
        return None
    selected = detected.get("selected") or ""
    candidates = detected.get("candidates") or []
    target_path = os.path.abspath(explicit_target) if explicit_target else ""
    if target_path and (not target_path.lower().endswith(".exe") or not os.path.exists(target_path)):
        target_path = ""
    if target_path:
        target_name = Path(target_path).stem
        excluded, _ = _is_excluded({
            "shortcut_path": display_name or install_dir,
            "target_path": target_path,
            "working_directory": install_dir,
        })
        if excluded and _compact(target_name) not in {_compact(Path(install_dir).name), _compact(display_name)}:
            target_path = ""
    if target_path:
        selected = target_path
    if not selected and not candidates:
        return None
    confidence = "high" if (best_score >= 72 or is_local_only) and selected else ("medium" if selected else "low")
    existing_status = library_status.get(slug, "")
    duplicate = existing_status == "installed"
    meta = platform_meta or {}
    return {
        "id": _compact(f"{source}|{install_dir}|{slug}|{platform_id}"),
        "shortcut_name": display_name or Path(install_dir).name,
        "shortcut_path": "",
        "target_path": selected or (candidates[0].get("path") if candidates else ""),
        "working_directory": install_dir,
        "install_path": install_dir,
        "matched_slug": slug,
        "matched_title": best_game.get("title") or slug,
        "confidence": confidence,
        "score": best_score,
        "import_status": "installed" if selected and confidence == "high" else "unlinked",
        "library_source": source,
        "platform_app_id": meta.get("platform_app_id", platform_id if source == "steam" else ""),
        "epic_catalog_item_id": meta.get("epic_catalog_item_id", ""),
        "epic_namespace": meta.get("epic_namespace", ""),
        "epic_app_name": meta.get("epic_app_name", platform_id if source == "epic" else ""),
        "local_only": is_local_only,
        "duplicate": duplicate,
        "checked": bool(not duplicate and (selected or confidence == "high")),
        "warning": (
            "Already linked in My Library."
            if duplicate
            else ("Multiple or uncertain executables; import will mark Needs Link." if not selected or confidence != "high" else "")
        ),
        "reasons": best_reasons,
    }


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _steam_roots() -> list[str]:
    roots: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "SteamPath")
            if value:
                roots.append(str(value).replace("/", "\\"))
    except OSError:
        pass
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Steam"),
        os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Steam"),
    ]
    roots.extend(candidates)
    deduped: dict[str, str] = {}
    for root in roots:
        if root and os.path.isdir(root):
            deduped[os.path.normcase(os.path.abspath(root))] = root
    return list(deduped.values())


def _parse_steam_library_paths(steam_root: str) -> list[str]:
    paths = [steam_root]
    text = _read_text(os.path.join(steam_root, "steamapps", "libraryfolders.vdf"))
    for match in re.finditer(r'"path"\s+"([^"]+)"', text, re.I):
        paths.append(match.group(1).replace("\\\\", "\\"))
    deduped: dict[str, str] = {}
    for path in paths:
        if os.path.isdir(os.path.join(path, "steamapps")):
            deduped[os.path.normcase(os.path.abspath(path))] = path
    return list(deduped.values())


def _parse_acf_value(text: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}"\s+"([^"]*)"', text, re.I)
    return match.group(1) if match else ""


def scan_steam_libraries(known_games: list[dict[str, Any]], library_status: dict[str, str]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    scanned = 0
    filtered = 0
    for steam_root in _steam_roots():
        for library_root in _parse_steam_library_paths(steam_root):
            steamapps = os.path.join(library_root, "steamapps")
            try:
                manifests = [p for p in Path(steamapps).glob("appmanifest_*.acf")]
            except OSError:
                manifests = []
            for manifest in manifests:
                scanned += 1
                text = _read_text(str(manifest))
                appid = _parse_acf_value(text, "appid")
                name = _parse_acf_value(text, "name")
                installdir = _parse_acf_value(text, "installdir")
                install_path = os.path.join(steamapps, "common", installdir)
                if not name or not installdir or not os.path.isdir(install_path):
                    filtered += 1
                    continue
                match = _match_from_install(
                    install_path,
                    name,
                    known_games,
                    library_status,
                    "steam",
                    platform_id=appid,
                    platform_meta={"platform_app_id": appid},
                )
                if match:
                    matches.append(match)
                else:
                    filtered += 1
    return {"scanned": scanned, "filtered": filtered, "matches": matches}


def scan_epic_libraries(known_games: list[dict[str, Any]], library_status: dict[str, str]) -> dict[str, Any]:
    roots = [
        os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Epic", "EpicGamesLauncher", "Data", "Manifests"),
    ]
    matches: list[dict[str, Any]] = []
    scanned = 0
    filtered = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for manifest in Path(root).glob("*.item"):
            scanned += 1
            try:
                data = json.loads(manifest.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                filtered += 1
                continue
            name = data.get("DisplayName") or data.get("AppName") or data.get("CatalogItemId") or manifest.stem
            install_path = data.get("InstallLocation") or ""
            launch_exe = data.get("LaunchExecutable") or ""
            target_path = os.path.join(install_path, launch_exe) if install_path and launch_exe else ""
            if not install_path or not os.path.isdir(install_path):
                filtered += 1
                continue
            match = _match_from_install(
                install_path,
                name,
                known_games,
                library_status,
                "epic",
                target_path,
                data.get("AppName", ""),
                {
                    "epic_catalog_item_id": data.get("CatalogItemId", ""),
                    "epic_namespace": data.get("CatalogNamespace", ""),
                    "epic_app_name": data.get("AppName", ""),
                },
            )
            if match:
                matches.append(match)
            else:
                filtered += 1
    return {"scanned": scanned, "filtered": filtered, "matches": matches}


def _candidate_install_dirs(root: str, limit: int = 160) -> list[str]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError("Selected game folder does not exist.")
    dirs = [str(root_path)]
    try:
        children = [child for child in root_path.iterdir() if child.is_dir()]
    except OSError:
        children = []
    excluded = {"_commonredist", "redist", "redistributable", "directx", "vc", "support", "installer"}
    for child in children:
        if child.name.lower() in excluded:
            continue
        dirs.append(str(child))
        if len(dirs) >= limit:
            break
    return dirs


def scan_install_paths(paths: list[str]) -> dict[str, Any]:
    known_games = _known_games()
    library_status = _library_status()
    matches: list[dict[str, Any]] = []
    scanned = 0
    filtered = 0
    seen_slugs: set[str] = set()
    for raw_path in paths:
        if not raw_path:
            continue
        candidate_dirs = _candidate_install_dirs(raw_path)
        generic_root_names = {"games", "game", "installed games", "library", "common", "steamapps"}
        raw_root = str(Path(raw_path).resolve())
        for install_dir in candidate_dirs:
            if (
                install_dir == raw_root
                and len(candidate_dirs) > 1
                and Path(install_dir).name.lower() in generic_root_names
            ):
                continue
            scanned += 1
            try:
                match = _match_from_install(install_dir, Path(install_dir).name, known_games, library_status, "folder_scan")
                if not match:
                    filtered += 1
                    continue
                slug = match.get("matched_slug") or ""
                if slug in seen_slugs:
                    filtered += 1
                    continue
                seen_slugs.add(slug)
                matches.append(match)
            except Exception:
                filtered += 1
    matches.sort(key=lambda item: (item["duplicate"], -int(item["score"]), item["matched_title"].lower()))
    return {"success": True, "scanned": scanned, "filtered": filtered, "matches": matches[:80]}


def scan_start_menu() -> dict[str, Any]:
    known_games = _known_games()
    library_status = _library_status()
    resolved = _resolve_shortcuts(_shortcut_paths())
    matches: list[dict[str, Any]] = []
    scanned = 0
    filtered = 0
    for shortcut in resolved:
        scanned += 1
        excluded, warning = _is_excluded(shortcut)
        if excluded:
            filtered += 1
            continue
        best_game: dict[str, Any] | None = None
        best_score = 0
        best_reasons: list[str] = []
        for game in known_games:
            score, reasons = _score_match(shortcut, game)
            if score > best_score:
                best_game = game
                best_score = score
                best_reasons = reasons
        if not best_game or best_score < 48:
            filtered += 1
            continue
        confidence = "high" if best_score >= 78 else "medium"
        slug = best_game.get("slug") or ""
        existing_status = library_status.get(slug, "")
        duplicate = existing_status == "installed"
        can_update_existing = bool(existing_status and not duplicate)
        matches.append({
            "id": _compact(f"{shortcut.get('shortcut_path')}|{shortcut.get('target_path')}"),
            "shortcut_name": Path(shortcut.get("shortcut_path") or "").stem,
            "shortcut_path": shortcut.get("shortcut_path") or "",
            "target_path": os.path.abspath(str(shortcut.get("target_path") or "")),
            "working_directory": shortcut.get("working_directory") or "",
            "install_path": _install_path_for(shortcut),
            "matched_slug": slug,
            "matched_title": best_game.get("title") or slug,
            "confidence": confidence,
            "score": best_score,
            "import_status": "installed" if confidence == "high" else "unlinked",
            "library_source": "start_menu",
            "duplicate": duplicate,
            "checked": bool(confidence == "high" and not duplicate),
            "warning": (
                "Already linked in My Library."
                if duplicate
                else ("Saved in My Library; import will update its install link." if can_update_existing else warning)
            ),
            "reasons": best_reasons,
        })
    for platform_result in (scan_steam_libraries(known_games, library_status), scan_epic_libraries(known_games, library_status)):
        scanned += int(platform_result.get("scanned") or 0)
        filtered += int(platform_result.get("filtered") or 0)
        matches.extend(platform_result.get("matches") or [])
    deduped: dict[str, dict[str, Any]] = {}
    source_rank = {"steam": 3, "epic": 3, "folder_scan": 2, "start_menu": 1}
    for item in matches:
        slug = item.get("matched_slug") or item.get("id")
        current = deduped.get(slug)
        if not current:
            deduped[slug] = item
            continue
        old_rank = source_rank.get(current.get("library_source"), 0)
        new_rank = source_rank.get(item.get("library_source"), 0)
        if new_rank > old_rank or int(item.get("score") or 0) > int(current.get("score") or 0):
            deduped[slug] = item
    matches = list(deduped.values())
    matches.sort(key=lambda item: (item["duplicate"], -int(item["score"]), item["matched_title"].lower()))
    return {
        "success": True,
        "scanned": scanned,
        "filtered": filtered,
        "matches": matches[:80],
    }


def import_matches(items: list[dict[str, Any]]) -> dict[str, Any]:
    imported: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in items:
        slug = str(item.get("matched_slug") or "").strip()
        if not slug:
            errors.append({"title": str(item.get("matched_title") or "Unknown"), "error": "Missing matched slug."})
            continue
        try:
            status = str(item.get("import_status") or "unlinked")
            source = str(item.get("library_source") or "start_menu")
            install_path = str(item.get("install_path") or os.path.dirname(str(item.get("target_path") or "")))
            target_path = str(item.get("target_path") or "")
            if str(slug).startswith("local-") and not library_service.get_game(slug):
                library_service.save_game({
                    "slug": slug,
                    "title": item.get("matched_title") or item.get("shortcut_name") or slug,
                    "category": "Local Game",
                    "summary": "Imported from installed games scan.",
                    "url": "",
                    "cover": "",
                    "thumbnail": "",
                    "platform_app_id": item.get("platform_app_id", ""),
                    "epic_catalog_item_id": item.get("epic_catalog_item_id", ""),
                    "epic_namespace": item.get("epic_namespace", ""),
                    "epic_app_name": item.get("epic_app_name", ""),
                }, source=source)
            if status == "installed" and target_path:
                result = library_service.link_game(slug, install_path, executable_path=target_path, source=source)
                library_service.update_user_data(slug, {"library_source": source})
            else:
                result = library_service.link_game(slug, install_path, source=source)
                library_service.update_user_data(slug, {
                    "install_status": "unlinked",
                    "executable_path": "",
                    "library_source": source,
                })
            library_service.update_user_data(slug, {
                "platform_app_id": item.get("platform_app_id", ""),
                "epic_catalog_item_id": item.get("epic_catalog_item_id", ""),
                "epic_namespace": item.get("epic_namespace", ""),
                "epic_app_name": item.get("epic_app_name", ""),
            })
            imported.append({
                "slug": slug,
                "title": item.get("matched_title") or slug,
                "status": status,
                "game": result.get("game"),
            })
        except Exception as exc:
            errors.append({"title": str(item.get("matched_title") or slug), "error": str(exc)})
    return {"success": True, "imported": imported, "errors": errors}
