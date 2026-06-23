from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.elevenlabs_internal_sample_import import (
    HOLD_SYNC_QA_REQUIRED,
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
