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
import re
import json

import requests
import webview
from PIL import Image, ImageDraw
import pystray

from backend.config import ASSETS_DIR, DATA_DIR, HOST, PORT, WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from backend.server import run_server, set_focus_callback
from backend.downloader import manager as downloader_manager
from backend.download_capture import validate_capture_url

ERROR_ALREADY_EXISTS = 183
APP_USER_MODEL_ID = "OKALI.ArcadiaCore"
_instance_mutex = None


def set_windows_app_user_model_id():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


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
                return Image.open(path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
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

    def choose_executable(self, initial_dir: str = ""):
        """Open a native file picker restricted to Windows executables."""
        try:
            directory = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
            result = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG,
                directory=directory,
                allow_multiple=False,
                file_types=("Executable (*.exe)", "All files (*.*)"),
            )
            if isinstance(result, (list, tuple)) and result:
                return result[0]
            return result or ""
        except Exception:
            return ""

    def choose_artwork(self, initial_dir: str = ""):
        """Open a native file picker for game artwork images."""
        try:
            directory = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
            result = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG,
                directory=directory,
                allow_multiple=False,
                file_types=("Images (*.jpg;*.jpeg;*.png;*.webp)", "All files (*.*)"),
            )
            if isinstance(result, (list, tuple)) and result:
                return result[0]
            return result or ""
        except Exception:
            return ""


def focus_existing_instance(url: str = None, timeout: float = 1.5) -> bool:
    try:
        payload = {"url": url}
        response = requests.post(f"http://{HOST}:{PORT}/api/app/focus", json=payload, timeout=timeout)
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


from ctypes.wintypes import HANDLE, LPVOID

# Define types for 64-bit Windows ctypes safety to prevent pointer truncation crashes
_OpenClipboard = ctypes.windll.user32.OpenClipboard
_OpenClipboard.argtypes = [HANDLE]
_OpenClipboard.restype = ctypes.c_bool

_CloseClipboard = ctypes.windll.user32.CloseClipboard
_CloseClipboard.argtypes = []
_CloseClipboard.restype = ctypes.c_bool

_GetClipboardData = ctypes.windll.user32.GetClipboardData
_GetClipboardData.argtypes = [ctypes.c_uint]
_GetClipboardData.restype = HANDLE

_GlobalLock = ctypes.windll.kernel32.GlobalLock
_GlobalLock.argtypes = [HANDLE]
_GlobalLock.restype = LPVOID

_GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
_GlobalUnlock.argtypes = [HANDLE]
_GlobalUnlock.restype = ctypes.c_bool

def get_clipboard_text() -> str | None:
    try:
        if not _OpenClipboard(None):
            return None
        try:
            h_data = _GetClipboardData(13) # CF_UNICODETEXT
            if not h_data:
                return None
            p_data = _GlobalLock(h_data)
            if not p_data:
                return None
            try:
                text = ctypes.c_wchar_p(p_data).value
                return text
            finally:
                _GlobalUnlock(h_data)
        finally:
            _CloseClipboard()
    except Exception:
        return None

def clipboard_monitor_loop(window):
    last_text = ""
    # Matches common archive formats, installers, magnets, or direct hosting providers
    direct_match = re.compile(
        r'(\.(zip|rar|7z|tar|gz|exe|msi|iso|dmg|pkg|torrent)(\?.*)?$)|'
        r'(^magnet:\?)|'
        r'(https?://(datanodes\.to|gofile\.io|buzzheavier\.com|pixeldrain\.com|krakenfiles\.com|doodrive\.com)/[a-zA-Z0-9_\-/]+)',
        re.IGNORECASE
    )
    while True:
        try:
            if not window:
                break
            text = get_clipboard_text()
            if text:
                text = text.strip()
                if text != last_text:
                    last_text = text
                    if text.startswith("http://") or text.startswith("https://") or text.startswith("magnet:"):
                        if direct_match.search(text):
                            try:
                                validate_capture_url(text)
                                window.evaluate_js(f"if (window.onClipboardLinkDetected) window.onClipboardLinkDetected({json.dumps(text)});")
                            except Exception:
                                pass
        except Exception:
            pass
        time.sleep(1.5)


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
import urllib.parse

def register_custom_protocol():
    if sys.platform != "win32":
        return
    import winreg
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            cmd = f'"{exe_path}" "%1"'
        else:
            python_exe = sys.executable
            script_path = os.path.abspath(__file__)
            cmd = f'"{python_exe}" "{script_path}" "%1"'
            
        key_path = r"Software\Classes\arcadia"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Arcadia Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
        command_key_path = r"Software\Classes\arcadia\shell\open\command"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path) as cmd_key:
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)
            
        print("Successfully registered arcadia:// custom protocol.")
    except Exception as e:
        print(f"Failed to register custom protocol: {e}")


def parse_protocol_url(args: list[str]) -> str | None:
    for arg in args:
        if arg.startswith("arcadia://"):
            match = re.search(r"[?&]url=([^&]+)", arg)
            if match:
                url = urllib.parse.unquote(match.group(1))
                validate_capture_url(url)
                return url
            url = arg[len("arcadia://"):]
            if url.startswith("add-url?url="):
                url = url[len("add-url?url="):]
                url = urllib.parse.unquote(url)
                validate_capture_url(url)
                return url
            return None
    return None


def write_crash_log():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "crash.log"), "w", encoding="utf-8") as f:
            import traceback
            traceback.print_exc(file=f)
    except Exception:
        pass
    return None


def handle_focus(url: str = None) -> bool:
    res = tray.show_window()
    if url and tray.window:
        try:
            validate_capture_url(url)
            tray.window.evaluate_js(f"if (window.onCapturedLinkDetected) window.onCapturedLinkDetected({json.dumps(url)});")
        except Exception as e:
            print(f"Error evaluating JS on focus: {e}")
    return res


def main():
    set_windows_app_user_model_id()
    signal.signal(signal.SIGINT, request_safe_exit)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_safe_exit)

    try:
        protocol_url = parse_protocol_url(sys.argv)
    except ValueError:
        protocol_url = None

    if focus_existing_instance(protocol_url):
        return
    if not acquire_single_instance():
        for _ in range(10):
            if focus_existing_instance(protocol_url, timeout=0.5):
                return
            time.sleep(0.25)
        return

    register_custom_protocol()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    if not wait_for_server(HOST, PORT):
        print("ERROR: Flask server failed to start.")
        return

    print(f"Server running at http://{HOST}:{PORT}")
    set_focus_callback(handle_focus)

    try:
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

        clipboard_thread = threading.Thread(target=clipboard_monitor_loop, args=(window,), daemon=True)
        clipboard_thread.start()

        if protocol_url:
            def trigger_cold_boot():
                time.sleep(2.5)
                handle_focus(protocol_url)
            threading.Thread(target=trigger_cold_boot, daemon=True).start()

        webview.start()
    except KeyboardInterrupt:
        request_safe_exit()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        write_crash_log()
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



