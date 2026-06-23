from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_elevenlabs_narration_text import (
    NarrationValidationError,
    public_audio_files,
    validate_sample_dir,
    validate_text,
)
from scripts.audiobook_chapter_pipeline import run_chapter_pipeline


FULL_CHAPTER_DIR = (
    Path.cwd() / "internal" / "audiobook_lab" / "dracula" / "en" / "chapter-1-elevenlabs-full"
)


def assert_text_fails(text: str, expected: str) -> None:
    failures = validate_text("dirty fixture", text)
    assert any(expected in failure for failure in failures), failures


def test_dirty_text_with_sentence_id_fails():
    assert_text_fails("[s001] Chapter One. Jonathan Harker's Journal.", "sentence id marker")


def test_dirty_text_with_comment_line_fails():
    assert_text_fails("# Internal source note\nChapter One.", "comment line")


def test_dirty_text_with_markdown_or_internal_notes_fails():
    failures = validate_text(
        "dirty fixture",
        "_Kept in shorthand._\nInternal-only note.\nDo not narrate this marker.",
    )

    assert any("raw underscore or markdown italic marker" in failure for failure in failures)
    assert any("internal instruction" in failure for failure in failures)


def test_clean_narration_text_passes():
    failures = validate_text(
        "clean fixture",
        "Chapter One. Jonathan Harker's Journal.\nKept in shorthand.\nMay the third. Bistritz.",
    )

    assert failures == []


def test_sentence_map_preserves_all_220_sentence_ids():
    sentence_map = json.loads((FULL_CHAPTER_DIR / "sentence_map.json").read_text(encoding="utf-8"))
    expected_ids = [f"s{index:03d}" for index in range(1, 221)]

    assert list(sentence_map) == expected_ids
    assert sentence_map["s001"]["source_text"] == "CHAPTER I. JONATHAN HARKER'S JOURNAL".replace(
        "'", "\u2019"
    )
    assert sentence_map["s001"]["narration_text"] == "Chapter One. Jonathan Harker's Journal."
    assert sentence_map["s002"]["narration_text"] == "Kept in shorthand."
    assert sentence_map["s003"]["narration_text"] == "May the third."
    assert sentence_map["s004"]["narration_text"].startswith("Bistritz. Left Munich")

    pause_entries = [
        (sentence_id, entry)
        for sentence_id, entry in sentence_map.items()
        if entry.get("sync_action") == "pause_only"
    ]
    assert [(sentence_id, entry["silence_ms"]) for sentence_id, entry in pause_entries] == [("s084", 750)]

    for sentence_id, entry in sentence_map.items():
        if entry.get("sync_action") == "pause_only":
            assert entry["narration_text"] == ""
            continue
        assert validate_text(f"sentence_map:{sentence_id}", entry["narration_text"]) == []


def test_chunk_manifest_references_clean_text_only():
    summary = validate_sample_dir(FULL_CHAPTER_DIR)
    manifest = json.loads((FULL_CHAPTER_DIR / "chunk_manifest.json").read_text(encoding="utf-8"))

    assert summary["sentence_count"] == 220
    assert summary["chunk_count"] == 27
    assert summary["pause_only_count"] == 1
    assert manifest["narration_text_file"] == "full_chapter_narration_text.txt"
    assert manifest["source_sync_file"] == "full_chapter_sync_source_with_ids.txt"
    assert manifest["generation_status"] == "NOT_GENERATED"
    assert manifest["non_narrated_markers"] == [
        {
            "sentence_id": "s084",
            "chunk_id": "c010",
            "marker_type": "section_break",
            "silence_ms": 750,
            "placement": "between s083 and s085",
        }
    ]

    assert len(manifest["chunks"]) == 27
    for chunk in manifest["chunks"]:
        assert chunk["generation_status"] == "NOT_GENERATED"
        assert chunk["sentence_ids"]
        assert chunk["narration_text"]
        assert validate_text(f"chunk:{chunk['chunk_id']}", chunk["narration_text"]) == []
        if chunk["chunk_id"] == "c010":
            assert chunk["silence_markers"][0]["sentence_id"] == "s084"
            assert chunk["silence_markers"][0]["silence_ms"] == 750


def test_validator_supports_generic_chapter_pipeline_directory():
    result = run_chapter_pipeline(
        book_slug="dracula",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="dry-run",
        write_root_reports=False,
    )

    summary = validate_sample_dir(result.output_dir)

    assert summary["narration_file"] == "internal/audiobook_lab/dracula/en/chapter-1/full_chapter_narration_text.txt"
    assert summary["sentence_count"] == 220
    assert summary["chunk_count"] == 27
    assert summary["pause_only_count"] == 1


def test_validation_raises_for_dirty_sample_dir(tmp_path: Path):
    sample_dir = tmp_path / "dirty"
    sample_dir.mkdir()
    (sample_dir / "full_chapter_narration_text.txt").write_text(
        "[s001] Dirty narration text.",
        encoding="utf-8",
    )
    (sample_dir / "sentence_map.json").write_text(
        json.dumps({"s001": {"source_text": "[s001] Dirty", "narration_text": "[s001] Dirty"}}),
        encoding="utf-8",
    )
    (sample_dir / "chunk_manifest.json").write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c001",
                        "sentence_ids": ["s001"],
                        "narration_text": "[s001] Dirty narration text.",
                        "text_hash": "wrong",
                        "estimated_duration_seconds": 10,
                        "generation_status": "NOT_GENERATED",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(NarrationValidationError, match="sentence id marker"):
        validate_sample_dir(sample_dir)


def test_no_public_audio_is_created():
    assert public_audio_files() == []
