from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import import_books
from scripts.publication_safety_mode import (
    APPROVED_RELEASE_ALLOWLIST,
    DRAFT_EDITORIAL_REVIEW_FLAGS,
    PUBLICATION_APPROVAL_CHECKLIST,
    apply_draft_editorial_review_flags,
    validate_import_book_safety,
    validate_manifest_payload,
)


def draft_book(slug: str = "frankenstein") -> dict:
    return apply_draft_editorial_review_flags(
        {
            "slug": slug,
            "title": "Frankenstein",
            "author": "Mary Wollstonecraft Shelley",
        }
    )


def test_import_draft_flags_are_exact_owner_required_values():
    book = draft_book()

    for key, expected in DRAFT_EDITORIAL_REVIEW_FLAGS.items():
        assert book[key] == expected
    assert book["is_published"] is False


def test_non_allowlisted_live_or_public_flags_are_blocked():
    unsafe = draft_book("sherlock-holmes")
    unsafe["publicationStatus"] = "live"
    unsafe["isPublic"] = True
    unsafe["allowPayment"] = True

    issues = validate_import_book_safety(unsafe)

    assert any("publicationStatus" in issue for issue in issues)
    assert any("isPublic" in issue for issue in issues)
    assert any("allowPayment" in issue for issue in issues)


def test_only_dracula_is_allowlisted_for_existing_live_release():
    assert APPROVED_RELEASE_ALLOWLIST == ("dracula",)
    assert validate_import_book_safety(
        {
            "slug": "dracula",
            "publicationStatus": "live",
            "isPublic": True,
            "isLive": True,
            "allowPublicReading": True,
            "is_published": True,
        }
    ) == []


def test_manifest_batch_of_10_new_books_passes_only_as_drafts():
    manifest = {
        "books": [
            draft_book(f"draft-book-{index}")
            for index in range(10)
        ]
    }

    assert validate_manifest_payload(manifest) == []

    manifest["books"][3]["showInPublicLibrary"] = True
    issues = validate_manifest_payload(manifest)

    assert any("draft-book-3" in issue and "showInPublicLibrary" in issue for issue in issues)


def test_importer_metadata_forces_draft_even_if_manifest_requests_publication():
    warnings: list[str] = []
    metadata = import_books.metadata_defaults(
        {
            "title": "A Draft Book",
            "author": "A Writer",
            "category_slug": "literary-fiction",
            "is_published": True,
            "availability": "published",
            "publicationStatus": "live",
        },
        word_count=5000,
        warnings=warnings,
    )

    assert metadata["is_published"] is False
    assert any("publication safety mode kept the book as draft" in warning for warning in warnings)


def test_publication_approval_checklist_documents_manual_human_gate():
    assert "source URL reviewed" in PUBLICATION_APPROVAL_CHECKLIST
    assert "cleaned chapters inspected" in PUBLICATION_APPROVAL_CHECKLIST
    assert "the book is intentionally selected for public release" in PUBLICATION_APPROVAL_CHECKLIST


def test_publication_safety_cli_fails_for_non_allowlisted_live_book(tmp_path: Path):
    manifest_path = tmp_path / "book_import_manifest.json"
    manifest_path.write_text(
        json.dumps({"books": [draft_book("new-book") | {"allowCheckout": True}]}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_publication_safety_mode.py",
            str(manifest_path),
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "BLOCKED" in completed.stdout
    assert "allowCheckout" in completed.stdout
