from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.elevenlabs_internal_sample_import import (
    HOLD_SYNC_QA_REQUIRED,
    INTERNAL_FULL_CHAPTER_ONLY,
    INTERNAL_SAMPLE_ONLY,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    run_import,
)


@pytest.fixture(autouse=True)
def cleanup_import_test_files():
    internal_root = Path.cwd() / "internal" / "audiobook_lab"
    for path in internal_root.glob("pytest-elevenlabs-*"):
        if path.is_dir():
            shutil.rmtree(path)
    public_audio = Path.cwd() / "frontend" / "public" / "pytest-elevenlabs-public.mp3"
    if public_audio.exists():
        public_audio.unlink()
    yield
    for path in internal_root.glob("pytest-elevenlabs-*"):
        if path.is_dir():
            shutil.rmtree(path)
    if public_audio.exists():
        public_audio.unlink()


def make_sample_dir(name: str = "pytest-elevenlabs-sample") -> Path:
    sample_dir = Path.cwd() / "internal" / "audiobook_lab" / name
    imported_dir = sample_dir / "imported_audio"
    imported_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "sample_text.txt").write_text(
        "[s001] CHAPTER I. JONATHAN HARKER'S JOURNAL.\n"
        "[s002] Left Munich at 8:35 P. M., on 1st May.\n",
        encoding="utf-8",
    )
    return sample_dir


