from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.audiobook_generation_sync_pipeline import (
    BLOCKED_GENERATE_INTERNAL,
    DRY_RUN_COMPLETE,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    evaluate_release_gates,
    model_candidate_status,
    run_pipeline,
    scan_public_audio_files,
)


@pytest.fixture(autouse=True)
def cleanup_internal_pytest_outputs():
    root = Path.cwd() / "internal" / "audiobook_lab"
    for path in root.glob("pytest-*"):
        if path.is_dir():
            shutil.rmtree(path)
    yield
    for path in root.glob("pytest-*"):
        if path.is_dir():
            shutil.rmtree(path)


def test_dry_run_creates_sync_manifest_but_no_public_audio(tmp_path: Path):
    output_dir = Path.cwd() / "internal" / "audiobook_lab" / "pytest-dracula" / "en" / "1"
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="kokoro",
        mode="dry-run",
        output_dir=output_dir,
        write_root_reports=False,
    )
    manifest = json.loads(result.sync_manifest_path.read_text(encoding="utf-8"))

    assert result.status == DRY_RUN_COMPLETE
    assert result.sync_manifest_path.exists()
    assert manifest["public"] is False
    assert manifest["items"]
    assert manifest["items"][0]["sync_level"] == "sentence"
    assert manifest["items"][0]["audio_hash"] == "sha256:placeholder-no-audio-generated"
    assert scan_public_audio_files() == []


def test_dry_run_outputs_only_json_or_markdown_artifacts():
    output_dir = Path.cwd() / "internal" / "audiobook_lab" / "pytest-artifacts" / "en" / "1"
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="kokoro",
        mode="dry-run",
        output_dir=output_dir,
        write_root_reports=False,
    )
    files = [path for path in result.output_dir.rglob("*") if path.is_file()]

    assert files
    assert {path.suffix for path in files} == {".json"}
    assert not any(path.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".aac"} for path in files)


def test_missing_model_license_blocks_generate_internal(tmp_path: Path):
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="kokoro",
        mode="generate-internal",
        output_dir=Path.cwd() / "internal" / "audiobook_lab" / "pytest-license" / "en" / "1",
        local_internal_generation_ok=True,
        write_root_reports=False,
    )
    codes = {blocker.code for blocker in result.blockers}

    assert result.status == BLOCKED_GENERATE_INTERNAL
    assert "MODEL_LICENSE_EVIDENCE_MISSING" in codes
    assert "MODEL_LICENSE_HOLD" in codes


def test_missing_derivative_rights_blocks_generate_internal(tmp_path: Path):
    evidence = tmp_path / "evidence.md"
    evidence.write_text("local model license evidence only", encoding="utf-8")
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="kokoro",
        mode="generate-internal",
        output_dir=Path.cwd() / "internal" / "audiobook_lab" / "pytest-derivative" / "en" / "1",
        local_internal_generation_ok=True,
        model_license_evidence=str(evidence),
        source_rights_evidence=str(evidence),
        voice_rights_evidence=str(evidence),
        human_qa_evidence=str(evidence),
        accessibility_qa_evidence=str(evidence),
        write_root_reports=False,
    )
    codes = {blocker.code for blocker in result.blockers}

    assert result.status == BLOCKED_GENERATE_INTERNAL
    assert "DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING" in codes


def test_generated_outputs_stay_under_internal_lab():
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="melotts",
        mode="dry-run",
        output_dir=Path.cwd() / "internal" / "audiobook_lab" / "pytest-internal" / "en" / "1",
        write_root_reports=False,
    )

    assert "internal/audiobook_lab" in result.sync_manifest_path.as_posix()
    assert "frontend/public" not in result.sync_manifest_path.as_posix()
    assert "frontend/build" not in result.sync_manifest_path.as_posix()


def test_output_dir_outside_internal_lab_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="output-dir must stay under internal/audiobook_lab"):
        run_pipeline(
            book_slug="dracula",
            chapter="1",
            language="en",
            model_candidate="kokoro",
            mode="dry-run",
            output_dir=tmp_path / "outside",
            write_root_reports=False,
        )


def test_sync_manifest_cannot_be_marked_public():
    blockers = evaluate_release_gates(
        mode="dry-run",
        model_info=model_candidate_status("kokoro", "en"),
        sync_items=[{"public": True}],
        local_internal_generation_ok=False,
        model_license_evidence=None,
        source_rights_evidence=None,
        derivative_rights_evidence=None,
        voice_rights_evidence=None,
        human_qa_evidence=None,
        accessibility_qa_evidence=None,
    )
    codes = {blocker.code for blocker in blockers}

    assert "SYNC_MANIFEST_PUBLIC_WITHOUT_APPROVAL" in codes


def test_public_audio_remains_blocked():
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="indic-parler-tts",
        mode="dry-run",
        output_dir=Path.cwd() / "internal" / "audiobook_lab" / "pytest-blocked" / "en" / "1",
        write_root_reports=False,
    )
    gate = json.loads(result.release_gate_report_path.read_text(encoding="utf-8"))

    assert gate["public_audio_release"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result_json_status(result) == PUBLIC_AUDIO_RELEASE_BLOCKED


def result_json_status(result):
    payload = json.loads(result.qa_packet_path.read_text(encoding="utf-8"))
    return payload["public_audio_release_status"]


def test_no_listen_now_cta_or_audioobject_metadata_is_introduced():
    result = run_pipeline(
        book_slug="dracula",
        chapter="1",
        language="en",
        model_candidate="piper",
        mode="dry-run",
        output_dir=Path.cwd() / "internal" / "audiobook_lab" / "pytest-public-surface" / "en" / "1",
        write_root_reports=False,
    )
    combined = "\n".join(
        [
            result.sync_manifest_path.read_text(encoding="utf-8"),
            result.qa_packet_path.read_text(encoding="utf-8"),
            result.model_decision_path.read_text(encoding="utf-8"),
        ]
    )

    assert "AudioObject" not in combined
    assert "Listen Now" not in combined
    assert scan_public_audio_files() == []
