from __future__ import annotations

import json
from pathlib import Path

from scripts.audiobook_chapter_pipeline import (
    NARRATION_MODE_PREMIUM,
    build_sentence_map,
    clean_narration_sentence,
    run_chapter_pipeline,
)
from scripts.validate_elevenlabs_narration_text import validate_text


def test_kept_in_shorthand_is_metadata_only_in_premium_mode():
    narration_text, metadata = clean_narration_sentence("(_Kept in shorthand._)", NARRATION_MODE_PREMIUM)

    assert narration_text == ""
    assert metadata["narration_decision"] == "metadata_only"
    assert metadata["reason"] == "metadata_only_paratext_shorthand_note"


def test_chapter_heading_and_date_location_are_transformed_for_audio():
    heading, heading_metadata = clean_narration_sentence("CHAPTER I. JONATHAN HARKER’S JOURNAL")
    date_line, date_metadata = clean_narration_sentence("_3 May.")

    assert heading == "Chapter One. Jonathan Harker's Journal."
    assert heading_metadata["narration_decision"] == "transform"
    assert date_line == "May the third. Bistritz."
    assert date_metadata["narration_decision"] == "transform"


def test_sentence_map_preserves_original_source_text_and_records_decisions():
    items = [
        {"sentence_id": "s001", "source_text": "CHAPTER I. JONATHAN HARKER’S JOURNAL"},
        {"sentence_id": "s002", "source_text": "(_Kept in shorthand._)"},
        {"sentence_id": "s003", "source_text": "_3 May."},
        {
            "sentence_id": "s004",
            "source_text": "Bistritz._--Left Munich at 8:35 P. M., on 1st May, but train was an hour late.",
        },
    ]

    sentence_map = build_sentence_map(items)

    assert sentence_map["s002"]["source_text"] == "(_Kept in shorthand._)"
    assert sentence_map["s002"]["narration_text"] == ""
    assert sentence_map["s002"]["narration_decision"] == "metadata_only"
    assert sentence_map["s003"]["source_text"] == "_3 May."
    assert sentence_map["s003"]["narration_text"] == "May the third. Bistritz."
    assert sentence_map["s004"]["source_text"].startswith("Bistritz._--Left Munich")
    assert sentence_map["s004"]["narration_text"].startswith("Left Munich at 8:35 P.M.")
    assert "on 1st May" in sentence_map["s004"]["source_text"]
    assert "but train was an hour late" in sentence_map["s004"]["source_text"]
    assert "on the first of May" in sentence_map["s004"]["narration_text"]
    assert "but the train was an hour late" in sentence_map["s004"]["narration_text"]


def test_premium_dracula_c001_contains_only_clean_narration_text():
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

    sentence_map = json.loads((result.output_dir / "sentence_map.json").read_text(encoding="utf-8"))
    chunk_manifest = json.loads((result.output_dir / "chunk_manifest.json").read_text(encoding="utf-8"))
    c001 = chunk_manifest["chunks"][0]

    assert sentence_map["s001"]["source_text"] == "CHAPTER I. JONATHAN HARKER’S JOURNAL"
    assert sentence_map["s002"]["source_text"] == "(_Kept in shorthand._)"
    assert sentence_map["s002"]["narration_decision"] == "metadata_only"
    assert sentence_map["s002"]["narration_text"] == ""
    assert sentence_map["s084"]["narration_decision"] == "silence_pause"
    assert "Kept in shorthand." not in c001["narration_text"]
    assert "on 1st May" in sentence_map["s004"]["source_text"]
    assert "but train was an hour late" in sentence_map["s004"]["source_text"]
    assert "on the first of May" in sentence_map["s004"]["narration_text"]
    assert "but the train was an hour late" in sentence_map["s004"]["narration_text"]
    assert "on 1st May" not in c001["narration_text"]
    assert "but train was an hour late" not in c001["narration_text"]
    assert c001["narration_text"].startswith(
        "Chapter One. Jonathan Harker's Journal.\n"
        "May the third. Bistritz.\n"
        "Left Munich at 8:35 P.M., on the first of May"
    )
    assert validate_text("c001", c001["narration_text"]) == []


def test_no_story_content_is_silently_lost_except_approved_paratext():
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

    sentence_map = json.loads((result.output_dir / "sentence_map.json").read_text(encoding="utf-8"))
    metadata_only = [
        (sentence_id, entry.get("reason"))
        for sentence_id, entry in sentence_map.items()
        if entry.get("narration_decision") == "metadata_only"
    ]
    empty_story_entries = [
        sentence_id
        for sentence_id, entry in sentence_map.items()
        if not entry.get("narration_text")
        and entry.get("narration_decision") not in {"metadata_only", "silence_pause"}
    ]

    assert ("s002", "metadata_only_paratext_shorthand_note") in metadata_only
    assert empty_story_entries == []
    assert all(
        entry.get("narration_text") or entry.get("narration_decision") in {"metadata_only", "silence_pause"}
        for entry in sentence_map.values()
    )
