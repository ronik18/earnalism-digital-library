from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.audiobook_chapter_pipeline import (
    BLOCKED_REAL_GENERATION,
    DRY_RUN_READY,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    public_audio_files,
    run_chapter_pipeline,
)
from scripts.validate_elevenlabs_narration_text import validate_text


@pytest.fixture(autouse=True)
def cleanup_pipeline_test_dirs():
    root = Path.cwd() / "internal" / "audiobook_lab"
    for slug in ("pytest-audiobook-pipeline", "pytest-generate-gates"):
        target = root / slug
        if target.exists():
            shutil.rmtree(target)
    yield
    for slug in ("pytest-audiobook-pipeline", "pytest-generate-gates"):
        target = root / slug
        if target.exists():
            shutil.rmtree(target)


def test_dry_run_generates_clean_internal_artifacts_without_audio():
    result = run_chapter_pipeline(
        book_slug="pytest-audiobook-pipeline",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="dry-run",
        write_root_reports=False,
    )

    assert result.status == DRY_RUN_READY
    assert result.generation["provider_api_called"] is False
    assert result.generation["audio_generated_by_repo"] is False
    assert result.public_release["public_audio_release"] == PUBLIC_AUDIO_RELEASE_BLOCKED

    output_dir = result.output_dir
    assert (output_dir / "full_chapter_sync_source_with_ids.txt").exists()
    assert (output_dir / "full_chapter_narration_text.txt").exists()
    assert (output_dir / "sentence_map.json").exists()
    assert (output_dir / "chunk_manifest.json").exists()
    assert not list(output_dir.rglob("*.mp3"))


def test_dracula_sentence_map_and_chunks_preserve_clean_ids():
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

    assert list(sentence_map) == [f"s{index:03d}" for index in range(1, 221)]
    assert sentence_map["s001"]["narration_text"] == "Chapter One. Jonathan Harker's Journal."
    assert sentence_map["s084"]["sync_action"] == "pause_only"
    assert chunk_manifest["chunk_count"] == 27
    assert chunk_manifest["public_audio_release"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert chunk_manifest["listen_now_cta_allowed"] is False
    assert chunk_manifest["audio_object_metadata_allowed"] is False
    assert chunk_manifest["full_book_generation_allowed"] is False
    for chunk in chunk_manifest["chunks"]:
        assert validate_text(chunk["chunk_id"], chunk["narration_text"]) == []
        assert chunk["generation_status"] == "NOT_GENERATED"


def test_generate_internal_refuses_without_execute(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    result = run_chapter_pipeline(
        book_slug="pytest-generate-gates",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="generate-internal",
        execute=False,
        max_cost_inr=500,
        max_chunks=3,
        write_root_reports=False,
    )

    assert result.status == BLOCKED_REAL_GENERATION
    assert any("--execute" in blocker for blocker in result.generation["blockers"])


def test_generate_internal_refuses_without_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    result = run_chapter_pipeline(
        book_slug="pytest-generate-gates",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="generate-internal",
        execute=True,
        max_cost_inr=500,
        max_chunks=3,
        write_root_reports=False,
    )

    assert result.status == BLOCKED_REAL_GENERATION
    assert any("ELEVENLABS_API_KEY" in blocker for blocker in result.generation["blockers"])


def test_generate_internal_refuses_when_provider_not_eligible(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy-env-value")

    result = run_chapter_pipeline(
        book_slug="pytest-generate-gates",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="generate-internal",
        execute=True,
        max_cost_inr=500,
        max_chunks=3,
        write_root_reports=False,
    )

    assert result.status == BLOCKED_REAL_GENERATION
    assert result.generation["provider_api_called"] is False
    assert any("ELIGIBLE_INTERNAL_EVAL_ONLY" in blocker for blocker in result.generation["blockers"])


def test_generate_internal_refuses_without_budget_caps(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy-env-value")

    result = run_chapter_pipeline(
        book_slug="pytest-generate-gates",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="generate-internal",
        execute=True,
        write_root_reports=False,
    )

    assert result.status == BLOCKED_REAL_GENERATION
    assert any("budget cap" in blocker for blocker in result.generation["blockers"])
    assert any("max chunks" in blocker.lower() for blocker in result.generation["blockers"])


def test_public_audio_remains_blocked_and_no_public_audio_created():
    result = run_chapter_pipeline(
        book_slug="pytest-audiobook-pipeline",
        language="en",
        chapter=1,
        provider="elevenlabs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        voice_name="Rachel",
        mode="dry-run",
        write_root_reports=False,
    )

    combined_reports = "\n".join(
        path.read_text(encoding="utf-8")
        for path in result.output_dir.glob("AUDIOBOOK_*.md")
    )
    assert "Listen Now" not in combined_reports
    assert "AudioObject" not in combined_reports
    assert public_audio_files() == []
