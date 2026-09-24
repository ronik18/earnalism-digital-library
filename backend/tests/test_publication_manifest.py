from __future__ import annotations

import json
import hashlib
from pathlib import Path

from backend.publication_manifest import (
    AUDIO_APPROVED,
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
    CONTROLLED_LIVE_BOOK_SLUGS,
    can_expose_reader,
    clear_controlled_artifact_caches,
    load_controlled_artifact_book,
)


ROOT = Path(__file__).resolve().parents[2]
SHERLOCK = ROOT / "data" / "controlled_publications" / "the-adventures-of-sherlock-holmes"
BISHOP = ROOT / "data" / "controlled_publications" / "the-bishop"
GIFT_OF_THE_MAGI = ROOT / "data" / "controlled_publications" / "the-gift-of-the-magi"
CANTERVILLE_GHOST = ROOT / "data" / "controlled_publications" / "the-canterville-ghost"


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


def test_gift_of_the_magi_is_india_ready_but_waits_for_commercial_cutover():
    manifest = build_manifest(GIFT_OF_THE_MAGI)
    source = json.loads((GIFT_OF_THE_MAGI / "source_evidence.json").read_text(encoding="utf-8"))
    backend_artifact = ROOT / "backend" / "data" / "controlled_publications" / "the-gift-of-the-magi"
    backend_manifest = build_manifest(backend_artifact)
    for artifact in (GIFT_OF_THE_MAGI, backend_artifact):
        checksum = json.loads((artifact / "checksum_manifest.json").read_text(encoding="utf-8"))
        source_digest = hashlib.sha256((artifact / "source_evidence.json").read_bytes()).hexdigest()
        indexed_source_digest = next(
            row["sha256"] for row in checksum["files"] if row["file"] == "source_evidence.json"
        )
        assert source_digest == indexed_source_digest

    assert manifest["rights"]["status"] == "APPROVED"
    assert manifest["rights"]["publication_region"] == "india"
    assert manifest["reader_release"]["status"] == "READY_FOR_APPROVAL"
    assert manifest["reader_release"]["exposed"] is False
    assert manifest["audio_release"]["status"] == AUDIO_NOT_REQUESTED
    assert manifest["audio_release"]["exposed"] is False
    assert manifest_reader_exposed(manifest) is False
    assert validate_manifest(manifest) == []
    assert validate_manifest(backend_manifest) == []
    assert backend_manifest["reader_release"]["exposed"] is False
    assert source["text_integrity_status"] == "TEXT_VERIFIED"
    assert source["canonical_chapter_text_sha256"] == "be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e"
    assert source["commercial_live_status"] == "WAITING_FOR_COMMERCIAL_CUTOVER"
    assert source["content_hash"] == "43f7c14de6be56f642476b78fd227fb0005d43909fc27e477646ec99b0900fcd"
    assert "the-gift-of-the-magi" not in CONTROLLED_LIVE_BOOK_SLUGS
    assert load_controlled_artifact_book(
        "the-gift-of-the-magi",
        include_content=False,
        artifact_dir=backend_artifact,
    ) is None


