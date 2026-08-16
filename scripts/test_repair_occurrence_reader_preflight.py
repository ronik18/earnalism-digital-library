from __future__ import annotations

import importlib.util
import re
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_occurrence_reader_preflight.py")
SPEC = importlib.util.spec_from_file_location("repair_occurrence_reader_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_repair_removes_banner_and_restores_semantic_paragraphs() -> None:
    chapter = MODULE.read_json(MODULE.CONTENT_CHAPTER)
    repaired = MODULE.repaired_content(chapter["content"])
    assert MODULE.PUBLISHER_BANNER not in repaired
    assert repaired.split("\n\n", 1)[0] == "I"
    assert len(re.split(r"\n\s*\n", repaired)) == MODULE.EXPECTED_BLOCK_COUNT
    assert repaired.endswith(MODULE.EXPECTED_ENDPOINT)
    assert MODULE.sha256_text(repaired) == MODULE.EXPECTED_NEW_SANITIZED_SHA256
    raw_source = MODULE.RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    assert MODULE.normalized(repaired) == MODULE.normalized(
        MODULE.remove_publisher_banner(raw_source)
    )


def test_repair_preserves_raw_source_and_invalidates_estimated_sync() -> None:
    before = MODULE.sha256_file(MODULE.RAW_SOURCE)
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    assert MODULE.sha256_file(MODULE.RAW_SOURCE) == before
    assert evidence["raw_source_immutable"] is True
    assert evidence["normalized_narrative_text_unchanged"] is True
    assert evidence["semantic_blocks"] == 40
    assert evidence["word_count"] == 3764
    assert evidence["legacy_highlight_sync_invalidated"] is True
    highlight = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "highlight_sync.json"].decode("utf-8")
    )
    assert highlight["chapters"] == []
    assert highlight["audio_enabled"] is False


def test_repair_packages_identical_railway_mirror() -> None:
    replacements, _ = MODULE.build_replacements("2026-08-16T00:00:00Z")
    for relative in (
        "approval_evidence.json",
        "chapters/chapter-001.json",
        "highlight_sync.json",
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "checksum_manifest.json",
    ):
        assert replacements[MODULE.PUBLICATION_DIR / relative] == replacements[MODULE.BACKEND_PUBLICATION_DIR / relative]


def test_repair_supersedes_historical_reader_approval() -> None:
    replacements, _ = MODULE.build_replacements("2026-08-16T00:00:00Z")
    public = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "public_book.json"].decode("utf-8")
    )
    source = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "source_evidence.json"].decode("utf-8")
    )
    approval = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "approval_evidence.json"].decode("utf-8")
    )
    assert source["qa_status"] == "READY_FOR_APPROVAL"
    assert public["approved_to_publish"] is False
    assert public["allowPublicReading"] is False
    assert approval["historical_approval_superseded"] is True
    assert approval["reader_public_release"] == "READER_APPROVAL_REQUIRED"
