from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.copy_elevenlabs_chunk_to_clipboard import copy_chunk_to_clipboard
from scripts.prepare_elevenlabs_manual_generation import (
    prepare_manual_generation,
)
from scripts.validate_elevenlabs_manual_downloads import validate_manual_downloads
from scripts.validate_elevenlabs_narration_text import validate_text


ROOT = Path.cwd()
DRACULA_CHAPTER_DIR = ROOT / "internal" / "audiobook_lab" / "dracula" / "en" / "chapter-1"
LISTEN_NOW_CTA = "Listen Now " + "CTA"
AUDIO_OBJECT_METADATA = "AudioObject " + "metadata"


@pytest.fixture(autouse=True)
def cleanup_pytest_internal_audio_lab():
    test_root = ROOT / "internal" / "audiobook_lab" / "pytest-manual"
    if test_root.exists():
        shutil.rmtree(test_root)
    yield
    if test_root.exists():
        shutil.rmtree(test_root)


def test_first3_export_creates_clean_chunk_text_files():
    result = prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunks="c001-c003",
    )

    assert result["status"] == "MANUAL_ELEVENLABS_CHUNKS_READY"
    assert result["exported_chunk_count"] == 3
    for chunk_id in ("c001", "c002", "c003"):
        path = DRACULA_CHAPTER_DIR / "manual_elevenlabs_chunks" / f"{chunk_id}.txt"
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert validate_text(chunk_id, text) == []
        assert "[s001]" not in text
        assert "Kept in shorthand." not in text
        assert "Do not narrate" not in text
        assert "Internal-only" not in text
        assert "Public audio release" not in text
        assert "(_Mem._" not in text


def test_all_export_creates_expected_chunk_text_files():
    result = prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        all_chunks=True,
    )
    manifest = json.loads((DRACULA_CHAPTER_DIR / "chunk_manifest.json").read_text(encoding="utf-8"))

    assert result["exported_chunk_count"] == len(manifest["chunks"]) == 27
    for chunk in manifest["chunks"]:
        chunk_id = chunk["chunk_id"]
        path = DRACULA_CHAPTER_DIR / "manual_elevenlabs_chunks" / f"{chunk_id}.txt"
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip() == chunk["narration_text"].strip()


def test_checklist_contains_elevenlabs_settings_and_expected_filenames():
    prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunks="c001-c003",
    )

    manual_dir = DRACULA_CHAPTER_DIR / "manual_elevenlabs_chunks"
    checklist = (manual_dir / "generation_checklist.md").read_text(encoding="utf-8")
    expected = json.loads((manual_dir / "expected_audio_filenames.json").read_text(encoding="utf-8"))

    assert "Voice: Rachel" in checklist
    assert "Voice ID: `21m00Tcm4TlvDq8ikWAM`" in checklist
    assert "Eleven Multilingual v2" in checklist
    assert "Speed: 0.85" in checklist
    assert "Stability: 60-65%" in checklist
    assert "Similarity: 75-80%" in checklist
    assert "Style Exaggeration: 5-10%" in checklist
    assert "Speaker Boost: On" in checklist
    assert "No beta services" in checklist
    assert "No voice cloning" in checklist
    assert "No ElevenReader" in checklist
    assert "frontend/public" in checklist
    assert "frontend/build" in checklist
    assert LISTEN_NOW_CTA not in checklist
    assert AUDIO_OBJECT_METADATA not in checklist
    assert [chunk["chunk_id"] for chunk in expected["chunks"]] == ["c001", "c002", "c003"]
    assert expected["public_audio_allowed"] is False
    assert expected["production_approved"] is False
    assert expected["provider_api_called"] is False
    assert expected["audio_generated_by_repo"] is False
    assert expected["chunks"][0]["audio_filename"] == "dracula-chapter-1-elevenlabs-rachel-c001.mp3"


