from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_horseman_reader_boundary.py")
SPEC = importlib.util.spec_from_file_location("repair_horseman_reader_boundary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_repaired_content_stops_at_narrative_endpoint() -> None:
    chapter = MODULE.read_json(MODULE.CONTENT_CHAPTER)
    repaired = MODULE.repaired_content(chapter["content"])
    assert repaired.endswith(MODULE.EXPECTED_ENDPOINT)
    assert "Here ends No. Four of the Western Classics" not in repaired
    assert MODULE.sha256_text(repaired) == MODULE.EXPECTED_NEW_SANITIZED_SHA256


def test_repair_preserves_raw_source_and_hides_audio() -> None:
    before = MODULE.sha256_file(MODULE.RAW_SOURCE)
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    after = MODULE.sha256_file(MODULE.RAW_SOURCE)
    assert before == after
    assert evidence["raw_source_immutable"] is True
    assert evidence["legacy_highlight_sync_invalidated"] is True

    public = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "public_book.json"].decode("utf-8")
    )
    reader = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "reader_manifest.json"].decode("utf-8")
    )
    highlight = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "highlight_sync.json"].decode("utf-8")
    )
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert reader["audio_enabled"] is False
    assert reader["audiobook_enabled"] is False
    assert highlight["chapters"] == []
    assert highlight["status"] == "INVALIDATED_SOURCE_BOUNDARY_CHANGED"
