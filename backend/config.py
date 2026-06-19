"""
Central configuration for Arcadia Core.
"""

import os
import sys


if getattr(sys, "frozen", False):
    PROJECT_ROOT = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", EXE_DIR), "Arcadia Core")
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

os.makedirs(DATA_DIR, exist_ok=True)

# Source site used for game catalog data. This is source attribution, not branding.
BASE_URL = "https://fitgirl-repacks.site/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 15

CACHE_FILE = os.path.join(DATA_DIR, "cache.json")
CACHE_TTL = 1800
CACHE_TTL_LONG = 3600

HOST = "127.0.0.1"
PORT = 5000

WINDOW_TITLE = "Arcadia Core"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

APP_VERSION = "0.3.3"
GITHUB_REPO = "OK-ALI/Arcadia"

