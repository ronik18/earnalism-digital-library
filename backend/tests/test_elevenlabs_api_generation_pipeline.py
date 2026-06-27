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
    cache_alignment_path,
    cache_key_for,
    cache_manifest_path,
    load_manual_chunks,
    run_generation,
    sha256_text,
)


ROOT = Path.cwd()
TEST_ROOT = ROOT / "internal" / "audiobook_lab" / "pytest-elevenlabs-api" / "en" / "chapter-1"
TEST_CACHE_ROOT = ROOT / "internal" / "audiobook_lab" / "pytest-elevenlabs-api" / "cache" / "elevenlabs"


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
            "speed": 0.78,
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
        "cache_dir": TEST_CACHE_ROOT,
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


def diagnostic_path(sample_dir: Path, chunk_id: str, suffix: str) -> Path:
    return sample_dir / f"elevenlabs_api_diagnostic_{chunk_id}_{suffix}"


def fake_urlopen_with_audio(audio: bytes = b"fake internal generated audio", request_id: str = "req_fake_c001"):
    class FakeResponse:
        headers = {"x-request-id": request_id}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            payload = {
                "audio_base64": base64.b64encode(audio).decode("ascii"),
                "alignment": {
                    "characters": ["H"],
                    "character_start_times_seconds": [0.0],
                    "character_end_times_seconds": [0.1],
                },
            }
            return json.dumps(payload).encode("utf-8")

    def ok_response(_request, timeout):
        return FakeResponse()

    return ok_response


def generate_c001_to_cache(monkeypatch, sample_dir: Path) -> dict:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-cache-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    return run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=fake_urlopen_with_audio(b"cached generated audio", "req_cache_c001"),
    )


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


def test_parallel_concurrency_limit_is_enforced():
    with pytest.raises(GenerationSafetyError, match="--concurrency must not exceed --max-concurrency"):
        run_fixture(concurrency=4)

    with pytest.raises(GenerationSafetyError, match="--max-concurrency above"):
        run_fixture(concurrency=4, max_concurrency=4)

    result = run_fixture(concurrency=4, max_concurrency=4, allow_concurrency_override=True)

    assert result["concurrency"] == 4


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


def test_identical_chunk_and_settings_reuse_cache_without_api_call(monkeypatch):
    sample_dir = make_fixture()
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-cache-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    class FakeResponse:
        headers = {"x-request-id": "req_cache_c001"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            payload = {
                "audio_base64": base64.b64encode(b"cached generated audio").decode("ascii"),
                "alignment": {
                    "characters": ["H"],
                    "character_start_times_seconds": [0.0],
                    "character_end_times_seconds": [0.1],
                },
            }
            return json.dumps(payload).encode("utf-8")

    calls = {"count": 0}

    def ok_response(_request, timeout):
        calls["count"] += 1
        return FakeResponse()

    first = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=ok_response,
    )
    assert first["generated_chunk_count"] == 1
    assert first["cache_miss_count"] == 1

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("ElevenLabs API should not be called on cache hit")

    generated_audio = sample_dir / "generated_audio" / "pytest-elevenlabs-rachel-c001.mp3"
    generated_alignment = sample_dir / "generated_alignment" / "c001.json"
    generated_audio.unlink()
    generated_alignment.unlink()
    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=fail_if_called,
    )
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))

    assert calls["count"] == 1
    assert result["skipped_cached_chunk_count"] == 1
    assert result["cache_hit_count"] == 1
    assert manifest["chunks"][0]["cache_status"] == "HIT"
    assert manifest["chunks"][0]["provider_api_called"] is False
    assert generated_audio.exists()
    assert generated_alignment.exists()


def test_changed_text_is_cache_miss(monkeypatch):
    sample_dir = make_fixture()
    generate_c001_to_cache(monkeypatch, sample_dir)
    (sample_dir / "manual_elevenlabs_chunks" / "c001.txt").write_text(
        "Chapter chunk 1 narration changed.\nThis is new text for cache miss.\n",
        encoding="utf-8",
    )

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
    )
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))

    assert result["cache_miss_count"] == 1
    assert manifest["chunks"][0]["cache_status"] == "MISS"


def test_changed_voice_settings_are_cache_miss(monkeypatch):
    sample_dir = make_fixture()
    generate_c001_to_cache(monkeypatch, sample_dir)
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    config["voice_settings"]["stability"] = 0.71
    (sample_dir / "elevenlabs_api_generation_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
    )
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))

    assert result["cache_miss_count"] == 1
    assert manifest["chunks"][0]["cache_status"] == "MISS"


def test_missing_cached_alignment_is_stale_and_regenerates(monkeypatch):
    sample_dir = make_fixture()
    generate_c001_to_cache(monkeypatch, sample_dir)
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    chunk = load_manual_chunks(sample_dir, "one", None, chunk_id="c001")[0]
    cache_key = cache_key_for(chunk, config)
    cache_alignment_path(TEST_CACHE_ROOT, cache_key).unlink()
    calls = {"count": 0}

    def regenerate(_request, timeout):
        calls["count"] += 1
        return fake_urlopen_with_audio(b"regenerated after stale alignment", "req_regen_c001")(_request, timeout)

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=regenerate,
    )
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))

    assert calls["count"] == 1
    assert result["cache_stale_count"] == 1
    assert result["generated_chunk_count"] == 1
    assert manifest["chunks"][0]["cache_preflight_status"] == "STALE"
    assert manifest["chunks"][0]["cache_status"] == "GENERATED"


