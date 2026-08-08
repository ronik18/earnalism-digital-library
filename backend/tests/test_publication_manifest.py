from __future__ import annotations

import json
import hashlib
from pathlib import Path

from backend.publication_manifest import (
    AUDIO_NOT_REQUESTED,
    READER_APPROVED,
    READER_READY,
    build_manifest,
    canonical_sha256,
    manifest_reader_exposed,
    validate_manifest,
)
from scripts.publication_manifest_conveyor import migrate_import_metadata
from backend.catalog_truth import (
    can_expose_reader,
    clear_controlled_artifact_caches,
    load_controlled_artifact_book,
)


ROOT = Path(__file__).resolve().parents[2]
SHERLOCK = ROOT / "data" / "controlled_publications" / "the-adventures-of-sherlock-holmes"


def test_sherlock_pilot_is_reader_ready_without_audio_or_commerce():
    manifest = build_manifest(SHERLOCK, generated_at="2026-08-08T00:00:00Z")

    assert manifest["reader_release"]["status"] == READER_READY
    assert manifest["reader_release"]["blockers"] == []
    assert manifest["content"]["chapter_count"] == 12
    assert manifest["audio_release"] == {
        "status": AUDIO_NOT_REQUESTED,
        "exposed": False,
        "required_for_reader_release": False,
    }
    assert manifest["commerce_release"]["status"] == "NOT_REQUESTED"
    assert validate_manifest(manifest) == []


def test_manifest_migration_is_deterministic_for_same_inputs():
    first = build_manifest(SHERLOCK, generated_at="2026-08-08T00:00:00Z")
    second = build_manifest(SHERLOCK, generated_at="2026-08-08T00:00:00Z")

    assert first == second
    assert first["manifest_sha256"] == canonical_sha256(first)


def test_reader_exposure_requires_explicit_publish_approval():
    candidate = build_manifest(SHERLOCK, generated_at="2026-08-08T00:00:00Z")
    approved = build_manifest(
        SHERLOCK,
        publish_approved=True,
        generated_at="2026-08-08T00:00:00Z",
    )

    assert manifest_reader_exposed(candidate) is False
    assert approved["reader_release"]["status"] == READER_APPROVED
    assert manifest_reader_exposed(approved) is True


def test_manifest_checksum_rejects_mutation():
    manifest = build_manifest(SHERLOCK, generated_at="2026-08-08T00:00:00Z")
    mutated = json.loads(json.dumps(manifest))
    mutated["content"]["chapter_count"] += 1

    assert "publication manifest checksum is invalid" in validate_manifest(mutated)


def test_migration_regenerates_legacy_checksum_bundle(tmp_path):
    artifact = tmp_path / "pilot-book"
    metadata = tmp_path / "import.json"
    metadata.write_text(
        json.dumps({
            "slug": "pilot-book",
            "title": "Pilot Book",
            "author": "Example Author",
            "language": "en",
            "rights_metadata": {
                "source_url": "https://example.test/source",
                "source_license": "Public domain",
            },
            "chapters": [{"title": "Chapter One", "content": "A complete first chapter."}],
        }),
        encoding="utf-8",
    )

    migrate_import_metadata(metadata, artifact)

    checksum = json.loads((artifact / "checksum_manifest.json").read_text(encoding="utf-8"))
    entries = {entry["file"]: entry["sha256"] for entry in checksum["files"]}
    public_bytes = (artifact / "public_book.json").read_bytes()
    chapter_bytes = (artifact / "chapters" / "chapter-001.json").read_bytes()
    assert entries["public_book.json"] == hashlib.sha256(public_bytes).hexdigest()
    assert entries["chapters/chapter-001.json"] == hashlib.sha256(chapter_bytes).hexdigest()
    assert "checksum_manifest.json" not in entries
    assert "publication_manifest.json" not in entries


def test_agentic_ai_reader_projection_is_public_without_audio():
    clear_controlled_artifact_caches()
    book = load_controlled_artifact_book("agentic-ai-with-python", include_content=True)

    assert book is not None
    assert can_expose_reader(book) is True
    assert len(book["chapters"]) == 14
    assert all(chapter.get("content") for chapter in book["chapters"])
    assert book.get("audio_enabled") is False
    assert book.get("audiobook_enabled") is False
