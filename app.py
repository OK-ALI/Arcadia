"""
Arcadia Core desktop application entry point.

Launches a Flask server in a background thread and opens a native desktop
window with pywebview. Closing the window hides Arcadia to the system tray so
active downloads can continue until the user explicitly quits.
"""

import os
import signal
import sys
import threading
import time
import ctypes

import requests
import webview
from PIL import Image, ImageDraw
import pystray

from backend.config import ASSETS_DIR, HOST, PORT, WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from backend.server import run_server, set_focus_callback
from backend.downloader import manager as downloader_manager

ERROR_ALREADY_EXISTS = 183
_instance_mutex = None


class TrayController:
    def __init__(self):
        self.icon = None
        self.window = None
        self.quit_requested = False
        self.ready = False
        self.status_text = "Downloads: idle"
        self.completed_seen: set[str] = set()
        self.status_thread = None

    def safe_shutdown(self, destroy_window: bool = True):
        self.quit_requested = True
        try:
            downloader_manager.shutdown()
        except Exception:
            pass
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass
        if destroy_window and self.window:
            try:
                self.window.destroy()
            except Exception:
                pass

    def build_image(self):
        candidates = [
            os.path.join(ASSETS_DIR, "icons", "icon.png"),
            os.path.join(ASSETS_DIR, "icon.png"),
            os.path.join(os.path.dirname(__file__), "frontend", "assets", "arcadia-icon.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return Image.open(path).convert("RGBA").resize((64, 64))
        image = Image.new("RGBA", (64, 64), (10, 10, 12, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(255, 50, 31, 255))
        draw.text((24, 19), "A", fill=(255, 255, 255, 255))
        return image

    def format_bytes(self, value: int | float) -> str:
        value = float(value or 0)
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        return f"{value:.1f} {units[idx]}" if idx else f"{int(value)} {units[idx]}"

    def status_menu_text(self, item=None):
        return self.status_text

    def summarize_downloads(self, downloads: list[dict]) -> tuple[str, list[dict]]:
        active_states = {"downloading", "queued", "metadata", "checking", "paused"}
        active = [d for d in downloads if d.get("status") in active_states]
        if not active:
            return "Downloads: idle", []
        total = sum(int(d.get("total_length") or 0) for d in active)
        done = sum(int(d.get("completed_length") or 0) for d in active)
        speed = sum(int(d.get("download_speed") or 0) for d in active)
        if total > 0:
            pct = min(100, round((done / total) * 100))
            status = f"Downloads: {pct}% · {self.format_bytes(speed)}/s"
        else:
            status = f"Downloads: {len(active)} active · metadata"
        return status, active

    def update_status_loop(self):
        while not self.quit_requested:
            try:
                data = downloader_manager.list_status()
                downloads = data.get("downloads", [])
                self.status_text, _ = self.summarize_downloads(downloads)
                if self.icon:
                    self.icon.title = f"Arcadia Core - {self.status_text}"
                    self.icon.update_menu()
                for item in downloads:
                    info_hash = item.get("info_hash") or item.get("id") or item.get("title", "")
                    if item.get("status") == "completed" and info_hash not in self.completed_seen:
                        self.completed_seen.add(info_hash)
                        if self.icon:
                            self.icon.notify(f"{item.get('title', 'Download')} is ready.", "Download complete")
            except Exception:
                self.status_text = "Downloads: unavailable"
            time.sleep(3)

    def show_window(self, icon=None, item=None):
        if self.window:
            self.window.show()
            try:
                self.window.restore()
            except Exception:
                pass
            return True
        return False

    def quit_app(self, icon=None, item=None):
        self.safe_shutdown()

    def start(self, window):
        self.window = window
        menu = pystray.Menu(
            pystray.MenuItem(self.status_menu_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show Arcadia", self.show_window, default=True),
            pystray.MenuItem("Quit Arcadia", self.quit_app),
        )
        self.icon = pystray.Icon("Arcadia Core", self.build_image(), "Arcadia Core", menu)
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()
        self.status_thread = threading.Thread(target=self.update_status_loop, daemon=True)
        self.status_thread.start()
        self.ready = True

    def close_to_tray(self):
        if self.quit_requested:
            return True
        if self.window:
            self.window.hide()
        return False


tray = TrayController()


class NativeBridge:
    def choose_folder(self, initial_dir: str = ""):
        """Open the native Windows folder picker for frontend path fields."""
        try:
            directory = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=directory,
                allow_multiple=False,
            )
            if isinstance(result, (list, tuple)) and result:
                return result[0]
            return result or ""
        except Exception:
            return ""


def focus_existing_instance(timeout: float = 1.5) -> bool:
    try:
        response = requests.post(f"http://{HOST}:{PORT}/api/app/focus", timeout=timeout)
        return response.ok and bool((response.json() or {}).get("success"))
    except Exception:
        return False


def acquire_single_instance() -> bool:
    """Return False when another Arcadia instance is already alive."""
    global _instance_mutex
    if sys.platform != "win32":
        return True
    mutex_name = "Global\\ArcadiaCoreSingleInstance"
    _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if not _instance_mutex:
        return True
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def request_safe_exit(signum=None, frame=None):
    """Exit from console interrupts without dumping a pywebview traceback."""
    print("\nArcadia Core is shutting down safely...")
    tray.safe_shutdown()
    raise SystemExit(0)


def wait_for_server(host: str, port: int, timeout: int = 10):
    """Wait until the Flask server is ready to accept connections."""
    url = f"http://{host}:{port}/"
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=1)
            return True
        except requests.ConnectionError:
            time.sleep(0.1)
    return False


def main():
    signal.signal(signal.SIGINT, request_safe_exit)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_safe_exit)

    if focus_existing_instance():
        return
    if not acquire_single_instance():
        for _ in range(10):
            if focus_existing_instance(timeout=0.5):
                return
            time.sleep(0.25)
        return

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    if not wait_for_server(HOST, PORT):
        print("ERROR: Flask server failed to start.")
        return

    print(f"Server running at http://{HOST}:{PORT}")
    set_focus_callback(lambda: tray.show_window())

    window = webview.create_window(
        title=WINDOW_TITLE,
        url=f"http://{HOST}:{PORT}",
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(900, 600),
        text_select=True,
        js_api=NativeBridge(),
    )
    window.events.closing += tray.close_to_tray
    tray.start(window)
    try:
        webview.start()
    except KeyboardInterrupt:
        request_safe_exit()
    except SystemExit:
        raise
    except Exception:
        tray.safe_shutdown()
        raise
    finally:
        if tray.quit_requested:
            tray.safe_shutdown(destroy_window=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        request_safe_exit()
    except SystemExit as exc:
        sys.exit(exc.code)



