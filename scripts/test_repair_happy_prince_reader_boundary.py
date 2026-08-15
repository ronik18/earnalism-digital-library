from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_happy_prince_reader_boundary.py")
SPEC = importlib.util.spec_from_file_location("repair_happy_prince_reader_boundary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_repair_isolates_only_the_happy_prince() -> None:
    chapter = MODULE.read_json(MODULE.CONTENT_CHAPTER)
    repaired = MODULE.repaired_content(chapter["content"])
    assert repaired.endswith(MODULE.EXPECTED_ENDPOINT)
    assert "[Picture:" not in repaired
    assert MODULE.NEXT_STORY_TITLE not in repaired
    assert MODULE.sha256_text(repaired) == MODULE.EXPECTED_NEW_SANITIZED_SHA256


def test_repair_preserves_raw_source_and_invalidates_estimated_sync() -> None:
    before = MODULE.sha256_file(MODULE.RAW_SOURCE)
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    assert MODULE.sha256_file(MODULE.RAW_SOURCE) == before
    assert evidence["raw_source_immutable"] is True
    assert evidence["word_count"] == 3473
    assert evidence["legacy_highlight_sync_invalidated"] is True
    highlight = MODULE.json.loads(
        replacements[MODULE.PUBLICATION_DIR / "highlight_sync.json"].decode("utf-8")
    )
    assert highlight["chapters"] == []
    assert highlight["audio_enabled"] is False
