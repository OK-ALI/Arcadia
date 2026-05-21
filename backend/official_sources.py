"""
Official source discovery for Arcadia Core.

The resolver intentionally prefers known publisher domains and curated mappings
over broad guesses. It is better to show no official link than a bad one.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any


KNOWN_OFFICIAL_SITES = {
    "tekken 8": {
        "official_site": "https://www.bandainamcoent.com/games/tekken-8",
        "publisher_site": "https://www.bandainamcoent.com/",
        "source_confidence": "verified",
    },
    "dragon ball sparking zero": {
        "official_site": "https://www.bandainamcoent.com/games/dragon-ball-sparking-zero",
        "publisher_site": "https://www.bandainamcoent.com/",
        "source_confidence": "verified",
    },
}

PUBLISHER_DOMAINS = {
    "bandai namco": "https://www.bandainamcoent.com/",
    "capcom": "https://www.capcom-games.com/",
    "ubisoft": "https://www.ubisoft.com/",
    "electronic arts": "https://www.ea.com/games",
    "ea": "https://www.ea.com/games",
    "sega": "https://www.sega.com/games",
    "square enix": "https://www.square-enix-games.com/",
    "rockstar": "https://www.rockstargames.com/games",
    "playstation": "https://www.playstation.com/games/",
    "xbox": "https://www.xbox.com/games",
    "activision": "https://www.activision.com/games",
    "bethesda": "https://bethesda.net/en/games",
}


def _normalize_title(title: str) -> str:
    title = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", title or "")
    title = re.sub(r"(?i)\b(v\d[\w.\-+]*|multi\d+|dlc|bonus content|repack|directors cut|deluxe edition)\b", " ", title)
    title = title.replace(":", " ")
    title = re.sub(r"[^a-zA-Z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip().lower()


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:80]


def resolve_official_links(game: dict[str, Any]) -> dict[str, str]:
    title = game.get("title", "")
    normalized = _normalize_title(title)
    links = {
        "official_site": "",
        "publisher_site": "",
        "steam_page": "",
        "source_confidence": "unknown",
    }

    for key, value in KNOWN_OFFICIAL_SITES.items():
        if key in normalized:
            links.update(value)
            return links

    company_text = " ".join([
        str(game.get("companies", "")),
        " ".join(game.get("tags", []) or []),
        " ".join(game.get("categories", []) or []),
    ]).lower()
    for publisher, url in PUBLISHER_DOMAINS.items():
        if publisher in company_text:
            links["publisher_site"] = url
            links["source_confidence"] = "likely"
            return links

    return links
