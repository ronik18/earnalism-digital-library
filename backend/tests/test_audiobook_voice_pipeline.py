from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.audiobook_voice_pipeline import (
    SUPPORTED_MODES,
    SUPPORTED_PROVIDERS,
    AudiobookPipelineInput,
    AudioQAMetrics,
    detect_language,
    evaluate_audio_qa,
    plan_audiobook_pipeline,
    plan_tts_provider,
    process_narration_script,
)
from scripts.audiobook_voice_pipeline import SAMPLE_TEXT, write_reports


def sample_input(**overrides):
    payload = {
        "book_slug": "alice-in-wonderland",
        "title": "Alice's Adventures in Wonderland",
        "source_text": SAMPLE_TEXT,
        "language": "en",
        "generation_mode": "preview_90s",
        "provider": "manual_audio_upload",
        "dry_run": True,
        "linked_approved_book": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "pronunciation_dictionary": {"Earnalism": "urn-uh-lizm"},
    }
    payload.update(overrides)
    return AudiobookPipelineInput(**payload)


def test_language_detection_supports_bengali_hindi_and_english():
    assert detect_language("আনন্দমঠ একটি বাংলা উপন্যাস।") == "bn"
    assert detect_language("यह एक हिंदी वाक्य है।") == "hi"
    assert detect_language("This is an English sentence.") == "en"


def test_punctuation_aware_chunking_detects_chapters_dialogue_and_pauses():
    result = process_narration_script(SAMPLE_TEXT, language="en", mode="chapter_audio")

    assert result.language == "en"
    assert result.chapter_count == 2
    assert any(chunk.segment_type == "chapter_heading" for chunk in result.chunks)
    assert any(chunk.segment_type == "dialogue" for chunk in result.chunks)
    assert sum(len(chunk.punctuation_pauses_ms) for chunk in result.chunks) > 0


def test_poetry_line_break_handling_marks_short_multiline_stanzas():
    text = "Chapter 1\n\nLight falls\nSoftly calls\nLearning rises"
    result = process_narration_script(text, language="en", mode="chapter_audio")

    assert any(chunk.segment_type == "poetry" for chunk in result.chunks)
    assert result.poetry_chunk_count == 1


def test_pronunciation_dictionary_is_applied():
    result = process_narration_script(
        "Chapter 1\n\nEarnalism by Reo Enterprise.",
        language="en",
        pronunciation_dictionary={"Earnalism": "urn-uh-lizm", "Reo Enterprise": "Ray-oh Enterprise"},
    )
    combined = " ".join(chunk.text for chunk in result.chunks)

    assert "urn-uh-lizm" in combined
    assert "Ray-oh Enterprise" in combined
    assert result.pronunciation_replacement_count == 2


def test_generation_modes_limit_chunks_deterministically():
    text = "\n\n".join(f"Paragraph {idx}. This sentence should become a chunk." for idx in range(20))
    preview = process_narration_script(text, language="en", mode="preview_30s", max_chunk_chars=80)
    full = process_narration_script(text, language="en", mode="full_audiobook_playlist", max_chunk_chars=80)

    assert len(preview.chunks) == 1
    assert len(full.chunks) > len(preview.chunks)
    assert set(SUPPORTED_MODES) == {"preview_30s", "preview_90s", "preview_3m", "chapter_audio", "full_audiobook_playlist"}