def make_full_chapter_dir(name: str = "pytest-elevenlabs-full") -> Path:
    sample_dir = Path.cwd() / "internal" / "audiobook_lab" / name
    imported_dir = sample_dir / "imported_audio"
    imported_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "full_chapter_text.txt").write_text(
        "# Internal-only full chapter fixture\n"
        "[s001] CHAPTER I. JONATHAN HARKER'S JOURNAL.\n"
        "[s002] Kept in shorthand.\n"
        "[s003] Left Munich at 8:35 P. M., on 1st May.\n"
        "[s004] Buda-Pesth seems a wonderful place.\n",
        encoding="utf-8",
    )
    (sample_dir / "chunk_manifest.json").write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c001",
                        "audio_filename": "dracula-chapter-1-elevenlabs-rachel-c001.mp3",
                        "sentence_start": "s001",
                        "sentence_end": "s002",
                        "text_hash": "fixture-text-hash-1",
                        "settings_hash": "fixture-settings-hash",
                    },
                    {
                        "chunk_id": "c002",
                        "audio_filename": "dracula-chapter-1-elevenlabs-rachel-c002.mp3",
                        "sentence_start": "s003",
                        "sentence_end": "s004",
                        "text_hash": "fixture-text-hash-2",
                        "settings_hash": "fixture-settings-hash",
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sample_dir


def test_import_validator_accepts_internal_audio_path_only():
    sample_dir = make_sample_dir()
    audio_path = sample_dir / "imported_audio" / "sample.mp3"
    audio_path.write_bytes(b"fake internal audio fixture")

    result = run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)
    manifest = json.loads((sample_dir / "imported_audio_manifest.json").read_text(encoding="utf-8"))
    sync = json.loads((sample_dir / "sync_manifest.json").read_text(encoding="utf-8"))

    assert result["status"] == INTERNAL_SAMPLE_ONLY
    assert result["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert manifest["audio_hash"] == result["audio_hash"]
    assert manifest["public_audio_release"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert manifest["public_audio_allowed"] is False
    assert manifest["audio_generated_by_repo"] is False
    assert manifest["audio_path"].startswith("internal/audiobook_lab/")
    assert sync["public"] is False
    assert sync["items"][0]["sync_status"] == HOLD_SYNC_QA_REQUIRED


def test_full_chapter_import_accepts_multiple_internal_chunks():
    sample_dir = make_full_chapter_dir()
    (sample_dir / "imported_audio" / "dracula-chapter-1-elevenlabs-rachel-c001.mp3").write_bytes(b"chunk-one")
    (sample_dir / "imported_audio" / "dracula-chapter-1-elevenlabs-rachel-c002.mp3").write_bytes(b"chunk-two")

    result = run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)
    manifest = json.loads((sample_dir / "imported_audio_manifest.json").read_text(encoding="utf-8"))
    sync = json.loads((sample_dir / "sync_manifest.json").read_text(encoding="utf-8"))

    assert result["status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert result["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert result["chunk_count"] == 2
    assert manifest["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert manifest["public_audio_release"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert manifest["public_audio_allowed"] is False
    assert manifest["production_approved"] is False
    assert manifest["listen_now_cta_allowed"] is False
    assert manifest["audio_object_metadata_allowed"] is False
    assert manifest["full_book_generation_allowed"] is False
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001", "c002"]
    assert all(chunk["audio_path"].startswith("internal/audiobook_lab/") for chunk in manifest["chunks"])
    assert sync["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert sync["public"] is False
    assert sync["items"][0]["chunk_id"] == "c001"
    assert sync["items"][-1]["chunk_id"] == "c002"
    assert all(item["start_ms"] is None and item["end_ms"] is None for item in sync["items"])


def test_import_validator_rejects_sample_dir_outside_internal_lab(tmp_path: Path):
    sample_dir = tmp_path / "outside"
    (sample_dir / "imported_audio").mkdir(parents=True)
    (sample_dir / "sample_text.txt").write_text("[s001] sample", encoding="utf-8")
    (sample_dir / "imported_audio" / "sample.mp3").write_bytes(b"fake")

    with pytest.raises(ValueError, match="sample-dir must stay under internal/audiobook_lab"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


def test_import_validator_rejects_public_audio_leakage():
    sample_dir = make_sample_dir("pytest-elevenlabs-public-leak")
    (sample_dir / "imported_audio" / "sample.mp3").write_bytes(b"fake internal audio fixture")
    public_audio = Path.cwd() / "frontend" / "public" / "pytest-elevenlabs-public.mp3"
    public_audio.write_bytes(b"fake public audio fixture")

    with pytest.raises(ValueError, match="public audio files are present"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


def test_import_validator_requires_exactly_one_audio_file():
    sample_dir = make_sample_dir("pytest-elevenlabs-two-files")
    (sample_dir / "imported_audio" / "sample-a.mp3").write_bytes(b"a")
    (sample_dir / "imported_audio" / "sample-b.wav").write_bytes(b"b")

    with pytest.raises(ValueError, match="Exactly one imported audio file"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


def test_full_chapter_workflow_docs_keep_public_release_and_production_blocked():
    root = Path.cwd()
    scorecard = (root / "ELEVENLABS_DRACULA_LISTENING_REVIEW_SCORECARD.md").read_text(encoding="utf-8")
    plan = (root / "ELEVENLABS_DRACULA_FULL_CHAPTER_INTERNAL_PLAN.md").read_text(encoding="utf-8")
    qa = (root / "ELEVENLABS_DRACULA_FULL_CHAPTER_QA_SCORECARD.md").read_text(encoding="utf-8")
    sync = (root / "ELEVENLABS_DRACULA_FULL_CHAPTER_SYNC_QA_REPORT.md").read_text(encoding="utf-8")
    package_json = json.loads((root / "package.json").read_text(encoding="utf-8"))

    assert "READY_FOR_FULL_CHAPTER_INTERNAL_ONLY" in scorecard
    assert "READY_FOR_FULL_CHAPTER_INTERNAL_ONLY" in plan
    assert "PUBLIC_AUDIO_RELEASE_BLOCKED" in plan
    assert "production_approved: false" in plan
    assert "listen_now_cta_allowed: false" in plan
    assert "audio_object_metadata_allowed: false" in plan
    assert "full_book_generation_allowed: false" in plan
    assert "No Listen Now CTA" in qa
    assert "No AudioObject metadata" in qa
    assert "HOLD_SYNC_QA_REQUIRED" in sync
    assert package_json["scripts"]["elevenlabs:full-chapter-import"].endswith(
        "--sample-dir internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full"
    )
