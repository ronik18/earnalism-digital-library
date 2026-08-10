"""Canonical catalog normalization rules."""

import re
import unicodedata
import uuid
from typing import Optional


DEFAULT_CATEGORY_SLUG = "literary-fiction"
CANONICAL_CATEGORY_SLUGS = {
    "bengali-classics",
    "literary-fiction",
    "young-readers",
    "business",
    "technology",
    "history-strategy",
    "adventure",
    "science-fiction",
    "gothic-fiction",
}
LEGACY_CATEGORY_SLUG_MAP = {
    "classic-literature": "literary-fiction",
    "literature": "literary-fiction",
    "children-classics": "young-readers",
    "children": "young-readers",
    "business-entrepreneurship": "business",
    "technology-ai": "technology",
    "history-politics": "history-strategy",
    "bengali": "bengali-classics",
    "bengali-reading": "bengali-classics",
}


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def slugify(text: str, fallback: Optional[str] = None) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", text).strip("-")
    return slug or fallback or str(uuid.uuid4())[:8]


def category_value_to_slug(value: str) -> str:
    text = normalize_text(value or "")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def normalize_category_slug(value: str) -> str:
    slug = category_value_to_slug(value)
    return LEGACY_CATEGORY_SLUG_MAP.get(slug, slug)


def canonical_category_slug(value: str, default: str = DEFAULT_CATEGORY_SLUG) -> str:
    slug = normalize_category_slug(value)
    if slug in CANONICAL_CATEGORY_SLUGS:
        return slug
    return default
