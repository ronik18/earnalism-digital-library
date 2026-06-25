from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from scripts.elevenlabs_full_chapter_generate import (
    GenerationSafetyError,
    build_request_body,
    load_manual_chunks,
    run_generation,
    settings_hash,
    sha256_text,
)


ROOT = Path.cwd()
TEST_ROOT = ROOT / "internal" / "audiobook_lab" / "pytest-elevenlabs-api" / "en" / "chapter-1"


@pytest.fixture(autouse=True)
def cleanup_api_generation_fixture():
    if TEST_ROOT.parent.parent.exists():
        shutil.rmtree(TEST_ROOT.parent.parent)
    yield
    if TEST_ROOT.parent.parent.exists():
        shutil.rmtree(TEST_ROOT.parent.parent)


def api_config() -> dict:
    return {
        "provider": "elevenlabs",
        "voice_name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_192",
        "language_code": "en",
        "voice_settings": {
            "stability": 0.63,
            "similarity_boost": 0.76,
            "style": 0.08,
            "speed": 0.3,
            "use_speaker_boost": True,
        },
        "beta_services_used": False,
        "voice_cloning_used": False,
        "elevenreader_used": False,
        "production_status": "PRODUCTION_BLOCKED",
        "public_audio_allowed": False,
    }


def make_fixture(*, chunk_count: int = 3, config_overrides: dict | None = None) -> Path:
    manual_dir = TEST_ROOT / "manual_elevenlabs_chunks"
    manual_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    sentence_map = {}
    for index in range(1, chunk_count + 1):
        chunk_id = f"c{index:03d}"
        text = f"Chapter chunk {index} narration.\nThis is clean internal review text {index}."
        text_path = manual_dir / f"{chunk_id}.txt"
        text_path.write_text(text + "\n", encoding="utf-8")
        sentence_id = f"s{index:03d}"
        sentence_map[sentence_id] = {
            "source_text": f"Source sentence {index}.",
            "narration_text": text.splitlines()[0],
            "narration_decision": "speak",
            "narration_mode": "premium_audiobook",
        }
        chunks.append(
            {
                "chunk_id": chunk_id,
                "audio_filename": f"pytest-elevenlabs-rachel-{chunk_id}.mp3",
                "chunk_text_path": str(text_path.relative_to(ROOT)),
                "sentence_ids": [sentence_id],
                "text_hash": sha256_text(text),
                "settings_hash": "manual-settings-hash",
                "estimated_duration_seconds": 45.0,
                "public": False,
            }
        )
    (manual_dir / "expected_audio_filenames.json").write_text(
        json.dumps(
            {
                "book_slug": "pytest-elevenlabs-api",
                "language": "en",
                "chapter": 1,
                "provider": "ElevenLabs",
                "voice_name": "Rachel",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "public_audio_allowed": False,
                "production_status": "PRODUCTION_BLOCKED",
                "chunks": chunks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (TEST_ROOT / "sentence_map.json").write_text(json.dumps(sentence_map, indent=2) + "\n", encoding="utf-8")
    config = api_config()
    if config_overrides:
        config.update(config_overrides)
    (TEST_ROOT / "elevenlabs_api_generation_config.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )
    return TEST_ROOT


def run_fixture(**overrides):
    sample_dir = make_fixture()
    kwargs = {
        "book_slug": "pytest-elevenlabs-api",
        "language": "en",
        "chapter": 1,
        "mode": "dry-run",
        "chunks": "first3",
        "output_dir": sample_dir / "generated_audio",
        "config_path": sample_dir / "elevenlabs_api_generation_config.json",
    }
    kwargs.update(overrides)
    return run_generation(**kwargs)


def read_fixture_reports() -> str:
    texts = []
    for path in TEST_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
            texts.append(path.read_text(encoding="utf-8"))
    root_report = ROOT / "ELEVENLABS_DRACULA_GENERATION_COST_CONTROL_REPORT.md"
    if root_report.exists():
        texts.append(root_report.read_text(encoding="utf-8"))
    return "\n".join(texts)


def test_dry_run_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", raising=False)

    result = run_fixture()

    assert result["status"] == "DRY_RUN_READY"
    assert result["generated_chunk_count"] == 0
    assert result["chunk_count"] == 3
    assert not list((TEST_ROOT / "generated_audio").glob("*.mp3"))


def test_generate_mode_fails_without_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    with pytest.raises(GenerationSafetyError, match="ELEVENLABS_API_KEY is required"):
        run_fixture(mode="generate")


def test_generate_mode_fails_without_explicit_environment_switch(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-secret")
    monkeypatch.delenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", raising=False)

    with pytest.raises(GenerationSafetyError, match="EARNALISM_ALLOW_ELEVENLABS_GENERATION"):
        run_fixture(mode="generate")


def test_all_chunk_generation_requires_force_and_full_chapter_switch(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    monkeypatch.delenv("EARNALISM_ALLOW_FULL_CHAPTER_AUDIO_GENERATION", raising=False)

    with pytest.raises(GenerationSafetyError, match="--chunks all requires --force"):
        run_fixture(mode="generate", chunks="all")

    with pytest.raises(GenerationSafetyError, match="EARNALISM_ALLOW_FULL_CHAPTER_AUDIO_GENERATION"):
        run_fixture(mode="generate", chunks="all", force=True, max_chunks=3)


def test_all_chunk_generation_requires_max_chunks_cap(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    monkeypatch.setenv("EARNALISM_ALLOW_FULL_CHAPTER_AUDIO_GENERATION", "true")

    with pytest.raises(GenerationSafetyError, match="requires --max-chunks"):
        run_fixture(mode="generate", chunks="all", force=True)


def test_api_key_is_never_written_to_report_files(monkeypatch):
    secret = "unit-test-secret-that-must-not-be-written"
    monkeypatch.setenv("ELEVENLABS_API_KEY", secret)

    run_fixture()

    assert secret not in read_fixture_reports()


def test_output_path_must_stay_internal_and_rejects_public_or_build():
    sample_dir = make_fixture()
    common = {
        "book_slug": "pytest-elevenlabs-api",
        "language": "en",
        "chapter": 1,
        "mode": "dry-run",
        "chunks": "first3",
        "config_path": sample_dir / "elevenlabs_api_generation_config.json",
    }
    with pytest.raises(GenerationSafetyError, match="internal/audiobook_lab"):
        run_generation(**common, output_dir=ROOT / "frontend" / "public" / "bad-audio")
    with pytest.raises(GenerationSafetyError, match="internal/audiobook_lab"):
        run_generation(**common, output_dir=ROOT / "frontend" / "build" / "bad-audio")


def test_generated_audio_files_are_ignored_by_git():
    ignored_path = TEST_ROOT / "generated_audio" / "pytest-elevenlabs-rachel-c001.mp3"
    ignored_path.parent.mkdir(parents=True, exist_ok=True)
    ignored_path.write_bytes(b"ignored internal audio fixture")

    result = subprocess.run(
        ["git", "check-ignore", str(ignored_path.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0


def test_cached_chunks_are_skipped_without_force():
    sample_dir = make_fixture()
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    expected = json.loads(
        (sample_dir / "manual_elevenlabs_chunks" / "expected_audio_filenames.json").read_text(encoding="utf-8")
    )
    first = expected["chunks"][0]
    audio_path = sample_dir / "generated_audio" / first["audio_filename"]
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"cached internal audio")
    (sample_dir / "chunk_generation_manifest.json").write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c001",
                        "text_hash": first["text_hash"],
                        "settings_hash": settings_hash(config),
                        "audio_path": str(audio_path.relative_to(ROOT)),
                        "audio_hash": "cached-hash",
                        "generation_status": "GENERATED_INTERNAL_ONLY",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="first3",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
    )
    manifest = json.loads((sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8"))

    assert result["skipped_cached_chunk_count"] == 1
    assert manifest["chunks"][0]["generation_status"] == "SKIPPED_CACHED_INTERNAL_AUDIO"


def test_failed_http_response_records_sanitized_error_details(monkeypatch):
    sample_dir = make_fixture()
    secret = "unit-test-secret-that-must-not-be-written"
    monkeypatch.setenv("ELEVENLABS_API_KEY", secret)
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    def fail_http(request, timeout):
        headers = Message()
        headers["x-request-id"] = "req_http_400"
        body = json.dumps(
            {
                "detail": {
                    "status": "invalid_voice_settings",
                    "message": f"Invalid speed. xi-api-key: {secret}",
                }
            }
        ).encode("utf-8")
        raise HTTPError(request.full_url, 400, "Bad Request", headers, io.BytesIO(body))

    with pytest.raises(GenerationSafetyError, match="one or more ElevenLabs generation chunks failed"):
        run_generation(
            book_slug="pytest-elevenlabs-api",
            language="en",
            chapter=1,
            mode="generate",
            chunks="one",
            chunk_id="c001",
            output_dir=sample_dir / "generated_audio",
            config_path=sample_dir / "elevenlabs_api_generation_config.json",
            urlopen_fn=fail_http,
        )

    manifest = json.loads((sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8"))
    full = json.loads((sample_dir / "full_chapter_audio_manifest.json").read_text(encoding="utf-8"))
    chunk = manifest["chunks"][0]
    full_chunk = full["chunks"][0]

    assert chunk["status"] == "FAILED_INTERNAL_GENERATION"
    assert chunk["http_status"] == 400
    assert chunk["elevenlabs_error_code"] == "invalid_voice_settings"
    assert chunk["failure_stage"] == "HTTP_RESPONSE"
    assert chunk["retryable"] is False
    assert chunk["request_id"] == "req_http_400"
    assert "Invalid speed" in chunk["sanitized_error_message"]
    assert secret not in json.dumps(manifest)
    assert "xi-api-key:" not in chunk["sanitized_error_message"]
    assert chunk["audio_path"] == ""
    assert chunk["alignment_path"] == ""
    assert full["generation_status"] == "INTERNAL_GENERATION_FAILED_HOLD_QA"
    assert full_chunk["http_status"] == 400
    assert secret not in json.dumps(full)


def test_exception_records_failure_stage_and_sanitized_error(monkeypatch):
    sample_dir = make_fixture()
    secret = "unit-test-secret-exception"
    monkeypatch.setenv("ELEVENLABS_API_KEY", secret)
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    def explode(*_args, **_kwargs):
        raise RuntimeError(f"socket exploded Authorization: Bearer {secret}")

    with pytest.raises(GenerationSafetyError, match="one or more ElevenLabs generation chunks failed"):
        run_generation(
            book_slug="pytest-elevenlabs-api",
            language="en",
            chapter=1,
            mode="generate",
            chunks="one",
            chunk_id="c001",
            output_dir=sample_dir / "generated_audio",
            config_path=sample_dir / "elevenlabs_api_generation_config.json",
            urlopen_fn=explode,
        )

    manifest_text = (sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    chunk = manifest["chunks"][0]

    assert chunk["failure_stage"] == "UNKNOWN"
    assert chunk["retryable"] == "unknown"
    assert "socket exploded" in chunk["sanitized_error_message"]
    assert secret not in manifest_text
    assert "Bearer " not in chunk["sanitized_error_message"]


def test_one_chunk_mode_selects_only_c001():
    result = run_fixture(chunks="one", chunk_id="c001")
    manifest = json.loads((TEST_ROOT / "chunk_generation_manifest.json").read_text(encoding="utf-8"))

    assert result["chunk_count"] == 1
    assert result["chunk_id"] == "c001"
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001"]


def test_first3_mode_selects_c001_to_c003():
    make_fixture(chunk_count=5)
    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="first3",
        output_dir=TEST_ROOT / "generated_audio",
        config_path=TEST_ROOT / "elevenlabs_api_generation_config.json",
    )
    manifest = json.loads((TEST_ROOT / "chunk_generation_manifest.json").read_text(encoding="utf-8"))

    assert result["chunk_count"] == 3
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001", "c002", "c003"]


def test_all_mode_selects_every_available_full_chapter_chunk():
    make_fixture(chunk_count=5)
    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="all",
        output_dir=TEST_ROOT / "generated_audio",
        config_path=TEST_ROOT / "elevenlabs_api_generation_config.json",
    )
    manifest = json.loads((TEST_ROOT / "chunk_generation_manifest.json").read_text(encoding="utf-8"))

    assert result["chunk_count"] == 5
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001", "c002", "c003", "c004", "c005"]


def test_unsupported_fields_are_omitted_from_request_payload():
    request_behavior = {"unsupported_request_fields": ["voice_settings.speed", "voice_settings.style", "language_code"]}
    sample_dir = make_fixture(config_overrides={"request_behavior": request_behavior})
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    chunk = load_manual_chunks(sample_dir, "one", None, chunk_id="c001")[0]
    body = build_request_body(chunk=chunk, previous_chunk=None, next_chunk=None, config=config)

    assert "language_code" not in body
    assert "speed" not in body["voice_settings"]
    assert "style" not in body["voice_settings"]

    run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
    )
    manifest = json.loads((sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8"))
    shape = manifest["chunks"][0]["request_shape"]

    assert "language_code" not in shape["request_fields"]
    assert "speed" not in shape["voice_settings_fields"]
    assert "style" not in shape["voice_settings_fields"]
    assert shape["unsupported_fields_omitted"] == [
        "language_code",
        "voice_settings.speed",
        "voice_settings.style",
    ]


def test_successful_mock_generation_does_not_persist_api_key(monkeypatch):
    sample_dir = make_fixture()
    secret = "unit-test-success-secret"
    monkeypatch.setenv("ELEVENLABS_API_KEY", secret)
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    class FakeResponse:
        headers = {"x-request-id": "req_success_c001"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            payload = {
                "audio_base64": base64.b64encode(b"fake internal generated audio").decode("ascii"),
                "alignment": {
                    "characters": ["H", "i"],
                    "character_start_times_seconds": [0.0, 0.1],
                    "character_end_times_seconds": [0.1, 0.2],
                },
                "normalized_alignment": {
                    "characters": ["H", "i"],
                    "character_start_times_seconds": [0.0, 0.1],
                    "character_end_times_seconds": [0.1, 0.2],
                },
            }
            return json.dumps(payload).encode("utf-8")

    def ok_response(_request, timeout):
        return FakeResponse()

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        urlopen_fn=ok_response,
    )
    manifest_text = (sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8")

    assert result["generated_chunk_count"] == 1
    assert secret not in manifest_text
    assert "xi-api-key" not in manifest_text


def test_existing_non_cached_audio_blocks_before_api_call(monkeypatch):
    sample_dir = make_fixture()
    expected = json.loads(
        (sample_dir / "manual_elevenlabs_chunks" / "expected_audio_filenames.json").read_text(encoding="utf-8")
    )
    audio_path = sample_dir / "generated_audio" / expected["chunks"][0]["audio_filename"]
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"existing non-cache audio")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("ElevenLabs API should not be called when output already exists")

    with pytest.raises(GenerationSafetyError, match="one or more ElevenLabs generation chunks failed"):
        run_generation(
            book_slug="pytest-elevenlabs-api",
            language="en",
            chapter=1,
            mode="generate",
            chunks="first3",
            output_dir=sample_dir / "generated_audio",
            config_path=sample_dir / "elevenlabs_api_generation_config.json",
            urlopen_fn=fail_if_called,
        )

    manifest = json.loads((sample_dir / "chunk_generation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["chunks"][0]["generation_status"] == "BLOCKED_EXISTING_AUDIO_REQUIRES_FORCE"
    assert manifest["chunks"][0]["provider_api_called"] is False


def test_sync_and_public_release_gates_remain_blocked():
    result = run_fixture()
    sync = json.loads((TEST_ROOT / "sync_manifest.json").read_text(encoding="utf-8"))
    audio_manifest = json.loads((TEST_ROOT / "full_chapter_audio_manifest.json").read_text(encoding="utf-8"))
    report_text = read_fixture_reports()

    assert result["sync_status"] == "HOLD_SYNC_QA_REQUIRED"
    assert sync["sync_status"] == "HOLD_SYNC_QA_REQUIRED"
    assert audio_manifest["production_status"] == "PRODUCTION_BLOCKED"
    assert audio_manifest["public_audio_allowed"] is False
    assert audio_manifest["listen_now_cta_allowed"] is False
    assert audio_manifest["audio_object_metadata_allowed"] is False
    assert "listen_now_cta_allowed: true" not in report_text
    assert "audio_object_metadata_allowed: true" not in report_text
