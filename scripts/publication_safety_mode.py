#!/usr/bin/env python3
"""Publication safety helpers for draft-only book ingestion.

This module is intentionally small and side-effect free so importer scripts,
validation scripts, and tests can share the same owner-approved safety rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


APPROVED_RELEASE_ALLOWLIST = ("dracula",)

DRAFT_EDITORIAL_REVIEW_FLAGS: dict[str, Any] = {
    "readerStatus": "ready_for_editorial_review",
    "publicationStatus": "draft",
    "isPublic": False,
    "isLive": False,
    "showInPublicLibrary": False,
    "showInHomepage": False,
    "allowPublicReading": False,
    "allowCheckout": False,
    "allowPayment": False,
}

BACKEND_DRAFT_COMPATIBILITY_FLAGS: dict[str, Any] = {
    "is_published": False,
}

PUBLICATION_APPROVAL_CHECKLIST = (
    "source URL reviewed",
    "public-domain/legal note reviewed",
    "raw source archived",
    "cleaned chapters inspected",
    "no Project Gutenberg or Wikisource boilerplate remains in reader-facing content",
    "no unapproved cover art, images, introductions, annotations, translations, or publisher material included",
    "chapter boundaries are correct",
    "typography and formatting are reader-ready",
    "Bengali Unicode displays correctly where applicable",
    "the book is intentionally selected for public release",
)

PUBLICATION_STATUS_LIVE_VALUES = {
    "live",
    "published",
    "public",
    "live_approved",
    "approved_to_publish",
    "published_core_reading_only",
}

PUBLIC_TRUTHY_FIELDS = (
    "isPublic",
    "isLive",
    "showInPublicLibrary",
    "showInHomepage",
    "allowPublicReading",
    "allowCheckout",
    "allowPayment",
    "is_published",
    "approved_to_publish",
    "public_metadata_allowed",
    "public_cta_allowed",
)

PUBLIC_STATUS_FIELDS = (
    "publicationStatus",
    "publication_status",
    "launch_status",
)


def normalize_slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")


def book_slug(book: dict[str, Any]) -> str:
    return normalize_slug(book.get("slug") or book.get("book_slug") or book.get("title"))


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "allowed", "approved"}


def apply_draft_editorial_review_flags(book: dict[str, Any]) -> dict[str, Any]:
    """Return a copy forced into the owner-approved draft import state."""

    protected = dict(book)
    protected.update(DRAFT_EDITORIAL_REVIEW_FLAGS)
    protected.update(BACKEND_DRAFT_COMPATIBILITY_FLAGS)
    return protected


def validate_import_book_safety(
    book: dict[str, Any],
    *,
    approved_release_allowlist: tuple[str, ...] = APPROVED_RELEASE_ALLOWLIST,
    require_draft_fields: bool = True,
) -> list[str]:
    """Return publication-safety violations for a single imported book."""

    slug = book_slug(book)
    if slug in approved_release_allowlist:
        return []

    issues: list[str] = []
    if require_draft_fields:
        for key, expected in DRAFT_EDITORIAL_REVIEW_FLAGS.items():
            if book.get(key) != expected:
                issues.append(f"{slug or 'unknown'}: {key} must be {expected!r} for imported draft books")
        if book.get("is_published") is not False:
            issues.append(f"{slug or 'unknown'}: is_published must be False for imported draft books")

    for key in PUBLIC_TRUTHY_FIELDS:
        if is_truthy(book.get(key)):
            issues.append(f"{slug or 'unknown'}: {key} must not be truthy unless slug is explicitly allowlisted")

    for key in PUBLIC_STATUS_FIELDS:
        status = str(book.get(key) or "").strip().lower()
        if status in PUBLICATION_STATUS_LIVE_VALUES:
            issues.append(f"{slug or 'unknown'}: {key}={book.get(key)!r} is blocked for non-allowlisted imports")

    return issues


def manifest_books(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        books = payload.get("books")
        if isinstance(books, list):
            return [item for item in books if isinstance(item, dict)]
        return [payload]
    return []


def validate_manifest_payload(
    payload: Any,
    *,
    approved_release_allowlist: tuple[str, ...] = APPROVED_RELEASE_ALLOWLIST,
    require_draft_fields: bool = True,
) -> list[str]:
    issues: list[str] = []
    for book in manifest_books(payload):
        issues.extend(
            validate_import_book_safety(
                book,
                approved_release_allowlist=approved_release_allowlist,
                require_draft_fields=require_draft_fields,
            )
        )
    return issues


def validate_manifest_file(path: Path, *, require_draft_fields: bool = True) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_manifest_payload(payload, require_draft_fields=require_draft_fields)
    return {
        "path": str(path),
        "book_count": len(manifest_books(payload)),
        "approved_release_allowlist": list(APPROVED_RELEASE_ALLOWLIST),
        "status": "PASS" if not issues else "BLOCKED",
        "issues": issues,
    }