def test_cache_paths_stay_internal_and_audio_binaries_are_ignored(monkeypatch):
    sample_dir = make_fixture()
    generate_c001_to_cache(monkeypatch, sample_dir)
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    chunk = load_manual_chunks(sample_dir, "one", None, chunk_id="c001")[0]
    cache_key = cache_key_for(chunk, config)
    manifest_path = cache_manifest_path(TEST_CACHE_ROOT)
    cache_audio = TEST_CACHE_ROOT / "audio" / f"{cache_key}.mp3"

    assert str(manifest_path.relative_to(ROOT)).startswith("internal/audiobook_lab/")
    assert str(cache_audio.relative_to(ROOT)).startswith("internal/audiobook_lab/")

    result = subprocess.run(
        ["git", "check-ignore", str(cache_audio.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0


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
            cache_dir=TEST_CACHE_ROOT,
            urlopen_fn=fail_http,
        )

    manifest = json.loads(diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8"))
    full = json.loads(diagnostic_path(sample_dir, "c001", "audio_manifest.json").read_text(encoding="utf-8"))
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


def test_retryable_http_response_retries_then_succeeds(monkeypatch):
    sample_dir = make_fixture()
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-retry-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    calls = {"count": 0}

    def retry_once(request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            headers = Message()
            headers["x-request-id"] = "req_retry_429"
            body = json.dumps({"detail": {"status": "rate_limited", "message": "try again"}}).encode("utf-8")
            raise HTTPError(request.full_url, 429, "Too Many Requests", headers, io.BytesIO(body))
        return fake_urlopen_with_audio(b"retry recovered audio", "req_retry_success")(request, timeout)

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        max_retries=2,
        sleep_fn=lambda _seconds: None,
        urlopen_fn=retry_once,
    )
    manifest = json.loads(diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8"))
    chunk = manifest["chunks"][0]

    assert calls["count"] == 2
    assert result["generated_chunk_count"] == 1
    assert result["retry_count"] == 1
    assert chunk["retry_count"] == 1
    assert chunk["attempt_count"] == 2


def test_non_retryable_http_response_does_not_retry(monkeypatch):
    sample_dir = make_fixture()
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-no-retry-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    calls = {"count": 0}

    def fail_validation(request, timeout):
        calls["count"] += 1
        headers = Message()
        headers["x-request-id"] = "req_no_retry_400"
        body = json.dumps({"detail": {"status": "invalid_request", "message": "validation failed"}}).encode("utf-8")
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
            cache_dir=TEST_CACHE_ROOT,
            max_retries=3,
            sleep_fn=lambda _seconds: None,
            urlopen_fn=fail_validation,
        )
    manifest = json.loads(diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8"))
    chunk = manifest["chunks"][0]

    assert calls["count"] == 1
    assert chunk["http_status"] == 400
    assert chunk["retryable"] is False
    assert chunk["retry_count"] == 0
    assert chunk["attempt_count"] == 1


def test_failed_chunk_can_resume_with_resume_flag(monkeypatch):
    sample_dir = make_fixture()
    previous_manifest = sample_dir / "elevenlabs_api_diagnostic_c001_generation_manifest.json"
    previous_manifest.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c001",
                        "generation_status": "FAILED_INTERNAL_GENERATION",
                        "cache_status": "FAILED",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-resume-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="generate",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
        resume_failed=True,
        sleep_fn=lambda _seconds: None,
        urlopen_fn=fake_urlopen_with_audio(b"resumed generated audio", "req_resume_c001"),
    )
    manifest = json.loads(previous_manifest.read_text(encoding="utf-8"))
    chunk = manifest["chunks"][0]

    assert result["generated_chunk_count"] == 1
    assert result["resume_failed"] is True
    assert chunk["resume_status"] == "PREVIOUS_FAILURE_RETRY"
    assert chunk["cache_status"] == "GENERATED"


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
            cache_dir=TEST_CACHE_ROOT,
            urlopen_fn=explode,
        )

    manifest_text = diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    chunk = manifest["chunks"][0]

    assert chunk["failure_stage"] == "UNKNOWN"
    assert chunk["retryable"] == "unknown"
    assert "socket exploded" in chunk["sanitized_error_message"]
    assert secret not in manifest_text
    assert "Bearer " not in chunk["sanitized_error_message"]


def test_one_chunk_mode_selects_only_c001():
    result = run_fixture(chunks="one", chunk_id="c001")
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))

    assert result["chunk_count"] == 1
    assert result["chunk_id"] == "c001"
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001"]
    assert result["chunk_generation_manifest_path"].endswith(
        "elevenlabs_api_diagnostic_c001_generation_manifest.json"
    )


