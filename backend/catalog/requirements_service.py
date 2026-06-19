"""Resolved one-source system requirements pipeline for Arcadia catalog games."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from backend import cache
from backend.catalog.title_matcher import compare_titles, normalize_title
from backend.config import HEADERS, REQUEST_TIMEOUT, CACHE_TTL_LONG


def requirements_with_meta(reqs: dict | None, source: str, confidence: str = "high", status: str = "available", **extra: Any) -> dict:
    value = dict(reqs or {})
    value.update({
        "requirements_source": source,
        "requirements_confidence": confidence,
        "requirements_status": status,
        "requirements_checked_at": int(time.time()),
    })
    value.update({k: v for k, v in extra.items() if v not in (None, "")})
    return value


def html_to_requirement_text(html: str) -> str:
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", str(html or ""))
    text = re.sub(r"(?i)</\s*(li|p|div)\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text.replace("&nbsp;", " ")).strip()


def _extract_req_value(text: str, names: tuple[str, ...]) -> str:
    escaped = "|".join(re.escape(name) for name in names)
    match = re.search(rf"(?:{escaped})\s*:?\s*([^\n\r]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip(" -:")


def parse_requirements_text(text: str) -> dict:
    reqs = {"ram_min": 0, "ram_rec": 0, "space": 0, "cpu": "", "gpu": ""}
    if not text:
        return reqs
    normalized = str(text).replace("|", "\n").replace("=", ":")
    ram_matches = re.findall(r"(?:Memory|RAM)\s*:?\s*(\d+(?:\.\d+)?)\s*GB", normalized, re.IGNORECASE)
    if not ram_matches:
        ram_matches = re.findall(r"(\d+(?:\.\d+)?)\s*GB\s*(?:RAM|Memory)", normalized, re.IGNORECASE)
    if ram_matches:
        reqs["ram_min"] = int(float(ram_matches[0]))
        reqs["ram_rec"] = int(float(ram_matches[1])) if len(ram_matches) > 1 else reqs["ram_min"]
    storage_match = re.search(
        r"(?:Storage|Disk Space|Free Space|Installation Space)\s*:?\s*(?:up to\s*)?(?:about\s*)?(\d+(?:\.\d+)?)\s*GB",
        normalized,
        re.IGNORECASE,
    )
    if storage_match:
        reqs["space"] = int(float(storage_match.group(1)))
    reqs["cpu"] = _extract_req_value(normalized, ("Processor", "CPU"))
    reqs["gpu"] = _extract_req_value(normalized, ("Graphics", "Video Card", "GPU"))
    return reqs


def has_real_requirements(reqs: dict | None) -> bool:
    value = reqs or {}
    return any([
        int(value.get("ram_min") or 0) > 0,
        int(value.get("ram_rec") or 0) > 0,
        str(value.get("cpu") or "").strip(),
        str(value.get("gpu") or "").strip(),
    ])


def display_requirements(game: dict | None = None) -> dict:
    reqs = dict((game or {}).get("requirements") or {})
    if has_real_requirements(reqs):
        reqs.setdefault("requirements_source", "Source Page")
        reqs.setdefault("requirements_confidence", "high")
        reqs.setdefault("requirements_status", "available")
        reqs.setdefault("requirements_checked_at", int(time.time()))
        return reqs
    return requirements_with_meta({"pending": True}, "Arcadia", "low", "checking")


@cache.cached(ttl=CACHE_TTL_LONG)
def fetch_steam_requirements(title: str, steam_page: str = "") -> dict:
    normalized = normalize_title(title)
    if not normalized:
        return {}
    app_id = ""
    page_match = re.search(r"store\.steampowered\.com/app/(\d+)", steam_page or "")
    if page_match:
        app_id = page_match.group(1)
    else:
        try:
            search = requests.get(
                "https://store.steampowered.com/api/storesearch/",
                params={"term": normalized, "cc": "us", "l": "en"},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            search.raise_for_status()
            items = (search.json() or {}).get("items") or []
            for item in items[:6]:
                match = compare_titles(title, item.get("name", ""))
                if match.status in {"exact", "confident"} and match.score >= 90:
                    app_id = str(item.get("id") or "")
                    break
        except Exception:
            return {}
    if not app_id:
        return {}
    try:
        details = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": app_id, "filters": "basic,pc_requirements", "cc": "us", "l": "en"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        details.raise_for_status()
        payload = (details.json() or {}).get(str(app_id), {})
        data = payload.get("data") or {}
        steam_name = (data.get("basic") or {}).get("name", "")
        match = compare_titles(title, steam_name)
        if steam_name and match.status not in {"exact", "confident"}:
            return {}
        pc = data.get("pc_requirements") or {}
        combined = "\n".join(
            part for part in (
                html_to_requirement_text(pc.get("minimum", "")),
                html_to_requirement_text(pc.get("recommended", "")),
            )
            if part
        )
        reqs = parse_requirements_text(combined)
        if has_real_requirements(reqs):
            reqs["steam_page"] = f"https://store.steampowered.com/app/{app_id}/"
            return requirements_with_meta(
                reqs,
                "Steam",
                "high",
                "available",
                matched_specs_title=steam_name,
                matched_specs_url=reqs["steam_page"],
                match_score=match.score,
                match_reason=match.reason,
            )
    except Exception:
        return {}
    return {}


@cache.cached(ttl=CACHE_TTL_LONG)
def fetch_pcgamingwiki_requirements(title: str) -> dict:
    normalized = normalize_title(title)
    if not normalized:
        return {}
    try:
        search = requests.get(
            "https://www.pcgamingwiki.com/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": normalized,
                "format": "json",
                "utf8": 1,
                "srlimit": 6,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        search.raise_for_status()
        results = (search.json() or {}).get("query", {}).get("search") or []
        page_title = ""
        best_match = None
        for item in results:
            match = compare_titles(title, item.get("title", ""))
            if match.status in {"exact", "confident"} and match.score >= 92:
                page_title = item.get("title", "")
                best_match = match
                break
        if not page_title or not best_match:
            return {}
        page = requests.get(
            "https://www.pcgamingwiki.com/w/api.php",
            params={"action": "parse", "page": page_title, "prop": "wikitext", "format": "json", "utf8": 1},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        page.raise_for_status()
        wikitext = ((page.json() or {}).get("parse", {}).get("wikitext", {}) or {}).get("*", "")
        reqs = parse_requirements_text(wikitext)
        if has_real_requirements(reqs):
            page_url = f"https://www.pcgamingwiki.com/wiki/{quote_plus(page_title.replace(' ', '_'))}"
            reqs["pcgamingwiki_page"] = page_url
            return requirements_with_meta(
                reqs,
                "PCGamingWiki",
                "medium",
                "available",
                matched_specs_title=page_title,
                matched_specs_url=page_url,
                match_score=best_match.score,
                match_reason=best_match.reason,
            )
    except Exception:
        return {}
    return {}


def resolve_requirements(title: str, source_requirements: dict | None = None, steam_page: str = "") -> dict:
    source = dict(source_requirements or {})
    if has_real_requirements(source) and source.get("requirements_status") != "unavailable":
        return requirements_with_meta(
            source,
            source.get("requirements_source") or "Source Page",
            source.get("requirements_confidence") or "high",
            "available",
        )
    steam = fetch_steam_requirements(title, steam_page)
    if steam:
        return {**source, **steam}
    wiki = fetch_pcgamingwiki_requirements(title)
    if wiki:
        return {**source, **wiki}
    return requirements_with_meta(source, "Arcadia", "low", "unavailable")

