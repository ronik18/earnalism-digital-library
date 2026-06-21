from __future__ import annotations

import json
from pathlib import Path

from scripts.english_audiobook_chunker import (
    DRACULA_DIR,
    build_representative_chunks,
    html_to_plain_text,
    load_chapter,
)
from scripts.english_text_normalizer import normalize_english_text


def test_html_to_plain_text_preserves_paragraph_boundaries():
    text = html_to_plain_text("<p>First.</p><p>Second.<br>Third.</p>")

    assert "First." in text
    assert "Second.\nThird." in text
    assert "<p>" not in text


def test_dracula_chunks_include_diary_heading_without_splitting_entry():
    chunks, _notes = build_representative_chunks(
        chapter_paths=[DRACULA_DIR / "chapters" / "chapter-001.json"],
        target_count=12,
    )
    first = chunks[0]

    assert first.segment_type == "diary_heading_with_entry"
    assert first.emotion_label == "intimate_diary"
    assert "_3 May. Bistritz." in first.original_text
    assert "Left Munich" in first.original_text


def test_dracula_chunk_ids_are_deterministic():
    paths = [DRACULA_DIR / "chapters" / "chapter-001.json"]
    first_run, _notes = build_representative_chunks(chapter_paths=paths, target_count=12)
    second_run, _notes = build_representative_chunks(chapter_paths=paths, target_count=12)

    assert [chunk.chunk_id for chunk in first_run] == [chunk.chunk_id for chunk in second_run]
    assert len({chunk.chunk_id for chunk in first_run}) == len(first_run)


def test_normalizer_expands_abbreviations_and_preserves_side_by_side():
    result = normalize_english_text("Mr. Harker arrived at 8:35 P. M.--late.")

    assert result.original_text.startswith("Mr. Harker")
    assert "Mister Harker" in result.normalized_text
    assert "P M" in result.normalized_text
    assert " - " in result.normalized_text
    assert result.replacements["Mr."] == 1


def test_committed_dracula_chunks_are_internal_review_only():
    payload = json.loads(Path("data/audiobook_generation/dracula/chunks.json").read_text(encoding="utf-8"))

    assert payload["book_slug"] == "dracula"
    assert payload["audio_enabled"] is False
    assert 10 <= payload["chunk_count"] <= 14
    assert all(chunk["internal_review_only"] is True for chunk in payload["chunks"])
    assert any(chunk["emotion_label"] == "quiet_fear" for chunk in payload["chunks"])


def test_english_chunk_coverage_report_accounts_for_all_chapters():
    report = Path("ENGLISH_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md").read_text(encoding="utf-8")

    assert "Total Dracula chapters: 27" in report
    assert "Selected chunk count: 12" in report
    assert "chapter-001" in report
    assert "Skipped chapter count" in report
    assert "9.9+ audiobook score still requires generated internal samples" in report


def test_voice_profile_caps_exaggeration_and_blocks_real_person_imitation():
    payload = json.loads(
        Path("data/audiobook_voice_profiles/english-gothic-premium-v1.json").read_text(encoding="utf-8")
    )

    assert payload["tone"]["exaggeration_cap"] <= 0.5
    assert payload["real_person_or_celebrity_imitation_allowed"] is False
    assert payload["audiobook_public_enabled"] is False


def test_local_generation_approval_example_is_default_denied():
    payload = json.loads(
        Path("data/audiobook_governance/dracula.local_generation_approval.example.json").read_text(encoding="utf-8")
    )

    assert payload["approved"] is False
    assert payload["scope"] == "LOCAL_INTERNAL_REVIEW_ONLY"
    assert payload["allowed_models"] == []
    assert payload["max_chunks"] == 0
    assert payload["no_public_release"] is True
    assert payload["no_upload"] is True
    assert payload["owner_signature_required"] is True


def test_chapter_source_is_controlled_dracula_artifact():
    chapter = load_chapter(DRACULA_DIR / "chapters" / "chapter-001.json")

    assert "JONATHAN HARKER" in chapter["title"]
    assert "JOURNAL" in chapter["title"]
    assert "Bistritz" in chapter["text"]
