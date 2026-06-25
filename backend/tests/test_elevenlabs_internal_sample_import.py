from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.elevenlabs_internal_sample_import import (
    HOLD_SYNC_QA_REQUIRED,
    INTERNAL_FULL_CHAPTER_ONLY,
    INTERNAL_SAMPLE_ONLY,
    PRODUCTION_BLOCKED,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    run_import,
    sha256_file,
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


def make_manual_chunk_sample_dir(
    name: str = "pytest-elevenlabs-manual-chunks",
    *,
    missing_chunk: str | None = None,
    unexpected_audio: bool = False,
    public_expected_path: bool = False,
    include_full_chapter_manifest: bool = False,
) -> Path:
    sample_dir = Path.cwd() / "internal" / "audiobook_lab" / name
    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    imported_dir = sample_dir / "imported_audio"
    manual_dir.mkdir(parents=True, exist_ok=True)
    imported_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "sentence_map.json").write_text(
        json.dumps(
            {
                "s001": {"source_text": "CHAPTER I. JONATHAN HARKER'S JOURNAL"},
                "s002": {"source_text": "May the third. Bistritz."},
                "s003": {"source_text": "Left Munich at 8:35 P.M."},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    chunks = []
    present_audio = []
    for index, chunk_id in enumerate(("c001", "c002", "c003"), start=1):
        filename = f"dracula-chapter-1-elevenlabs-rachel-{chunk_id}.mp3"
        audio_path = imported_dir / filename
        sentence_id = f"s{index:03d}"
        if chunk_id != missing_chunk:
            audio_path.write_bytes(f"fake manual chunk {chunk_id}".encode("utf-8"))
            present_audio.append(
                {
                    "chunk_id": chunk_id,
                    "audio_filename": filename,
                    "path": str(audio_path.relative_to(Path.cwd())),
                    "audio_hash": sha256_file(audio_path),
                    "file_size_bytes": audio_path.stat().st_size,
                    "public": False,
                }
            )
        expected_audio_path = (
            Path("frontend") / "public" / filename
            if public_expected_path and chunk_id == "c001"
            else imported_dir.relative_to(Path.cwd()) / filename
        )
        chunks.append(
            {
                "chunk_id": chunk_id,
                "audio_filename": filename,
                "expected_audio_path": str(expected_audio_path),
                "chunk_text_path": str((manual_dir / f"{chunk_id}.txt").relative_to(Path.cwd())),
                "sentence_ids": [sentence_id],
                "text_hash": f"text-hash-{chunk_id}",
                "settings_hash": "settings-hash",
                "estimated_duration_seconds": 45.0,
                "generation_status": "PENDING_MANUAL_UI_GENERATION",
                "public": False,
            }
        )
        (manual_dir / f"{chunk_id}.txt").write_text(f"Chunk {chunk_id} narration.\n", encoding="utf-8")
    if unexpected_audio:
        (imported_dir / "dracula-chapter-1-elevenlabs-rachel-c999.mp3").write_bytes(b"unexpected")
    expected_manifest = {
        "book_slug": "dracula",
        "language": "en",
        "chapter": 1,
        "provider": "ElevenLabs",
        "voice_name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "imported_audio_dir": str(imported_dir.relative_to(Path.cwd())),
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "production_approved": False,
        "chunks": chunks,
    }
    (manual_dir / "expected_audio_filenames.json").write_text(
        json.dumps(expected_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    validation_report = {
        "status": "READY_FOR_INTERNAL_IMPORT",
        "book_slug": "dracula",
        "language": "en",
        "chapter": 1,
        "expected_chunk_count": 3,
        "present_audio": present_audio,
        "missing_audio": [],
        "unexpected_audio": [],
        "public_audio_files": [],
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_approved": False,
    }
    (manual_dir / "manual_download_validation_report.json").write_text(
        json.dumps(validation_report, indent=2) + "\n",
        encoding="utf-8",
    )
    if include_full_chapter_manifest:
        (sample_dir / "chunk_manifest.json").write_text(
            json.dumps(
                {
                    "chunks": [
                        {
                            "chunk_id": chunk["chunk_id"],
                            "sentence_ids": chunk["sentence_ids"],
                            "text_hash": chunk["text_hash"],
                            "settings_hash": chunk["settings_hash"],
                            "estimated_duration_seconds": chunk["estimated_duration_seconds"],
                            "audio_filename": chunk["audio_filename"],
                        }
                        for chunk in chunks
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


def test_manual_ready_validation_imports_three_chunks_successfully():
    sample_dir = make_manual_chunk_sample_dir()

    result = run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)
    manifest = json.loads((sample_dir / "imported_audio_manifest.json").read_text(encoding="utf-8"))
    combined = json.loads((sample_dir / "combined_sample_manifest.json").read_text(encoding="utf-8"))
    sync = json.loads((sample_dir / "sync_manifest.json").read_text(encoding="utf-8"))

    assert result["status"] == INTERNAL_SAMPLE_ONLY
    assert result["chunk_count"] == 3
    assert result["combined_sample_manifest_path"].endswith("combined_sample_manifest.json")
    assert manifest["import_workflow"] == "manual_chunk_sample"
    assert manifest["audio_status"] == INTERNAL_SAMPLE_ONLY
    assert manifest["chunk_count"] == 3
    assert [chunk["chunk_id"] for chunk in manifest["chunks"]] == ["c001", "c002", "c003"]
    assert all(len(chunk["audio_hash"]) == 64 for chunk in manifest["chunks"])
    assert all(chunk["audio_path"].startswith("internal/audiobook_lab/") for chunk in manifest["chunks"])
    assert combined["provider"] == "ElevenLabs"
    assert combined["voice"] == "Rachel"
    assert combined["voice_id"] == "21m00Tcm4TlvDq8ikWAM"
    assert combined["status"] == INTERNAL_SAMPLE_ONLY
    assert combined["chunk_count"] == 3
    assert combined["production_status"] == PRODUCTION_BLOCKED
    assert combined["public_audio_allowed"] is False
    assert manifest["production_status"] == PRODUCTION_BLOCKED
    assert manifest["public_audio_allowed"] is False
    assert manifest["production_approved"] is False
    assert sync["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert sync["production_status"] == PRODUCTION_BLOCKED
    assert sync["public_audio_allowed"] is False
    assert [item["chunk_id"] for item in sync["items"]] == ["c001", "c002", "c003"]


def test_manual_full_chapter_ready_validation_imports_internal_full_chapter():
    sample_dir = make_manual_chunk_sample_dir(
        "pytest-elevenlabs-manual-full-chapter",
        include_full_chapter_manifest=True,
    )

    result = run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)
    manifest = json.loads((sample_dir / "imported_audio_manifest.json").read_text(encoding="utf-8"))
    combined = json.loads((sample_dir / "combined_sample_manifest.json").read_text(encoding="utf-8"))
    sync = json.loads((sample_dir / "sync_manifest.json").read_text(encoding="utf-8"))

    assert result["status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert manifest["import_workflow"] == "manual_full_chapter"
    assert manifest["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert combined["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert combined["status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert manifest["production_status"] == PRODUCTION_BLOCKED
    assert combined["production_status"] == PRODUCTION_BLOCKED
    assert manifest["public_audio_allowed"] is False
    assert combined["public_audio_allowed"] is False
    assert manifest["listen_now_cta_allowed"] is False
    assert combined["listen_now_cta_allowed"] is False
    assert manifest["audio_object_metadata_allowed"] is False
    assert combined["audio_object_metadata_allowed"] is False
    assert all(len(chunk["audio_hash"]) == 64 for chunk in manifest["chunks"])
    assert sync["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert sync["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert sync["production_status"] == PRODUCTION_BLOCKED
    assert sync["public_audio_allowed"] is False


def test_manual_ready_validation_missing_chunk_fails():
    sample_dir = make_manual_chunk_sample_dir("pytest-elevenlabs-manual-missing", missing_chunk="c003")

    with pytest.raises(FileNotFoundError, match="missing expected manual chunk audio files"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


def test_manual_ready_validation_unexpected_chunk_fails():
    sample_dir = make_manual_chunk_sample_dir("pytest-elevenlabs-manual-unexpected", unexpected_audio=True)

    with pytest.raises(ValueError, match="unexpected audio files in manual imported_audio"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


def test_manual_ready_validation_public_build_expected_path_fails():
    sample_dir = make_manual_chunk_sample_dir("pytest-elevenlabs-manual-public-path", public_expected_path=True)

    with pytest.raises(ValueError, match="expected audio path must stay under internal/audiobook_lab"):
        run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)


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


def test_dracula_full_chapter_import_evidence_and_qa_forms_remain_internal_only():
    root = Path.cwd()
    sample_dir = root / "internal" / "audiobook_lab" / "dracula" / "en" / "chapter-1"
    imported_manifest_path = sample_dir / "imported_audio_manifest.json"
    combined_manifest_path = sample_dir / "combined_sample_manifest.json"
    full_audio_manifest_path = sample_dir / "full_chapter_audio_manifest.json"
    sync_manifest_path = sample_dir / "sync_manifest.json"
    owner_qa_path = sample_dir / "full_chapter_owner_listening_qa_form.md"
    sync_qa_path = sample_dir / "full_chapter_highlight_sync_qa_form.md"

    run_import(book_slug="dracula", chapter="1", sample_dir=sample_dir)

    for path in (
        imported_manifest_path,
        combined_manifest_path,
        full_audio_manifest_path,
        sync_manifest_path,
        owner_qa_path,
        sync_qa_path,
    ):
        assert path.exists(), f"missing full chapter evidence file: {path}"

    imported = json.loads(imported_manifest_path.read_text(encoding="utf-8"))
    combined = json.loads(combined_manifest_path.read_text(encoding="utf-8"))
    full_audio = json.loads(full_audio_manifest_path.read_text(encoding="utf-8"))
    sync = json.loads(sync_manifest_path.read_text(encoding="utf-8"))
    owner_qa = owner_qa_path.read_text(encoding="utf-8")
    sync_qa = sync_qa_path.read_text(encoding="utf-8")

    expected_audio_hash = "5cea977f3fcffca744f9fa71a8da249943462a9096580d6522b4d80c509bc2c0"
    assert imported["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert imported["chunk_count"] == 27
    assert len(imported["chunks"]) == 27
    assert imported["audio_hash"] == expected_audio_hash
    assert imported["listening_qa_status"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert imported["owner_listening_score"] == 9.4
    assert imported["owner_listening_decision"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert imported["internal_player_test_status"] == "READY_TO_PREPARE_INTERNAL_PLAYER_TEST"
    assert combined["status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert combined["chunk_count"] == 27
    assert combined["combined_audio_hash"] == expected_audio_hash
    assert combined["listening_qa_status"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert combined["owner_listening_score"] == 9.4
    assert combined["owner_listening_decision"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert combined["internal_player_test_status"] == "READY_TO_PREPARE_INTERNAL_PLAYER_TEST"
    assert full_audio["audio_status"] == INTERNAL_FULL_CHAPTER_ONLY
    assert full_audio["chunk_count"] == 27
    assert full_audio["audio_hash"] == expected_audio_hash
    assert full_audio["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert full_audio["listening_qa_status"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert full_audio["owner_listening_qa_status"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert full_audio["owner_listening_score"] == 9.4
    assert full_audio["owner_listening_decision"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert full_audio["owner_reviewer"] == "Ronik Basak"
    assert full_audio["owner_review_date"] == "24/06/2026"
    assert full_audio["owner_listening_scores"]["pacing"] == 9.3
    assert full_audio["internal_player_test_status"] == "READY_TO_PREPARE_INTERNAL_PLAYER_TEST"
    assert sync["sync_status"] == HOLD_SYNC_QA_REQUIRED
    assert sync["listening_qa_status"] == "READY_FOR_INTERNAL_PLAYER_TEST"
    assert sync["internal_player_test_status"] == "READY_TO_PREPARE_INTERNAL_PLAYER_TEST"
    assert sync.get("timing_qa_passed", False) is False
    assert len(sync["items"]) == 220

    for payload in (imported, combined, full_audio, sync):
        assert payload["public_audio_allowed"] is False
        assert payload["production_status"] == PRODUCTION_BLOCKED
    assert imported["listen_now_cta_allowed"] is False
    assert imported["audio_object_metadata_allowed"] is False
    assert full_audio["listen_now_cta_allowed"] is False
    assert full_audio["audio_object_metadata_allowed"] is False

    assert "READY_FOR_INTERNAL_PLAYER_TEST" in owner_qa
    assert "overall score: 9.4/10" in owner_qa
    assert "Selected decision: `HOLD_SYNC_QA_REQUIRED`" in sync_qa
    assert "PUBLIC_AUDIO_RELEASE_BLOCKED" in owner_qa
    assert "PRODUCTION_BLOCKED" in sync_qa
    assert "READY_FOR_INTERNAL_PLAYER_TEST" in (
        root / "ELEVENLABS_DRACULA_INTERNAL_PLAYER_TEST_READINESS_REPORT.md"
    ).read_text(encoding="utf-8")
    assert "No Listen Now CTA" in (root / "ELEVENLABS_DRACULA_FULL_CHAPTER_QA_SCORECARD.md").read_text(
        encoding="utf-8"
    )
    assert "No AudioObject metadata" in (root / "ELEVENLABS_DRACULA_FULL_CHAPTER_QA_SCORECARD.md").read_text(
        encoding="utf-8"
    )

    audio_path = imported["chunks"][0]["audio_path"]
    check_ignore = subprocess.run(
        ["git", "check-ignore", audio_path],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    tracked_audio = subprocess.run(
        ["git", "ls-files", audio_path],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert check_ignore.returncode == 0
    assert tracked_audio.stdout.strip() == ""
