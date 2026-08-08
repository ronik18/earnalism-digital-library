"""Small, independently cacheable contracts for critical Home surfaces.

The canonical curation builder remains the sole selection and release-truth
authority. This module only projects that approved payload into bounded public
responses suitable for the critical hero and deferred listening rail.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


HERO_SCHEMA_VERSION = "home-hero-v1"
LISTENING_SCHEMA_VERSION = "home-listening-v1"
MAX_LISTENING_ITEMS = 6

_HERO_BOOK_FIELDS = (
    "slug",
    "title",
    "author",
    "language",
    "front_cover_url",
    "cover_alt_text",
    "cover_valid",
    "reader_enabled",
    "book_url",
    "reader_url",
)

_LISTENING_BOOK_FIELDS = (
    *_HERO_BOOK_FIELDS,
    "primary_cta_label",
    "primary_cta_url",
    "audiobook_enabled",
    "audiobook_release_gate",
    "audio_qa_status",
    "audio_duration_ms",
    "audiobook_url",
    "highlight_sync_enabled",
    "narrator",
    "narrator_name",
)


def _project(book: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: book[field] for field in fields if field in book and book[field] not in (None, "")}


def _revision(schema_version: str, value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f'{schema_version}-{hashlib.sha256(encoded).hexdigest()[:20]}'


def _source(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    return {
        key: source[key]
        for key in ("truth_source", "generated_at", "catalog_version")
        if source.get(key) not in (None, "")
    }


def build_home_hero_contract(payload: dict[str, Any]) -> dict[str, Any]:
    hero = payload.get("hero") if isinstance(payload.get("hero"), dict) else {}
    books = hero.get("carousel_books") if isinstance(hero.get("carousel_books"), list) else []
    projected_hero = {
        key: hero[key]
        for key in ("headline", "subheadline", "primary_cta", "secondary_cta")
        if hero.get(key) not in (None, "")
    }
    projected_hero["carousel_books"] = [_project(book, _HERO_BOOK_FIELDS) for book in books if isinstance(book, dict)]
    source = _source(payload)
    core = {"hero": projected_hero, "source": source}
    revision_core = {"hero": projected_hero, "source": {key: value for key, value in source.items() if key != "generated_at"}}
    return {
        "schema_version": HERO_SCHEMA_VERSION,
        "revision": _revision(HERO_SCHEMA_VERSION, revision_core),
        **core,
    }


def _approved_listening_book(book: dict[str, Any]) -> bool:
    slug = str(book.get("slug") or "").strip()
    endpoint = str(book.get("audiobook_url") or "").strip()
    qa_status = str(book.get("audio_qa_status") or "").strip().upper()
    return bool(
        slug
        and book.get("audiobook_enabled") is True
        and str(book.get("audiobook_release_gate") or "").strip().upper() == "APPROVED"
        and qa_status in {"APPROVED", "PASS", "PASSED", "QA_PASSED"}
        and endpoint == f"/api/reader/book/{slug}/audiobook"
        and book.get("cover_valid") is True
        and book.get("reader_enabled") is True
        and book.get("front_cover_url")
    )


def _listening_projection(book: dict[str, Any]) -> dict[str, Any]:
    projected = _project(book, _LISTENING_BOOK_FIELDS)
    projected.update({
        "cta_kind": "listen",
        "cta_label": "Start Listening",
        "cta_url": str(book.get("primary_cta_url") or f'/reader/{book["slug"]}?listen=1'),
        "audio_available": True,
        "audio_package_valid": True,
    })
    return projected


def build_home_listening_contract(payload: dict[str, Any], *, limit: int = 3) -> dict[str, Any]:
    rooms = payload.get("listening_rooms") if isinstance(payload.get("listening_rooms"), dict) else {}
    raw_items = rooms.get("items") if isinstance(rooms.get("items"), list) else []
    approved = [_listening_projection(book) for book in raw_items if isinstance(book, dict) and _approved_listening_book(book)]
    bounded_limit = min(MAX_LISTENING_ITEMS, max(1, int(limit)))
    items = approved[:bounded_limit]
    source = _source(payload)
    core = {
        "total": len(approved),
        "items": items,
        "source": source,
    }
    revision_core = {**core, "source": {key: value for key, value in source.items() if key != "generated_at"}}
    return {
        "schema_version": LISTENING_SCHEMA_VERSION,
        "revision": _revision(LISTENING_SCHEMA_VERSION, revision_core),
        **core,
    }
