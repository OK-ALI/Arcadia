"""
cache.py - Simple JSON file cache with TTL.
No databases, just a dict on disk.
"""

import hashlib
import json
import os
import shutil
import threading
import time
from functools import wraps

from backend.config import CACHE_FILE, CACHE_TTL

_CACHE_LOCK = threading.RLock()


def _load_cache() -> dict:
    """Load cache from disk without letting a corrupt cache break the app."""
    with _CACHE_LOCK:
        if not os.path.exists(CACHE_FILE):
            return {}

        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except UnicodeDecodeError:
            try:
                with open(CACHE_FILE, "rb") as f:
                    text = f.read().decode("utf-8", errors="replace")
                data = json.loads(text)
                if isinstance(data, dict):
                    _save_cache(data)
                    return data
            except (json.JSONDecodeError, IOError, OSError):
                pass
        except (json.JSONDecodeError, IOError, OSError):
            pass

        try:
            shutil.copy2(CACHE_FILE, f"{CACHE_FILE}.corrupt")
        except OSError:
            pass
        return {}


def _save_cache(cache: dict):
    """Persist cache to disk atomically."""
    with _CACHE_LOCK:
        try:
            tmp_file = f"{CACHE_FILE}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
            os.replace(tmp_file, CACHE_FILE)
        except (IOError, OSError):
            pass


def _make_key(*args, **kwargs) -> str:
    """Generate a unique cache key from function arguments."""
    raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def get(key: str):
    """Get a value from cache if it exists and hasn't expired."""
    with _CACHE_LOCK:
        cache = _load_cache()
        entry = cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["ts"] > entry.get("ttl", CACHE_TTL):
            del cache[key]
            _save_cache(cache)
            return None
        return entry["data"]


def set(key: str, data, ttl: int = CACHE_TTL):
    """Store a value in cache with a TTL."""
    with _CACHE_LOCK:
        cache = _load_cache()
        cache[key] = {
            "data": data,
            "ts": time.time(),
            "ttl": ttl,
        }
        now = time.time()
        cache = {
            k: v for k, v in cache.items()
            if now - v["ts"] <= v.get("ttl", CACHE_TTL)
        }
        _save_cache(cache)


def cached(ttl: int = CACHE_TTL):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{_make_key(*args, **kwargs)}"
            result = get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            if result is not None:
                set(key, result, ttl)
            return result
        return wrapper
    return decorator


def clear():
    """Clear all cache."""
    with _CACHE_LOCK:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)


def get_cached_games() -> list:
    """Scan the cache for all cached game details pages."""
    with _CACHE_LOCK:
        cache = _load_cache()
        games = []
        for key, entry in cache.items():
            if key.startswith("get_game_details:"):
                data = entry.get("data")
                if data and isinstance(data, dict) and "slug" in data and "title" in data:
                    games.append(data)
        return games
