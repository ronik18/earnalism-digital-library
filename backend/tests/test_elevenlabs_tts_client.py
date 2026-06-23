from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.elevenlabs_tts_client import (
    ElevenLabsSafetyError,
    ElevenLabsSettings,
    build_tts_request_body,
    dry_run_generation_record,
    ensure_internal_output_path,
    generate_tts_audio,
)


def settings(**overrides) -> ElevenLabsSettings:
    values = {
        "provider": "elevenlabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "voice_name": "Rachel",
        "model_id": "eleven_multilingual_v2",
    }
    values.update(overrides)
    return ElevenLabsSettings(**values)


def test_dry_run_request_body_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    body = build_tts_request_body("Chapter One.", settings())

    assert body["text"] == "Chapter One."
    assert body["model_id"] == "eleven_multilingual_v2"
    assert "xi-api-key" not in str(body)


def test_dry_run_generation_record_never_calls_provider(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy-env-value")
    output_path = Path.cwd() / "internal" / "audiobook_lab" / "pytest-client" / "chunk.mp3"

    record = dry_run_generation_record(
        chunk_id="c001",
        text="Clean narration.",
        settings=settings(),
        output_path=output_path,
    )

    assert record["generation_status"] == "DRY_RUN_ONLY"
    assert record["provider_api_called"] is False
    assert record["audio_hash"] == ""
    assert "dummy-env-value" not in str(record)


def test_execute_requires_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    output_path = Path.cwd() / "internal" / "audiobook_lab" / "pytest-client" / "chunk.mp3"

    with pytest.raises(ElevenLabsSafetyError, match="ELEVENLABS_API_KEY"):
        generate_tts_audio(
            chunk_id="c001",
            text="Clean narration.",
            settings=settings(),
            output_path=output_path,
            execute=True,
        )


def test_output_path_cannot_be_frontend_public_or_build():
    with pytest.raises(ElevenLabsSafetyError, match="internal/audiobook_lab"):
        ensure_internal_output_path(Path.cwd() / "frontend" / "public" / "bad.mp3")

    with pytest.raises(ElevenLabsSafetyError, match="internal/audiobook_lab"):
        ensure_internal_output_path(Path.cwd() / "frontend" / "build" / "bad.mp3")


def test_beta_voice_clone_and_elevenreader_are_rejected():
    unsafe = settings(beta_services_allowed=True, voice_cloning_allowed=True, elevenreader_allowed=True)

    with pytest.raises(ElevenLabsSafetyError) as exc:
        build_tts_request_body("Clean narration.", unsafe)

    message = str(exc.value)
    assert "beta services" in message
    assert "voice cloning" in message
    assert "ElevenReader" in message
