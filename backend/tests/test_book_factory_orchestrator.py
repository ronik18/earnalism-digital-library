from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.orchestrate_book_factory import (
    BOOK_FACTORY_AUDIOBOOK_STAGES,
    INTERNAL_AUDIOBOOK_ROOT,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    PRODUCTION_BLOCKED,
    run_factory,
)
from scripts.elevenlabs_full_chapter_generate import sha256_text


ROOT = Path.cwd()
FIXTURE_SLUG = "factory-fixture"


@pytest.fixture(autouse=True)
def cleanup_factory_fixture():
    target = INTERNAL_AUDIOBOOK_ROOT / FIXTURE_SLUG
    if target.exists():
        shutil.rmtree(target)
    yield
    if target.exists():
        shutil.rmtree(target)


def write_factory_config(tmp_path: Path, *, slug: str = FIXTURE_SLUG, generation_mode: str = "dry_run") -> Path:
    path = tmp_path / f"{slug}.yml"
    path.write_text(
        f"""slug: {slug}
book_title: Factory Fixture
title: Factory Fixture
author: Test Author
language: english
source_url: https://www.gutenberg.org/ebooks/1
source_type: gutenberg
public_domain_basis: Public domain fixture for internal dry-run tests.
audiobook:
  provider: elevenlabs
  voice_id: 21m00Tcm4TlvDq8ikWAM
  voice_name: Rachel
  model_id: eleven_multilingual_v2
  output_format: mp3_44100_192
  generation_mode: {generation_mode}
  scope: selected_chapters
  selected_chapters:
    - 1
  concurrency: 1
  max_concurrency: 3
  retry_policy:
    max_retries: 2
    retry_base_seconds: 0.01
    retry_max_seconds: 0.02
  cache_enabled: true
  public_target: false
  public_audio_target: false
""",
        encoding="utf-8",
    )
    return path