def test_provider_abstraction_has_no_vendor_lock_in(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AI4BHARAT_TTS_ENDPOINT", raising=False)
    monkeypatch.delenv("INDIC_TTS_COMMAND", raising=False)
    monkeypatch.delenv("PIPER_MODEL_PATH", raising=False)
    monkeypatch.delenv("PIPER_TTS_COMMAND", raising=False)

    plans = [plan_tts_provider(provider, "bn") for provider in SUPPORTED_PROVIDERS]

    assert {plan.provider for plan in plans} == set(SUPPORTED_PROVIDERS)
    assert next(plan for plan in plans if plan.provider == "openai_tts").dry_run_only is True
    assert next(plan for plan in plans if plan.provider == "ai4bharat_indic_tts").dry_run_only is True
    assert next(plan for plan in plans if plan.provider == "piper_local_tts").dry_run_only is True
    assert next(plan for plan in plans if plan.provider == "manual_audio_upload").dry_run_only is False


def test_openai_provider_detects_configured_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    plan = plan_tts_provider("openai_tts", "en")

    assert plan.credentials_configured is True
    assert plan.dry_run_only is False
    assert plan.supports_ssml is False


def test_pipeline_dry_run_never_publishes_audio():
    result = plan_audiobook_pipeline(sample_input())

    assert result.generation_status == "DRY_RUN_READY"
    assert result.publish_gate_status == "DRY_RUN_ONLY"
    assert result.dry_run is True
    assert all(asset["publishable"] is False for asset in result.planned_audio_assets)


def test_non_dry_run_requires_linked_approved_book():
    result = plan_audiobook_pipeline(sample_input(dry_run=False, linked_approved_book=False))

    assert result.publish_gate_status == "BLOCKED_BOOK_APPROVAL"
    assert "linked approved book" in result.blocking_reason


def test_non_dry_run_requires_approved_rights():
    result = plan_audiobook_pipeline(sample_input(dry_run=False, rights_tier="C"))

    assert result.publish_gate_status == "BLOCKED_RIGHTS"


def test_non_dry_run_requires_qa_pass():
    result = plan_audiobook_pipeline(
        sample_input(
            dry_run=False,
            qa_metrics=AudioQAMetrics(word_error_rate=0.2, file_size_bytes=1000),
        )
    )

    assert result.publish_gate_status == "BLOCKED_QA"
    assert result.qa.qa_status == "FAIL"


def test_non_dry_run_can_pass_only_with_manual_provider_and_qa_pass():
    result = plan_audiobook_pipeline(
        sample_input(
            dry_run=False,
            qa_metrics=AudioQAMetrics(
                stt_transcript_comparison="PASS",
                word_error_rate=0.01,
                file_size_bytes=2_000_000,
            ),
        )
    )

    assert result.publish_gate_status == "PASS"
    assert result.generation_status == "READY_FOR_REVIEW"


def test_audio_qa_flags_required_failures():
    qa = evaluate_audio_qa(
        AudioQAMetrics(
            word_error_rate=0.12,
            missing_paragraph_count=1,
            repeated_line_count=1,
            clipping_detected=True,
            long_silence_detected=True,
            file_size_bytes=0,
        ),
        dry_run=False,
    )

    assert qa.qa_status == "FAIL"
    assert len(qa.issues) >= 5


def test_mastering_plan_contains_ffmpeg_metadata_but_does_not_execute():
    result = plan_audiobook_pipeline(sample_input(generation_mode="chapter_audio"))

    assert result.mastering_plan.executed is False
    assert any("ffmpeg -i" in command for command in result.mastering_plan.ffmpeg_commands)
    assert result.mastering_plan.output_formats == ["mp3", "aac", "ogg"]
    assert result.mastering_plan.waveform_preview.endswith(".waveform.json")


def test_reports_are_preview_only_by_default_and_include_text_when_requested(tmp_path: Path):
    result = plan_audiobook_pipeline(sample_input())
    json_path, _csv_path, md_path = write_reports(result, tmp_path, text_preview_chars=18)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    first_chunk = next(chunk for chunk in result.narration_script.chunks if len(chunk.text) > 18)
    first_chunk_index = first_chunk.index - 1

    assert "text" not in payload["narration_script"]["chunks"][first_chunk_index]
    assert payload["narration_script"]["chunks"][first_chunk_index]["text_preview"] == first_chunk.text[:18]
    assert first_chunk.text not in markdown

    json_path, _csv_path, md_path = write_reports(result, tmp_path / "full", include_text=True)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    assert payload["narration_script"]["chunks"][first_chunk_index]["text"] == first_chunk.text
    assert first_chunk.text in markdown


def test_cli_sample_writes_reports(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audiobook_voice_pipeline.py",
            "--sample",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Audiobook voice dry-run complete" in completed.stdout
    assert (tmp_path / "audiobook_voice_report.json").exists()
    assert (tmp_path / "audiobook_voice_report.csv").exists()
    assert (tmp_path / "audiobook_voice_report.md").exists()


def test_cli_rejects_publish_options(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audiobook_voice_pipeline.py",
            "--sample",
            "--publish",
            "--output-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "dry-run only" in completed.stderr
