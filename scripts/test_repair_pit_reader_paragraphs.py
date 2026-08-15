from __future__ import annotations

import importlib.util
import re
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_pit_reader_paragraphs.py")
SPEC = importlib.util.spec_from_file_location("repair_pit_reader_paragraphs", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_reflow_preserves_words_order_epigraph_and_ending() -> None:
    chapter = MODULE.read_json(MODULE.CONTENT_CHAPTER)
    repaired = MODULE.repaired_content(chapter["content"])
    assert MODULE.normalized(repaired) == MODULE.normalized(chapter["content"])
    assert len(re.split(r"\n\s*\n", repaired)) == MODULE.EXPECTED_BLOCK_COUNT
    assert repaired.split("\n\n", 1)[0].count("\n") == 3
    assert repaired.endswith(MODULE.EXPECTED_ENDPOINT)
    assert MODULE.sha256_text(repaired) == MODULE.EXPECTED_NEW_SANITIZED_SHA256


def test_repair_preserves_raw_source_and_invalidates_estimated_sync() -> None:
    before = MODULE.sha256_file(MODULE.RAW_SOURCE)
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    assert MODULE.sha256_file(MODULE.RAW_SOURCE) == before
    assert evidence["normalized_text_unchanged"] is True
    assert evidence["semantic_blocks"] == 40
    assert evidence["word_count"] == 6149
    assert evidence["root_backend_byte_parity"] is True
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
