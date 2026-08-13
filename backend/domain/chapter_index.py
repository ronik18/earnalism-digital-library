"""Deterministic chapter-index labels shared by reader API surfaces."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping


CHAPTER_INDEX_CONTRACT_VERSION = "chapter-index.v1"

_FORMAT_MARKS_RE = re.compile(r"[_*`]+")
_CONTINUATION_SUFFIX_RE = re.compile(
    r"\s*[.:]?\s*(?:(?:--|—|-)\s*)?continued\.?\s*$",
    re.IGNORECASE,
)
_STRUCTURED_TITLE_RE = re.compile(
    r"^(chapter|letter|book|part|section|canto|volume|poem|gitanjali)\s+"
    r"([ivxlcdm]+|\d+)[.:]?\s*(.*)$",
    re.IGNORECASE,
)
_ALL_CAPS_WORD_RE = re.compile(r"\b([a-z])([a-z'’.]*)", re.IGNORECASE)
_HONORIFIC_RE = re.compile(r"\b(Dr|Mr|Mrs|Ms)\b\.?", re.IGNORECASE)
_ACRONYMS = {"ai", "api", "css", "dna", "html", "pdf", "uk", "us", "usa"}


def _roman_to_int(value: str) -> int | None:
    text = str(value or "").upper()
    if not text or not re.fullmatch(r"[IVXLCDM]+", text):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for character in reversed(text):
        current = values[character]
        total += -current if current < previous else current
        previous = max(previous, current)
    return total if total > 0 else None


def _smart_title_case(value: str) -> str:
    text = str(value or "").strip()
    letters = re.findall(r"[A-Za-z]", text)
    uppercase = re.findall(r"[A-Z]", text)
    if not letters or len(uppercase) / len(letters) < 0.72:
        return text

    def replace_word(match: re.Match[str]) -> str:
        word = match.group(0)
        lowered = word.lower()
        if lowered in _ACRONYMS:
            return lowered.upper()
        return f"{lowered[0].upper()}{lowered[1:]}"

    normalized = _ALL_CAPS_WORD_RE.sub(replace_word, text.lower())
    return _HONORIFIC_RE.sub(lambda match: f"{match.group(1).title()}.", normalized)


def normalize_chapter_display_title(title: Any) -> str:
    """Return a reader-safe title without mutating source metadata."""

    original = str(title or "").strip()
    if not original:
        return ""
    cleaned = _FORMAT_MARKS_RE.sub("", original)
    cleaned = _CONTINUATION_SUFFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    match = _STRUCTURED_TITLE_RE.match(cleaned)
    if not match:
        return _smart_title_case(cleaned)
    unit, numeral, remainder = match.groups()
    number = int(numeral) if numeral.isdigit() else (_roman_to_int(numeral) or numeral.upper())
    unit_label = f"{unit.title()} {number}"
    subtitle = _smart_title_case(remainder)
    return f"{unit_label}. {subtitle}" if subtitle else unit_label


def chapter_index_entry(
    chapter: Mapping[str, Any],
    *,
    position: int,
    total: int,
) -> dict[str, Any]:
    """Decorate one chapter with a stable visual/accessibility index contract."""

    source_title = str(chapter.get("title") or "").strip()
    display_title = normalize_chapter_display_title(source_title)
    match = _STRUCTURED_TITLE_RE.match(display_title)
    unit_label = ""
    subtitle = ""
    if match:
        unit, numeral, remainder = match.groups()
        unit_label = f"{unit.title()} {numeral}"
        subtitle = remainder.strip().lstrip(".:-— ").strip()

    width = max(2, len(str(max(int(total or 0), 1))))
    sequence_label = str(max(int(position or 0), 1)).zfill(width)
    primary_title = subtitle or unit_label or display_title or f"Section {position}"
    secondary_label = unit_label if subtitle else ""
    return {
        **dict(chapter),
        "index_contract": CHAPTER_INDEX_CONTRACT_VERSION,
        "index_sequence": max(int(position or 0), 1),
        "index_sequence_label": sequence_label,
        "display_title": display_title or primary_title,
        "index_title": primary_title,
        "index_secondary_label": secondary_label,
    }


def build_chapter_index_entries(chapters: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Sort and decorate a complete chapter list deterministically."""

    indexed = list(enumerate(chapters))
    indexed.sort(
        key=lambda pair: (
            int(pair[1].get("order", pair[0]) or 0),
            str(pair[1].get("id") or ""),
            pair[0],
        )
    )
    total = len(indexed)
    return [
        chapter_index_entry(chapter, position=position, total=total)
        for position, (_source_index, chapter) in enumerate(indexed, start=1)
    ]