def test_one_chunk_diagnostic_does_not_overwrite_full_chapter_import_manifests():
    sample_dir = make_fixture()
    full_manifest = sample_dir / "full_chapter_audio_manifest.json"
    sync_manifest = sample_dir / "sync_manifest.json"
    original_full = {
        "generated_by": "scripts/elevenlabs_internal_sample_import.py",
        "chunk_count": 27,
        "audio_status": "INTERNAL_FULL_CHAPTER_ONLY",
        "audio_hash": "existing-full-chapter-hash",
        "public_audio_allowed": False,
        "production_status": "PRODUCTION_BLOCKED",
    }
    original_sync = {
        "sync_status": "HOLD_SYNC_QA_REQUIRED",
        "items": [{"sentence_id": "s001"}],
        "public_audio_allowed": False,
        "production_status": "PRODUCTION_BLOCKED",
    }
    full_manifest.write_text(json.dumps(original_full, indent=2) + "\n", encoding="utf-8")
    sync_manifest.write_text(json.dumps(original_sync, indent=2) + "\n", encoding="utf-8")

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
    )

    assert json.loads(full_manifest.read_text(encoding="utf-8")) == original_full
    assert json.loads(sync_manifest.read_text(encoding="utf-8")) == original_sync
    assert Path(result["full_chapter_audio_manifest_path"]).name == "elevenlabs_api_diagnostic_c001_audio_manifest.json"
    assert Path(result["sync_manifest_path"]).name == "elevenlabs_api_diagnostic_c001_sync_manifest.json"


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
        cache_dir=TEST_CACHE_ROOT,
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
        cache_dir=TEST_CACHE_ROOT,
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
        cache_dir=TEST_CACHE_ROOT,
    )
    manifest = json.loads(diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8"))
    shape = manifest["chunks"][0]["request_shape"]

    assert "language_code" not in shape["request_fields"]
    assert "speed" not in shape["voice_settings_fields"]
    assert "style" not in shape["voice_settings_fields"]
    assert shape["unsupported_fields_omitted"] == [
        "language_code",
        "voice_settings.speed",
        "voice_settings.style",
    ]


def test_out_of_range_ui_speed_is_auto_omitted_from_request_payload():
    settings = dict(api_config()["voice_settings"])
    settings["speed"] = 0.3
    sample_dir = make_fixture(config_overrides={"voice_settings": settings})
    config = json.loads((sample_dir / "elevenlabs_api_generation_config.json").read_text(encoding="utf-8"))
    chunk = load_manual_chunks(sample_dir, "one", None, chunk_id="c001")[0]
    body = build_request_body(chunk=chunk, previous_chunk=None, next_chunk=None, config=config)

    assert config["voice_settings"]["speed"] == 0.3
    assert "speed" not in body["voice_settings"]

    result = run_generation(
        book_slug="pytest-elevenlabs-api",
        language="en",
        chapter=1,
        mode="dry-run",
        chunks="one",
        chunk_id="c001",
        output_dir=sample_dir / "generated_audio",
        config_path=sample_dir / "elevenlabs_api_generation_config.json",
        cache_dir=TEST_CACHE_ROOT,
    )
    manifest = json.loads(Path(result["chunk_generation_manifest_path"]).read_text(encoding="utf-8"))
    shape = manifest["chunks"][0]["request_shape"]

    assert "speed" not in shape["voice_settings_fields"]
    assert shape["auto_omitted_invalid_fields"] == ["voice_settings.speed"]


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
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=ok_response,
    )
    manifest_text = diagnostic_path(sample_dir, "c001", "generation_manifest.json").read_text(encoding="utf-8")

    assert result["generated_chunk_count"] == 1
    assert secret not in manifest_text
    assert "xi-api-key" not in manifest_text


def test_mock_generation_uses_with_timestamps_json_response_shape(monkeypatch):
    sample_dir = make_fixture()
    monkeypatch.setenv("ELEVENLABS_API_KEY", "unit-test-request-shape-secret")
    monkeypatch.setenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", "true")
    captured = {}

    class FakeResponse:
        headers = {"x-request-id": "req_shape_c001"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {
                    "audio_base64": base64.b64encode(b"shape audio").decode("ascii"),
                    "alignment": {
                        "characters": ["H"],
                        "character_start_times_seconds": [0.0],
                        "character_end_times_seconds": [0.1],
                    },
                }
            ).encode("utf-8")

    def capture_request(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
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
        cache_dir=TEST_CACHE_ROOT,
        urlopen_fn=capture_request,
    )

    assert result["generated_chunk_count"] == 1
    assert captured["url"].endswith(
        "/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM/with-timestamps?output_format=mp3_44100_192"
    )
    assert "output_format" not in captured["body"]
    assert captured["body"]["model_id"] == "eleven_multilingual_v2"
    assert captured["body"]["language_code"] == "en"
    assert captured["body"]["voice_settings"]["stability"] == 0.63
    assert captured["body"]["voice_settings"]["speed"] == 0.78
    assert captured["headers"]["Accept"] == "application/json"


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
            cache_dir=TEST_CACHE_ROOT,
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
