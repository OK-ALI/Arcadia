"""Shared title normalization and confidence scoring for Arcadia matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

NOISE_WORDS = {
    "a", "an", "and", "the", "of", "for", "with", "game",
    "edition", "editions", "deluxe", "ultimate", "complete", "digital",
    "gold", "goty", "definitive", "enhanced", "remastered", "remaster",
    "remake", "palace", "repack", "lossless", "fitgirl", "dodi", "multi", "bonus",
    "bonuses", "dlc", "dlcs", "pack", "content", "version", "build",
    "steam", "epic", "library", "local", "install",
}

WEAK_FRANCHISE_WORDS = {
    "need", "speed", "call", "duty", "assassin", "creed", "grand", "theft",
    "auto", "resident", "evil", "final", "fantasy", "star", "wars",
    "spider", "man", "marvel", "dragon", "ball",
}

ROMAN_NUMERALS = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
    "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
}


@dataclass(frozen=True)
class TitleMatch:
    score: int
    status: str
    reason: str
    source_title: str
    candidate_title: str


def normalize_title(title: str) -> str:
    value = str(title or "")
    for bad in ("â„¢", "Â®"):
        value = value.replace(bad, " ")
    value = value.translate(str.maketrans({
        "™": " ", "®": " ", "©": " ",
        "’": "'", "‘": "'", "“": '"', "”": '"',
    }))
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"(?i)\b(v|ver|version|build)\s*[\d][\w.\-+]*", " ", value)
    value = re.sub(r"(?i)\b(?:multi|language|update)\s*\d*\b", " ", value)
    value = re.sub(r"(?i)\b(?:bonus(?:es)?|soundtrack|ost|dlc(?:s)?|pack|content)\b", " ", value)
    value = re.sub(
        r"(?i)\b(?:deluxe|ultimate|complete|digital|gold|goty|definitive|enhanced|remaster(?:ed)?|remake|collector'?s?|standard|premium|palace)\b",
        " ",
        value,
    )
    value = re.sub(r"(?i)\b(?:lossless|repack|fitgirl|dodi|steam library|epic games|local install|arcadia)\b", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    tokens = []
    for token in value.lower().split():
        tokens.append(ROMAN_NUMERALS.get(token, token))
    return re.sub(r"\s+", " ", " ".join(tokens)).strip()


def compact_title(title: str) -> str:
    return re.sub(r"\s+", "", normalize_title(title))


def title_tokens(title: str) -> list[str]:
    return [token for token in normalize_title(title).split() if token and token not in NOISE_WORDS]


def required_number_tokens(title: str) -> set[str]:
    return {token for token in title_tokens(title) if token.isdigit()}


def strong_tokens(title: str) -> set[str]:
    return {
        token for token in title_tokens(title)
        if len(token) >= 4 and token not in WEAK_FRANCHISE_WORDS and not token.isdigit()
    }


def title_aliases(*values: str) -> list[str]:
    aliases: list[str] = []
    for value in values:
        raw = str(value or "").strip()
        cleaned = normalize_title(raw)
        compact = compact_title(raw)
        for candidate in (raw, cleaned, compact):
            if candidate and candidate not in aliases:
                aliases.append(candidate)
    return aliases


def _sequence_score(left: str, right: str) -> int:
    if not left or not right:
        return 0
    return int(SequenceMatcher(None, left, right).ratio() * 100)


def compare_titles(source: str, candidate: str) -> TitleMatch:
    source_norm = normalize_title(source)
    candidate_norm = normalize_title(candidate)
    if not source_norm or not candidate_norm:
        return TitleMatch(0, "none", "empty title", source, candidate)
    if source_norm == candidate_norm:
        return TitleMatch(100, "exact", "cleaned title exact match", source, candidate)

    source_numbers = required_number_tokens(source)
    candidate_numbers = required_number_tokens(candidate)
    if source_numbers and candidate_numbers and source_numbers != candidate_numbers:
        return TitleMatch(0, "none", "required sequel numbers differ", source, candidate)

    source_tokens = set(title_tokens(source))
    candidate_tokens = set(title_tokens(candidate))
    if not source_tokens or not candidate_tokens:
        return TitleMatch(0, "none", "no useful tokens", source, candidate)

    overlap = source_tokens & candidate_tokens
    if not overlap:
        return TitleMatch(0, "none", "no token overlap", source, candidate)

    source_strong = strong_tokens(source)
    candidate_strong = strong_tokens(candidate)
    strong_overlap = source_strong & candidate_strong
    min_token_count = min(len(source_tokens), len(candidate_tokens))
    short_title = min_token_count <= 2
    token_ratio = len(overlap) / max(1, min_token_count)
    union_ratio = len(overlap) / max(1, len(source_tokens | candidate_tokens))
    compact_score = _sequence_score(compact_title(source), compact_title(candidate))

    if source_numbers and not source_numbers.issubset(candidate_numbers or source_numbers):
        return TitleMatch(0, "none", "missing required sequel number", source, candidate)
    if short_title and source_norm != candidate_norm and compact_score < 94:
        return TitleMatch(0, "none", "short title requires near exact match", source, candidate)
    if source_strong and not strong_overlap and source_norm != candidate_norm:
        return TitleMatch(0, "none", "unique title token missing", source, candidate)
    if token_ratio < (0.75 if not short_title else 1.0):
        return TitleMatch(0, "none", "insufficient token overlap", source, candidate)

    score = int(token_ratio * 45 + union_ratio * 25 + compact_score * 0.30)
    if source_numbers and source_numbers.issubset(candidate_numbers):
        score += 5
    if strong_overlap:
        score += min(10, len(strong_overlap) * 4)
    score = max(0, min(99, score))

    if score >= 92:
        status = "confident"
    elif score >= 84:
        status = "uncertain"
    else:
        status = "none"
    reason = f"tokens={len(overlap)}, strong={len(strong_overlap)}, compact={compact_score}"
    return TitleMatch(score, status, reason, source, candidate)


def best_title_match(source: str, candidates: Iterable[dict | str]) -> tuple[dict | str | None, TitleMatch]:
    best_item: dict | str | None = None
    best_match = TitleMatch(0, "none", "no candidates", source, "")
    runner_up = 0
    for item in candidates:
        candidate_title = item.get("title") if isinstance(item, dict) else str(item)
        match = compare_titles(source, candidate_title or "")
        if match.score > best_match.score:
            runner_up = best_match.score
            best_match = match
            best_item = item
        elif match.score > runner_up:
            runner_up = match.score
    if best_match.score and runner_up and best_match.score - runner_up < 5:
        best_match = TitleMatch(best_match.score, "uncertain", f"close candidate conflict ({runner_up})", best_match.source_title, best_match.candidate_title)
    return best_item, best_match
