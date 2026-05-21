"""
Live news aggregation for Arcadia Core.

Uses small RSS/Atom requests and caches the normalized result locally. The app
links users to original sources instead of republishing full articles.
"""

from __future__ import annotations

import email.utils
import html
import re
import time
import urllib.request
import concurrent.futures
import xml.etree.ElementTree as ET
from typing import Any

from backend import cache
from backend.config import HEADERS, REQUEST_TIMEOUT


NEWS_CACHE_KEY = "arcadia_live_news"
NEWS_TTL = 15 * 60

FEEDS = [
    {"source": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "category": "PC"},
    {"source": "GameSpot", "url": "https://www.gamespot.com/feeds/news/", "category": "Releases"},
    {"source": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed", "category": "PC"},
    {"source": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "category": "PC"},
    {"source": "The Verge Gaming", "url": "https://www.theverge.com/rss/games/index.xml", "category": "Hardware"},
    {"source": "IGN", "url": "https://feeds.feedburner.com/ign/games-all", "category": "PC"},
    {"source": "PCGamesN", "url": "https://www.pcgamesn.com/mainrss.xml", "category": "PC"},
    {"source": "PlayStation Blog", "url": "https://blog.playstation.com/feed/", "category": "Official", "official": True},
    {"source": "Xbox Wire", "url": "https://news.xbox.com/en-us/feed/", "category": "Official", "official": True},
    {"source": "Ubisoft News", "url": "https://news.ubisoft.com/en-us/rss", "category": "Official", "official": True},
    {"source": "Capcom News", "url": "https://news.capcomusa.com/feed", "category": "Official", "official": True},
    {"source": "Steam News - TEKKEN 8", "url": "https://store.steampowered.com/feeds/news/app/1778820", "category": "Official", "official": True, "game": "TEKKEN 8"},
    {"source": "Steam News - Dragon Ball: Sparking! ZERO", "url": "https://store.steampowered.com/feeds/news/app/1790600", "category": "Official", "official": True, "game": "Dragon Ball: Sparking! ZERO"},
]

UPCOMING_GAMES = [
    {
        "title": "Upcoming PC games release calendar",
        "source": "PC Gamer",
        "url": "https://www.pcgamer.com/games/new-pc-games-2026/",
        "category": "Releases",
    },
    {
        "title": "2026 upcoming games release schedule",
        "source": "GameSpot",
        "url": "https://www.gamespot.com/articles/2026-upcoming-games-release-schedule/1100-6534941/",
        "category": "Releases",
    },
    {
        "title": "Upcoming PC games",
        "source": "PCGamesN",
        "url": "https://www.pcgamesn.com/upcoming-pc-games",
        "category": "Releases",
    },
]

UPCOMING_EVENTS = [
    {
        "title": "Future Games Show",
        "source": "GamesRadar",
        "url": "https://www.gamesradar.com/future-games-show/",
        "category": "Events",
    },
    {
        "title": "PC Gaming Show",
        "source": "PC Gamer",
        "url": "https://www.pcgamer.com/pc-gaming-show/",
        "category": "Events",
    },
    {
        "title": "Gaming showcases and event coverage",
        "source": "GameSpot",
        "url": "https://www.gamespot.com/gallery/every-video-game-showcase-to-watch-in-2026/2900-7446/",
        "category": "Events",
    },
]


def _text(el) -> str:
    if el is None or el.text is None:
        return ""
    return html.unescape(el.text.strip())


def _find_child(item, names: tuple[str, ...]):
    for child in item:
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names:
            return child
    return None


def _parse_date(value: str) -> float:
    if not value:
        return 0
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.timestamp()
    except Exception:
        return 0


def _image_from_item(item) -> str:
    for child in item.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in {"thumbnail", "content"} and child.attrib.get("url"):
            return child.attrib["url"]
        if local == "enclosure" and child.attrib.get("type", "").startswith("image") and child.attrib.get("url"):
            return child.attrib["url"]
    return ""


def _fetch_feed(feed: dict[str, Any]) -> list[dict[str, Any]]:
    req = urllib.request.Request(feed["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        raw = resp.read(2 * 1024 * 1024)
    root = ET.fromstring(raw)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    articles = []
    for item in items[:10]:
        title = _text(_find_child(item, ("title",)))
        link_el = _find_child(item, ("link",))
        link = ""
        if link_el is not None:
            link = link_el.attrib.get("href", "") or _text(link_el)
        date_text = _text(_find_child(item, ("pubdate", "published", "updated")))
        summary = _text(_find_child(item, ("description", "summary")))
        summary = html.unescape(summary)
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = " ".join(summary.split())[:220]
        if title and link:
            articles.append({
                "title": title,
                "source": feed["source"],
                "url": link,
                "published_at": _parse_date(date_text),
                "summary": summary,
                "image": _image_from_item(item),
                "category": feed.get("category", "PC"),
                "is_official": bool(feed.get("official")),
                "game": feed.get("game", ""),
            })
    return articles


def get_news(force_refresh: bool = False) -> dict[str, Any]:
    cached = cache.get(NEWS_CACHE_KEY)
    if cached and not force_refresh:
        cached["stale"] = False
        return cached

    articles: list[dict[str, Any]] = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(FEEDS))) as executor:
        futures = {executor.submit(_fetch_feed, feed): feed for feed in FEEDS}
        done, pending = concurrent.futures.wait(futures, timeout=max(REQUEST_TIMEOUT, 18))
        for future in done:
            feed = futures[future]
            try:
                articles.extend(future.result())
            except Exception as exc:
                errors.append(f"{feed['source']}: {exc}")
        for future in pending:
            feed = futures[future]
            future.cancel()
            errors.append(f"{feed['source']}: timed out")

    seen = set()
    deduped = []
    for item in sorted(articles, key=lambda x: x.get("published_at", 0), reverse=True):
        key = item["url"].split("?", 1)[0].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    payload = {
        "updated_at": time.time(),
        "refresh_seconds": NEWS_TTL,
        "articles": deduped[:48],
        "upcoming_games": UPCOMING_GAMES,
        "upcoming_events": UPCOMING_EVENTS,
        "sources": [{"source": f["source"], "url": f["url"], "category": f.get("category", "PC"), "official": bool(f.get("official")), "game": f.get("game", "")} for f in FEEDS],
        "errors": errors,
        "stale": bool(errors) and not deduped,
    }
    if deduped:
        cache.set(NEWS_CACHE_KEY, payload, NEWS_TTL)
        return payload
    if cached:
        cached["stale"] = True
        cached["errors"] = errors
        return cached
    return payload



