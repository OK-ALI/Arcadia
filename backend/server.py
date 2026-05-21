"""
server.py â€” Flask application with REST API endpoints.
Serves the frontend and provides scraping API.
"""

import webbrowser
from flask import Flask, jsonify, request, send_from_directory, send_file
import os
from typing import Callable

from backend.config import DATA_DIR, FRONTEND_DIR, HOST, PORT
from backend import scraper, cache as app_cache, system, news
from backend.downloader import manager as downloader_manager
from backend.offline_library import library as offline_library

_focus_callback: Callable[[], bool] | None = None


def set_focus_callback(callback: Callable[[], bool] | None):
    global _focus_callback
    _focus_callback = callback

# â”€â”€ Flask App Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = Flask(
    __name__,
    static_folder=os.path.join(FRONTEND_DIR),
    static_url_path=""
)


# â”€â”€ Frontend Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/")
def index():
    """Serve the main SPA page."""
    return send_file(os.path.join(FRONTEND_DIR, "index.html"))


@app.route("/api/app/focus", methods=["POST"])
def api_app_focus():
    """Restore the existing Arcadia window when a second launch occurs."""
    try:
        if _focus_callback:
            return jsonify({"success": bool(_focus_callback())})
        return jsonify({"success": False, "message": "Focus callback not ready"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# â”€â”€ API Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/search")
def api_search():
    """Search games by query string."""
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    try:
        results = scraper.search_games(query, page)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest")
def api_latest():
    """Get latest repacks from the homepage."""
    page = request.args.get("page", 1, type=int)

    try:
        results = scraper.get_latest_repacks(page)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/library")
def api_library():
    """Paged Games Gallery library with A-Z filtering."""
    letter = request.args.get("letter", "all")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 48, type=int)
    try:
        return jsonify(scraper.get_games_library(letter, page, page_size))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/library/index", methods=["GET", "POST"])
def api_library_index():
    """Start or inspect the background A-Z catalog indexer."""
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            force = bool(payload.get("force") or request.args.get("force") == "1")
            max_pages = int(payload.get("max_pages") or request.args.get("max_pages") or 140)
            return jsonify(scraper.start_library_index(force=force, max_pages=max_pages))
        return jsonify(scraper.get_library_index_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/library/artwork", methods=["GET", "POST"])
def api_library_artwork():
    """Start or inspect background artwork loading for Gallery cards."""
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            limit = int(payload.get("limit") or request.args.get("limit") or 36)
            slugs = payload.get("slugs") or []
            if not isinstance(slugs, list):
                slugs = []
            return jsonify(scraper.start_cover_hydration(limit=limit, slugs=slugs))
        return jsonify(scraper.get_cover_hydration_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/library/artwork/visible", methods=["POST"])
def api_library_visible_artwork():
    """Fetch artwork for the current visible Gallery page."""
    try:
        payload = request.get_json(silent=True) or {}
        slugs = payload.get("slugs") or []
        if not isinstance(slugs, list):
            slugs = []
        limit = int(payload.get("limit") or 24)
        return jsonify(scraper.hydrate_visible_artwork(slugs, limit=limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/library/requirements", methods=["POST"])
def api_library_requirements():
    """Fetch accurate requirements for visible gallery games."""
    try:
        payload = request.get_json(silent=True) or {}
        slugs = payload.get("slugs") or []
        if not isinstance(slugs, list):
            slugs = []
        limit = int(payload.get("limit") or 24)
        return jsonify(scraper.hydrate_requirements(slugs, limit=limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/game/<slug>")
def api_game(slug):
    """Get full details for a specific game."""
    try:
        details = scraper.get_game_details(slug)
        if details is None:
            return jsonify({"error": "Game not found"}), 404
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


import subprocess
import winreg
import re

def find_fdm_path():
    """Try to find the path to fdm.exe on the system."""
    # 1. Check registry magnet handler
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"magnet\shell\open\command") as key:
            cmd, _ = winreg.QueryValueEx(key, "")
            match = re.search(r'"([^"]+)"', cmd)
            if match:
                path = match.group(1)
                if os.path.exists(path):
                    return path
            path = cmd.split()[0].replace('"', '')
            if os.path.exists(path):
                return path
    except Exception:
        pass

    # 2. Check registry App Paths
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\fdm.exe") as key:
            path, _ = winreg.QueryValueEx(key, "")
            if os.path.exists(path):
                return path
    except Exception:
        pass

    # 3. Check common installation directories
    common_paths = [
        r"C:\Program Files\Softdeluxe\Free Download Manager\fdm.exe",
        r"C:\Program Files (x86)\Softdeluxe\Free Download Manager\fdm.exe",
        r"C:\Program Files\Free Download Manager\fdm.exe",
        r"C:\Program Files (x86)\Free Download Manager\fdm.exe",
    ]
    
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        common_paths.append(os.path.join(local_app_data, "Softdeluxe", "Free Download Manager", "fdm.exe"))
        common_paths.append(os.path.join(local_app_data, "Free Download Manager", "fdm.exe"))
        
    app_data = os.environ.get("APPDATA")
    if app_data:
        common_paths.append(os.path.join(app_data, "Softdeluxe", "Free Download Manager", "fdm.exe"))
        common_paths.append(os.path.join(app_data, "Free Download Manager", "fdm.exe"))

    for path in common_paths:
        if os.path.exists(path):
            return path
            
    return None


@app.route("/api/download/<slug>", methods=["POST"])
def api_download(slug):
    """Extract magnet link and open it directly in Free Download Manager (FDM)."""
    try:
        magnet = scraper.extract_magnet_link(slug)
        if not magnet:
            return jsonify({"error": "No magnet link found for this game"}), 404

        # Try to find and run FDM directly
        fdm_path = find_fdm_path()
        if fdm_path:
            # Run FDM with the magnet link as an argument
            subprocess.Popen([fdm_path, magnet])
            return jsonify({
                "success": True, 
                "message": "Magnet link sent directly to Free Download Manager!"
            })
        else:
            # Fall back to default OS protocol handler
            webbrowser.open(magnet)
            return jsonify({
                "success": True, 
                "message": "FDM not located. Magnet link opened via OS default handler."
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/prepare/<slug>", methods=["POST"])
def api_download_prepare(slug):
    """Extract magnet metadata and prepare an internal selectable download."""
    try:
        payload = request.get_json(silent=True) or {}
        game = scraper.get_game_details(slug)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        magnet = game.get("magnet_link") or scraper.extract_magnet_link(slug)
        if not magnet:
            return jsonify({"error": "No magnet link found for this game"}), 404
        offline_library.save_game(game)
        prepared = downloader_manager.prepare_download(
            slug=slug,
            title=game.get("title", slug),
            magnet=magnet,
            save_path=payload.get("save_path"),
        )
        prepared["game"] = {
            "title": game.get("title", slug),
            "slug": slug,
            "cover": game.get("cover", ""),
            "repack_size": game.get("repack_size", ""),
            "original_size": game.get("original_size", ""),
            "requirements": game.get("requirements", {}),
            "magnet_link": magnet,
        }
        return jsonify(prepared)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/download/prepare-status/<prepared_id>")
def api_download_prepare_status(prepared_id):
    """Poll libtorrent metadata for an existing prepared download."""
    try:
        return jsonify(downloader_manager.prepare_status(prepared_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/torrent/confirm", methods=["POST"])
def api_torrent_confirm():
    """Confirm a prepared download with selected files and queue settings."""
    try:
        payload = request.get_json(force=True)
        item = downloader_manager.confirm_download(
            prepared_id=payload.get("prepared_id"),
            info_hash=payload.get("info_hash", ""),
            selected_indexes=payload.get("selected_indexes", []),
            save_path=payload.get("save_path") or downloader_manager.state["settings"].get("default_save_path"),
            priority=payload.get("priority", "Normal"),
            queue_position=payload.get("queue_position", "normal"),
        )
        return jsonify({"success": True, "download": item})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/torrent/status")
def api_torrent_status():
    try:
        return jsonify(downloader_manager.list_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/torrent/control", methods=["POST"])
def api_torrent_control():
    try:
        payload = request.get_json(force=True)
        action = payload.get("action")
        if action == "pause-all":
            downloader_manager.pause_all()
            return jsonify({"success": True})
        if action == "resume-all":
            downloader_manager.resume_all()
            return jsonify({"success": True})
        if action == "clear-completed":
            downloader_manager.clear_completed()
            return jsonify({"success": True})
        item = downloader_manager.control(payload.get("info_hash", ""), action)
        return jsonify({"success": True, "download": item})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/torrent/priority", methods=["POST"])
def api_torrent_priority():
    try:
        payload = request.get_json(force=True)
        item = downloader_manager.set_priority(payload.get("info_hash", ""), payload.get("priority", "Normal"))
        return jsonify({"success": True, "download": item})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/torrent/reorder", methods=["POST"])
def api_torrent_reorder():
    try:
        payload = request.get_json(force=True)
        downloads = downloader_manager.reorder(payload.get("info_hash", ""), payload.get("direction", "down"))
        return jsonify({"success": True, "downloads": downloads})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/torrent/settings", methods=["GET", "POST"])
def api_torrent_settings():
    try:
        if request.method == "POST":
            settings = downloader_manager.update_settings(request.get_json(force=True))
        else:
            settings = downloader_manager.state["settings"]
        return jsonify({"settings": settings, "engine": downloader_manager.engine_info()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/popular")
def api_popular():
    """Get popular repacks of the week."""
    try:
        results = scraper.get_popular_repacks()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upcoming")
def api_upcoming():
    """Get upcoming repacks list."""
    try:
        results = scraper.get_upcoming_repacks()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/news")
def api_news():
    """Return cached live gaming news and event links."""
    try:
        force = request.args.get("refresh") in {"1", "true", "yes"}
        return jsonify(news.get_news(force_refresh=force))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    """Clear the JSON cache."""
    try:
        app_cache.clear()
        return jsonify({"success": True, "message": "Cache cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/specs")
def api_system_specs():
    """Get local system hardware specifications."""
    try:
        specs = system.get_pc_specs()
        return jsonify(specs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/drives")
def api_system_drives():
    """Get disk drive space info."""
    try:
        drives = system.get_drive_space()
        return jsonify(drives)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/ping")
def api_system_ping():
    """Ping the official domain to measure latency and verify connectivity."""
    import time
    import requests
    from backend.config import BASE_URL
    start = time.time()
    try:
        # Fast HEAD request with 2.5s timeout
        requests.head(BASE_URL, timeout=2.5)
        latency = int((time.time() - start) * 1000)
        return jsonify({"online": True, "latency": latency})
    except Exception:
        return jsonify({"online": False, "latency": 0})


@app.route("/api/offline/library")
def api_offline_library():
    """Fetch all games available in the offline catalog cache."""
    try:
        saved_games = offline_library.list_games()
        cached_games = app_cache.get_cached_games()
        seen = set()
        games = []
        for game in saved_games + cached_games:
            slug = game.get("slug")
            if slug and slug not in seen:
                seen.add(slug)
                games.append(game)
        cards = []
        for g in games:
            # Categories
            cats = g.get("categories", [])
            category = cats[0] if cats else "Lossless Repack"
            screenshots = g.get("screenshots") or []
            first_shot = ""
            if screenshots:
                first = screenshots[0] or {}
                first_shot = first.get("thumb_cached") or first.get("thumb") or first.get("full", "")

            card = dict(g)
            card.update({
                "title": g.get("title", ""),
                "slug": g.get("slug", ""),
                "thumbnail": g.get("thumbnail_cached") or g.get("thumbnail") or g.get("cover_cached") or g.get("cover") or first_shot,
                "cover": g.get("cover_cached") or g.get("cover") or g.get("thumbnail_cached") or g.get("thumbnail") or first_shot,
                "date": g.get("date", ""),
                "repack_size": g.get("repack_size", ""),
                "original_size": g.get("original_size", ""),
                "category": category,
                "requirements": g.get("requirements", {
                    "ram_min": 8,
                    "ram_rec": 16,
                    "space": 0,
                    "cpu": "Intel Core i5 / AMD Ryzen",
                    "gpu": "NVIDIA GTX 1060 / AMD RX 580"
                })
            })
            cards.append(card)
        return jsonify({"games": cards})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/save/<slug>", methods=["POST"])
def api_offline_save(slug):
    try:
        game = scraper.get_game_details(slug)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        saved = offline_library.save_game(game)
        return jsonify({"success": True, "entry": saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/game/<slug>")
def api_offline_game(slug):
    try:
        game = offline_library.get_game(slug)
        if not game:
            return jsonify({"error": "Offline game not found"}), 404
        return jsonify(game)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/user/<slug>", methods=["POST"])
def api_offline_user(slug):
    try:
        entry = offline_library.update_user_data(slug, request.get_json(force=True))
        return jsonify({"success": True, "entry": entry})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/stats")
def api_offline_stats():
    try:
        downloads = downloader_manager.state.get("downloads", [])
        return jsonify(offline_library.stats(downloads))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/export")
def api_offline_export():
    try:
        return jsonify({
            "library": offline_library.export_library(),
            "downloads": downloader_manager.export_state(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/import", methods=["POST"])
def api_offline_import():
    try:
        payload = request.get_json(force=True)
        if payload.get("library"):
            offline_library.import_library(payload["library"])
        if payload.get("downloads"):
            downloader_manager.import_state(payload["downloads"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/prune-media", methods=["POST"])
def api_offline_prune_media():
    try:
        return jsonify(offline_library.prune_media())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/offline/media/<path:rel_path>")
def api_offline_media(rel_path):
    """Serve locally cached offline media."""
    try:
        safe_root = os.path.abspath(DATA_DIR)
        target = os.path.abspath(os.path.join(DATA_DIR, rel_path))
        if not target.startswith(safe_root) or not os.path.exists(target):
            return jsonify({"error": "Media not found"}), 404
        return send_from_directory(os.path.dirname(target), os.path.basename(target))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_server():
    """Start the Flask server (called from app.py in a background thread)."""
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)




