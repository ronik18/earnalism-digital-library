from __future__ import annotations

import json
import importlib
import subprocess
import sys
from pathlib import Path

from scripts import import_books
from scripts.publication_safety_mode import (
    APPROVED_RELEASE_ALLOWLIST,
    DRAFT_EDITORIAL_REVIEW_FLAGS,
    FIRST_BATCH_DRAFT_IMPORT_SLUGS,
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


def test_publication_allowlist_requires_root_and_backend_controlled_launch_parity():
    root = Path(__file__).resolve().parents[2]
    root_launch = json.loads((root / "data" / "controlled_launch.json").read_text(encoding="utf-8"))
    backend_launch = json.loads((root / "backend" / "data" / "controlled_launch.json").read_text(encoding="utf-8"))
    expected = tuple(sorted(set(root_launch["live_approved_slugs"]) & set(backend_launch["live_approved_slugs"])))

    assert APPROVED_RELEASE_ALLOWLIST == expected
    assert "book-d19e96859f" in APPROVED_RELEASE_ALLOWLIST
    assert "not-controlled" not in APPROVED_RELEASE_ALLOWLIST
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
            draft_book(slug)
            for slug in FIRST_BATCH_DRAFT_IMPORT_SLUGS
        ]
    }

    assert len(FIRST_BATCH_DRAFT_IMPORT_SLUGS) == 10
    assert validate_manifest_payload(manifest) == []

    manifest["books"][3]["showInPublicLibrary"] = True
    issues = validate_manifest_payload(manifest)

    assert any(
        FIRST_BATCH_DRAFT_IMPORT_SLUGS[3] in issue and "showInPublicLibrary" in issue
        for issue in issues
    )


def test_first_batch_slugs_are_blocked_from_live_public_or_payment_flags():
    for slug in FIRST_BATCH_DRAFT_IMPORT_SLUGS:
        unsafe = draft_book(slug) | {
            "publicationStatus": "live",
            "isPublic": True,
            "isLive": True,
            "showInPublicLibrary": True,
            "allowPublicReading": True,
            "allowCheckout": True,
            "allowPayment": True,
            "is_published": True,
        }

        issues = validate_import_book_safety(unsafe)

        assert issues, f"{slug} unexpectedly passed with live/public flags"
        assert any("publicationStatus" in issue for issue in issues)
        assert any("allowPayment" in issue for issue in issues)
        assert any("is_published" in issue for issue in issues)


def test_missing_public_flags_do_not_default_into_public_backend_state(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_publication_safety_test")
    monkeypatch.setenv("JWT_SECRET", "publication-safety-test-secret")

    server = importlib.import_module("backend.server")

    book_input = server.BookIn(title="Draft Import", category_slug="literary-fiction")
    book_model = server.Book(slug="draft-import", title="Draft Import", category_slug="literary-fiction")

    assert book_input.readerStatus == "ready_for_editorial_review"
    assert book_input.publicationStatus == "draft"
    assert book_input.is_published is False
    assert book_model.is_published is False


def test_backend_publish_blocker_rejects_non_allowlisted_books(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_publication_safety_test")
    monkeypatch.setenv("JWT_SECRET", "publication-safety-test-secret")

    server = importlib.import_module("backend.server")

    blockers = server._publish_blockers(
        {
            "slug": "frankenstein-science-ethics-guide",
            "title": "Frankenstein Science & Ethics Guide",
            "is_published": True,
            "cover_image_url": "/assets/covers/frankenstein.webp",
            "chapters": [],
            "rights_metadata": {},
        }
    )

    assert any("allowlist" in blocker for blocker in blockers)


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
