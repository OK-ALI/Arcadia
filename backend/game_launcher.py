"""
Windows game launching and lightweight play-session tracking.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Callable


_ACTIVE_SESSIONS: dict[str, dict] = {}
_LOCK = threading.Lock()


def get_launch_session(session_key: str) -> dict | None:
    with _LOCK:
        session = _ACTIVE_SESSIONS.get(session_key)
        return dict(session) if session else None


def launch_executable(
    executable_path: str,
    session_key: str | None = None,
    on_finished: Callable[[float], None] | None = None,
) -> dict:
    path = os.path.abspath(os.path.expanduser(str(executable_path or "").strip().strip('"')))
    if not path.lower().endswith(".exe") or not os.path.exists(path):
        raise ValueError("Linked executable is missing.")

    cwd = os.path.dirname(path)
    started_at = time.time()
    proc = subprocess.Popen([path], cwd=cwd, shell=False)
    if session_key:
        with _LOCK:
            _ACTIVE_SESSIONS[session_key] = {
                "pid": proc.pid,
                "started_at": started_at,
                "executable_path": path,
                "running": True,
            }

    if on_finished or session_key:
        def _watch():
            try:
                proc.wait()
                elapsed = max(0.0, time.time() - started_at)
                if on_finished:
                    on_finished(elapsed)
            except Exception:
                pass
            finally:
                if session_key:
                    with _LOCK:
                        _ACTIVE_SESSIONS.pop(session_key, None)

        threading.Thread(target=_watch, daemon=True).start()

    return {
        "pid": proc.pid,
        "started_at": started_at,
        "executable_path": path,
    }