def test_clipboard_helper_does_not_require_pbcopy_for_test_pass():
    prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunks="c001",
    )

    result = copy_chunk_to_clipboard(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunk="c001",
        pbcopy_path="",
    )

    assert result["copied_to_clipboard"] is False
    assert "Chapter One. Jonathan Harker's Journal." in str(result["text"])


def test_download_validator_reports_missing_chunks():
    prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunks="c001-c003",
    )

    report = validate_manual_downloads(book_slug="dracula", language="en", chapter=1)

    assert report["status"] == "HOLD_MANUAL_DOWNLOADS_REQUIRED"
    assert report["expected_chunk_count"] == 3
    assert len(report["missing_audio"]) == 3
    assert report["present_audio"] == []
    assert report["public_audio_allowed"] is False
    assert report["production_approved"] is False


def make_pytest_expected_manifest() -> Path:
    manual_dir = ROOT / "internal" / "audiobook_lab" / "pytest-manual" / "en" / "chapter-1" / "manual_elevenlabs_chunks"
    imported_audio_dir = manual_dir.parent / "imported_audio"
    manual_dir.mkdir(parents=True)
    imported_audio_dir.mkdir(parents=True)
    payload = {
        "book_slug": "pytest-manual",
        "language": "en",
        "chapter": 1,
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "public_audio_allowed": False,
        "production_approved": False,
        "chunks": [
            {
                "chunk_id": "c001",
                "audio_filename": "pytest-c001.mp3",
                "expected_audio_path": "internal/audiobook_lab/pytest-manual/en/chapter-1/imported_audio/pytest-c001.mp3",
            }
        ],
    }
    path = manual_dir / "expected_audio_filenames.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_download_validator_computes_hashes_for_fixture_audio():
    manifest_path = make_pytest_expected_manifest()
    audio_path = manifest_path.parent.parent / "imported_audio" / "pytest-c001.mp3"
    audio_bytes = b"fake owner downloaded internal audio"
    audio_path.write_bytes(audio_bytes)

    report = validate_manual_downloads(book_slug="pytest-manual", language="en", chapter=1)

    assert report["status"] == "READY_FOR_INTERNAL_IMPORT"
    assert report["missing_audio"] == []
    assert len(report["present_audio"]) == 1
    assert report["present_audio"][0]["audio_hash"] == hashlib.sha256(audio_bytes).hexdigest()
    assert report["present_audio"][0]["path"].startswith("internal/audiobook_lab/")


def test_download_validator_rejects_frontend_public_and_build_audio_paths():
    make_pytest_expected_manifest()

    report = validate_manual_downloads(
        book_slug="pytest-manual",
        language="en",
        chapter=1,
        public_audio_override=["frontend/public/bad.mp3", "frontend/build/bad.wav"],
    )

    assert report["status"] == "HOLD_MANUAL_DOWNLOADS_REQUIRED"
    assert "audio files are present under frontend/public or frontend/build" in report["blockers"]
    assert report["public_audio_files"] == ["frontend/public/bad.mp3", "frontend/build/bad.wav"]


def test_no_public_audio_or_public_ui_metadata_is_enabled():
    prepare_manual_generation(
        book_slug="dracula",
        language="en",
        chapter=1,
        chunks="c001-c003",
    )
    manual_dir = DRACULA_CHAPTER_DIR / "manual_elevenlabs_chunks"
    expected = json.loads((manual_dir / "expected_audio_filenames.json").read_text(encoding="utf-8"))
    readme = (manual_dir / "README.md").read_text(encoding="utf-8")
    checklist = (manual_dir / "generation_checklist.md").read_text(encoding="utf-8")

    assert expected["public_audio_allowed"] is False
    assert expected["production_approved"] is False
    assert expected["public_audio_release"] == "PUBLIC_AUDIO_RELEASE_BLOCKED"
    assert LISTEN_NOW_CTA not in readme
    assert AUDIO_OBJECT_METADATA not in readme
    assert LISTEN_NOW_CTA not in checklist
    assert AUDIO_OBJECT_METADATA not in checklist