def test_canterville_ghost_is_india_ready_but_waits_for_commercial_cutover():
    manifest = build_manifest(CANTERVILLE_GHOST)
    backend_artifact = ROOT / "backend" / "data" / "controlled_publications" / "the-canterville-ghost"
    backend_manifest = build_manifest(backend_artifact)
    source = json.loads((CANTERVILLE_GHOST / "source_evidence.json").read_text(encoding="utf-8"))
    book = json.loads((CANTERVILLE_GHOST / "public_book.json").read_text(encoding="utf-8"))
    intake_metadata = json.loads(
        (ROOT / "content/books/the-canterville-ghost/book.json").read_text(encoding="utf-8")
    )
    generated_covers = json.loads(
        (ROOT / "internal/earnalism_intelligence/english_25_title_generated_cover_audit.json")
        .read_text(encoding="utf-8")
    )
    cover_record = next(row for row in generated_covers["rows"] if row["slug"] == "the-canterville-ghost")

    assert source["india_copyright_category"] == "ORDINARY_PUBLISHED_LITERARY_WORK_SECTION_22"
    assert source["underlying_work_status"] == "INDIA_TERM_EXPIRED"
    assert source["author_death_year"] == 1900
    assert source["original_publication_year"] == 1887
    assert source["source_url"] == "https://www.gutenberg.org/ebooks/14522"
    assert source["translation_status"] == "NOT_APPLICABLE_ORIGINAL_LANGUAGE_WORK"
    assert source["canonical_text_status"] == "TEXT_VERIFIED"
    assert source["canonical_content_sha256"] == book["content_hash"]
    assert source["source_comparison"]["result"] == "EXACT_MATCH"
    assert source["source_comparison"]["comparison_tokens"] == 11295
    assert (
        "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html"
        in source["copyright_evidence_links"]
    )
    assert "india-only" in intake_metadata["rightsTerritoryBasis"].lower()
    assert "no worldwide clearance is asserted" in intake_metadata["rightsTerritoryBasis"].lower()
    assert source["reader_chapter_boundary_repair"]["chapter_count"] == 7
    assert source["reader_chapter_boundary_repair"]["normalized_words_order_unchanged"] is True
    assert source["reader_chapter_boundary_repair"]["narrative_endpoint"] == "Virginia blushed."
    assert cover_record["art_source"] == "deterministic_vector_primitives_no_external_art"
    for path_key, hash_key in (("front_path", "front_sha256"), ("back_path", "back_sha256")):
        assert hashlib.sha256((ROOT / cover_record[path_key]).read_bytes()).hexdigest() == cover_record[hash_key]
    for artifact in (CANTERVILLE_GHOST, backend_artifact):
        checksum = json.loads((artifact / "checksum_manifest.json").read_text(encoding="utf-8"))
        for row in checksum["files"]:
            assert hashlib.sha256((artifact / row["file"]).read_bytes()).hexdigest() == row["sha256"]
    assert manifest["rights"]["status"] == "APPROVED"
    assert manifest["rights"]["publication_region"] == "in"
    assert manifest["reader_release"]["status"] == "READY_FOR_APPROVAL"
    assert manifest["reader_release"]["exposed"] is False
    assert manifest["audio_release"]["status"] == AUDIO_NOT_REQUESTED
    assert manifest["audio_release"]["exposed"] is False
    assert validate_manifest(manifest) == []
    assert validate_manifest(backend_manifest) == []
    assert "the-canterville-ghost" not in CONTROLLED_LIVE_BOOK_SLUGS
    assert load_controlled_artifact_book(
        "the-canterville-ghost", include_content=False, artifact_dir=backend_artifact
    ) is None


def test_checksum_bound_approved_audio_is_a_separate_exposed_lane():
    manifest = build_manifest(
        ROOT / "data" / "controlled_publications" / "the-selfish-giant",
        publish_approved=True,
        generated_at="2026-08-16T06:45:34Z",
    )

    assert manifest["reader_release"]["status"] == READER_APPROVED
    assert manifest["audio_release"] == {
        "status": AUDIO_APPROVED,
        "exposed": True,
        "required_for_reader_release": False,
        "qa_status": "QA_PASSED",
        "audio_sha256": "824944d0c068b4f4f45cb750e018918b2af55c5e043cd29417ce2a756e9a4c67",
        "candidate_fingerprint": "92a24c3442fe5ad637e72be523f52baded74d0390a256e3b5d5865bdb3f3d96e",
        "delivery_mode": "SERVER_OWNED_CONVEYOR",
        "public_endpoint": "/api/reader/book/the-selfish-giant/audiobook",
        "discovery_exposed": False,
        "blockers": [],
    }
    assert validate_manifest(manifest) == []


def test_server_owned_audio_manifest_fails_closed_for_cross_title_endpoint():
    manifest = build_manifest(
        ROOT / "data" / "controlled_publications" / "the-selfish-giant",
        publish_approved=True,
        generated_at="2026-08-16T06:45:34Z",
    )
    manifest["audio_release"]["public_endpoint"] = "/api/reader/book/a-white-heron/audiobook"
    manifest["manifest_sha256"] = canonical_sha256(manifest)

    assert "server-owned audio release requires its same-origin public endpoint" in validate_manifest(manifest)


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


def test_manifest_evaluates_translator_rights_from_source_evidence():
    manifest = build_manifest(BISHOP, generated_at="2026-08-16T00:00:00Z")

    assert manifest["rights"]["status"] == "APPROVED"
    assert not [
        blocker
        for blocker in manifest["reader_release"]["blockers"]
        if "translator" in blocker.lower()
    ]


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


def test_agentic_ai_reader_package_is_not_exposed_outside_the_controlled_release():
    clear_controlled_artifact_caches()
    book = load_controlled_artifact_book("agentic-ai-with-python", include_content=True)

    assert book is not None
    assert "agentic-ai-with-python" not in CONTROLLED_LIVE_BOOK_SLUGS
    assert can_expose_reader(book) is False
    assert len(book["chapters"]) == 14
    assert all(chapter.get("content") for chapter in book["chapters"])
    assert book.get("audio_enabled") is False
    assert book.get("audiobook_enabled") is False