def create_internal_chunk_fixture(slug: str = FIXTURE_SLUG) -> Path:
    sample_dir = INTERNAL_AUDIOBOOK_ROOT / slug / "en" / "chapter-1"
    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    manual_dir.mkdir(parents=True, exist_ok=True)
    text = "Chapter One. Internal factory dry-run text only."
    text_path = manual_dir / "c001.txt"
    text_path.write_text(text + "\n", encoding="utf-8")
    expected = {
        "book_slug": slug,
        "language": "en",
        "chapter": 1,
        "provider": "ElevenLabs",
        "voice_name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "chunks": [
            {
                "chunk_id": "c001",
                "audio_filename": "factory-fixture-c001.mp3",
                "chunk_text_path": str(text_path.relative_to(ROOT)),
                "sentence_ids": ["s001"],
                "text_hash": sha256_text(text),
                "settings_hash": "factory-settings",
                "estimated_duration_seconds": 45,
                "public": False,
            }
        ],
    }
    (manual_dir / "expected_audio_filenames.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    (sample_dir / "sentence_map.json").write_text(
        json.dumps(
            {
                "s001": {
                    "source_text": text,
                    "narration_text": text,
                    "narration_decision": "speak",
                    "narration_mode": "premium_audiobook",
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (sample_dir / "elevenlabs_api_generation_config.json").write_text(
        json.dumps(
            {
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
                "production_status": PRODUCTION_BLOCKED,
                "public_audio_allowed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sample_dir


def fake_generation_result(**overrides):
    result = {
        "status": "DRY_RUN_READY",
        "chunk_count": 1,
        "total_characters": 48,
        "generated_chunk_count": 0,
        "skipped_cached_chunk_count": 0,
        "cache_hit_count": 0,
        "cache_miss_count": 1,
        "cache_stale_count": 0,
        "failed_chunk_count": 0,
        "retry_count": 0,
        "concurrency": 1,
        "elapsed_seconds": 0,
        "chunk_generation_manifest_path": "internal/audiobook_lab/factory-fixture/en/chapter-1/chunk_generation_manifest.json",
        "cache_manifest_path": "internal/audiobook_lab/cache/elevenlabs/cache_manifest.json",
        "sync_manifest_path": "internal/audiobook_lab/factory-fixture/en/chapter-1/sync_manifest.json",
        "full_chapter_audio_manifest_path": "internal/audiobook_lab/factory-fixture/en/chapter-1/full_chapter_audio_manifest.json",
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
    }
    result.update(overrides)
    return result


def stage(result, name):
    return next(item for item in result.stages if item.name == name)


def test_book_factory_adds_all_audiobook_stages(tmp_path: Path):
    config_path = write_factory_config(tmp_path)
    calls = []

    def fake_generator(**kwargs):
        calls.append(kwargs)
        return fake_generation_result()

    result = run_factory(config_path=config_path, output_root=tmp_path / "output", generator_fn=fake_generator)

    assert [item.name for item in result.stages] == list(BOOK_FACTORY_AUDIOBOOK_STAGES)
    assert calls[0]["mode"] == "dry-run"
    assert result.final_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result.final_gate["public_audio_allowed"] is False


def test_book_factory_dry_run_does_not_call_provider(tmp_path: Path):
    config_path = write_factory_config(tmp_path)

    def fake_generator(**_kwargs):
        return fake_generation_result(generated_chunk_count=0)

    result = run_factory(config_path=config_path, output_root=tmp_path / "output", generator_fn=fake_generator)
    tts_stage = stage(result, "AUDIOBOOK_TTS_GENERATION")

    assert tts_stage.status == "DRY_RUN_READY"
    assert tts_stage.details["provider_api_called"] is False


def test_book_factory_generate_mode_requires_env_flags(monkeypatch, tmp_path: Path):
    config_path = write_factory_config(tmp_path, generation_mode="generate")
    create_internal_chunk_fixture()
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("EARNALISM_ALLOW_ELEVENLABS_GENERATION", raising=False)

    result = run_factory(config_path=config_path, mode="generate", output_root=tmp_path / "output")
    tts_stage = stage(result, "AUDIOBOOK_TTS_GENERATION")

    assert tts_stage.status == "BLOCKED"
    assert any("ELEVENLABS_API_KEY is required" in blocker for blocker in tts_stage.blockers)
    assert tts_stage.details["provider_api_called"] is False


def test_book_factory_cache_hit_skips_provider(tmp_path: Path):
    config_path = write_factory_config(tmp_path, generation_mode="generate")

    def fake_generator(**_kwargs):
        return fake_generation_result(
            status="GENERATED_INTERNAL_ONLY_HOLD_QA",
            generated_chunk_count=0,
            skipped_cached_chunk_count=1,
            cache_hit_count=1,
            cache_miss_count=0,
        )

    result = run_factory(config_path=config_path, mode="generate", output_root=tmp_path / "output", generator_fn=fake_generator)
    tts_stage = stage(result, "AUDIOBOOK_TTS_GENERATION")
    cache_stage = stage(result, "AUDIOBOOK_CACHE_LOOKUP")

    assert cache_stage.details["cache_hit_count"] == 1
    assert tts_stage.details["provider_api_called"] is False
    assert tts_stage.details["skipped_cached_chunk_count"] == 1


def test_book_factory_failed_chunks_remain_hold(tmp_path: Path):
    config_path = write_factory_config(tmp_path)

    def fake_generator(**_kwargs):
        return fake_generation_result(status="INTERNAL_GENERATION_FAILED_HOLD_QA", failed_chunk_count=1)

    result = run_factory(config_path=config_path, output_root=tmp_path / "output", generator_fn=fake_generator)

    assert stage(result, "AUDIOBOOK_QA_GATE").status == "HOLD_AUDIO_QA"
    assert result.final_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED


def test_book_factory_release_gate_blocks_until_qa_complete(tmp_path: Path):
    config_path = write_factory_config(tmp_path)
    result = run_factory(
        config_path=config_path,
        output_root=tmp_path / "output",
        generator_fn=lambda **_kwargs: fake_generation_result(),
    )
    gate = result.final_gate

    assert gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert gate["public_audio_publish_allowed"] is False
    assert gate["listen_now_cta_allowed"] is False
    assert gate["audio_object_metadata_allowed"] is False
    assert gate["production_status"] == PRODUCTION_BLOCKED
    assert any("owner listening QA" in blocker for blocker in gate["blockers"])


def test_book_factory_reports_do_not_add_listen_now_or_audioobject(tmp_path: Path):
    config_path = write_factory_config(tmp_path)
    result = run_factory(
        config_path=config_path,
        output_root=tmp_path / "output",
        generator_fn=lambda **_kwargs: fake_generation_result(),
    )
    report_text = "\n".join(Path(path).read_text(encoding="utf-8") for path in result.reports.values())

    assert "Listen Now CTA allowed: `false`" in report_text
    assert "AudioObject metadata allowed: `false`" in report_text
    assert "Listen Now CTA allowed: `true`" not in report_text
    assert "AudioObject metadata allowed: `true`" not in report_text


def test_book_factory_output_paths_stay_internal(tmp_path: Path):
    config_path = write_factory_config(tmp_path)
    result = run_factory(
        config_path=config_path,
        output_root=tmp_path / "output",
        generator_fn=lambda **_kwargs: fake_generation_result(),
    )
    tts_stage = stage(result, "AUDIOBOOK_TTS_GENERATION")

    assert tts_stage.details["chunk_generation_manifest_path"].startswith("internal/audiobook_lab/")
    assert "frontend/public" not in json.dumps(result.final_gate)
    assert result.final_gate["public_audio_allowed"] is False
