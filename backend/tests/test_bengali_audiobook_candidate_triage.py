from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from scripts.triage_bengali_audiobook_candidates import (
    RELEASE_HOLD,
    ensure_internal_path,
    load_candidates,
    ranked_candidates,
    repair_vtt_text,
    run_triage,
)


ROOT = Path.cwd()
TRIAGE_DIR = ROOT / "internal" / "audiobook_lab" / "pytest_bengali_candidate_triage"


@pytest.fixture(autouse=True)
def cleanup_triage_dir():
    if TRIAGE_DIR.exists():
        shutil.rmtree(TRIAGE_DIR)
    yield
    if TRIAGE_DIR.exists():
        shutil.rmtree(TRIAGE_DIR)


def write_tiny_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    duration_seconds = 1
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate * duration_seconds):
            value = int(16000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def write_candidate(
    slug: str,
    *,
    objective: float,
    sync: float,
    missing: list[str] | None = None,
    duration: float = 1200.0,
) -> Path:
    candidate_dir = TRIAGE_DIR / slug
    candidate_dir.mkdir(parents=True, exist_ok=True)
    source_audio = candidate_dir / "source_internal.wav"
    write_tiny_wav(source_audio)
    source_vtt = candidate_dir / "source_highlight.vtt"
    source_vtt.write_text(
        "WEBVTT\n\n"
        "1\n00:00:01.000 --> 00:00:01.200\nদ্বিতীয়\n\n"
        "2\n00:00:00.000 --> 00:00:00.500\nপ্রথম\n",
        encoding="utf-8",
    )
    source_timestamps = candidate_dir / "source_timestamps.json"
    source_timestamps.write_text(json.dumps([{"word": "প্রথম", "start_ms": 0, "end_ms": 500}], ensure_ascii=False) + "\n")

    blocker_list = [
        "objective_audio_score_9_5",
        "sync_usability_score_9_5",
        "bengali_human_listening_qa_9_5",
        "accessibility_listening_qa_9_5",
        "source_text_rights_evidence_exists",
        "derivative_audiobook_rights_evidence_exists",
        "owner_approval_exists",
        "legal_internal_review_exists",
        "rollback_plan_exists",
    ]
    write_json(
        candidate_dir / "source_inventory.json",
        {
            "candidate_slug": slug,
            "missing_required_files": missing or [],
            "audio_files": [str(source_audio)],
            "sidecar_files": [str(source_vtt), str(source_timestamps)],
            "files": [
                {
                    "category": "audio",
                    "source_path": str(source_audio),
                    "size_bytes": source_audio.stat().st_size,
                    "sha256": "audio-hash",
                },
                {"category": "sidecar", "source_path": str(source_vtt), "sha256": "vtt-hash"},
                {"category": "sidecar", "source_path": str(source_timestamps), "sha256": "json-hash"},
            ],
        },
    )
    write_json(
        candidate_dir / "objective_audio_analysis.json",
        {
            "candidate_slug": slug,
            "objective_audio_score": objective,
            "duration_seconds": duration,
            "ffprobe_status": "PASS",
        },
    )
    write_json(
        candidate_dir / "sidecar_integrity_report.json",
        {"candidate_slug": slug, "sync_usability_score": sync, "sidecar_integrity_status": "REVIEW_REQUIRED"},
    )
    write_json(
        candidate_dir / "highlight_sync_usability_report.json",
        {"candidate_slug": slug, "sync_usability_score": sync, "sync_status": "HOLD_SYNC_QA_REQUIRED"},
    )
    write_json(
        candidate_dir / "release_gate_report.json",
        {
            "candidate_slug": slug,
            "release_status": RELEASE_HOLD,
            "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
            "production_approved": False,
            "blockers": blocker_list,
            "gates": {
                "objective_audio_score_9_5": objective >= 9.5,
                "sync_usability_score_9_5": sync >= 9.5,
                "bengali_human_listening_qa_9_5": False,
                "accessibility_listening_qa_9_5": False,
                "source_text_rights_evidence_exists": False,
                "derivative_audiobook_rights_evidence_exists": False,
                "owner_approval_exists": False,
                "legal_internal_review_exists": False,
                "rollback_plan_exists": False,
                "no_frontend_public_or_build_audio": True,
            },
        },
    )
    write_json(
        candidate_dir / "normalized_metadata.json",
        {
            "candidate_slug": slug,
            "title": f"Title {slug}",
            "author": "Author",
            "duration_seconds": duration,
            "chapter_count": 1,
            "narrator_or_model_source": "internal",
        },
    )
    return candidate_dir


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_candidates_are_ranked_deterministically():
    write_candidate("candidate-c", objective=8.8, sync=6.0)
    write_candidate("candidate-a", objective=8.8, sync=8.0)
    write_candidate("candidate-b", objective=8.8, sync=8.0)

    first = ranked_candidates(load_candidates(TRIAGE_DIR))
    second = ranked_candidates(load_candidates(TRIAGE_DIR))

    assert first == second
    assert [row["candidate_slug"] for row in first[:3]] == ["candidate-a", "candidate-b", "candidate-c"]


def test_top_n_selection_writes_expected_packets():
    for index, sync in enumerate([8.0, 7.5, 7.0, 6.5], start=1):
        write_candidate(f"candidate-{index}", objective=8.8, sync=sync)

    summary = run_triage(TRIAGE_DIR, mode="triage", limit=2, write_root_reports=False)

    assert summary["total_candidates_ranked"] == 4
    assert [row["candidate_slug"] for row in summary["top_candidates"]] == ["candidate-1", "candidate-2"]
    assert (TRIAGE_DIR / "candidate-1" / "triage_decision.json").exists()
    assert (TRIAGE_DIR / "candidate-1" / "human_review_packet.md").exists()
    assert (TRIAGE_DIR / "candidate-1" / "remaster_plan.md").exists()
    decision = json.loads((TRIAGE_DIR / "candidate-1" / "triage_decision.json").read_text(encoding="utf-8"))
    assert decision["release_status"] == RELEASE_HOLD
    assert decision["release_path"]["ready_for_public_release_candidate"] is False
    assert decision["release_path"]["gates"]["bengali_human_listening_qa_9_5"] is False


def test_public_and_build_paths_are_rejected():
    with pytest.raises(ValueError):
        ensure_internal_path(ROOT / "frontend" / "public" / "bad.mp3")
    with pytest.raises(ValueError):
        ensure_internal_path(ROOT / "frontend" / "build" / "bad.mp3")


def test_sync_repairs_do_not_invent_content():
    dirty = (
        "WEBVTT\n\n"
        "1\n00:00:02.000 --> 00:00:02.500\nদ্বিতীয়\n\n"
        "2\n00:00:00.000 --> 00:00:00.500\nপ্রথম\n\n"
        "3\n00:00:03.000 --> 00:00:03.200\n\n"
    )

    repaired, details = repair_vtt_text(dirty)

    assert "প্রথম" in repaired
    assert "দ্বিতীয়" in repaired
    assert details["content_invented"] is False
    assert details["cue_content_preserved"] is True
    assert repaired.index("প্রথম") < repaired.index("দ্বিতীয়")


def test_remaster_outputs_stay_internal_original_is_preserved_and_audio_is_ignored():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required for remaster output test")
    candidate_dir = write_candidate("candidate-remaster", objective=8.8, sync=8.0)
    source_audio = candidate_dir / "source_internal.wav"
    before_bytes = source_audio.read_bytes()

    summary = run_triage(TRIAGE_DIR, mode="remaster-top", limit=1, write_root_reports=False)
    remaster = summary["remaster_results"]["candidate-remaster"]

    assert remaster["status"] == "INTERNAL_REMASTER_REVIEW_COPY_CREATED"
    output_path = ROOT / remaster["output_path"]
    assert output_path.exists()
    assert str(output_path).startswith(str(ROOT / "internal" / "audiobook_lab"))
    assert not str(output_path).startswith(str(ROOT / "frontend" / "public"))
    assert not str(output_path).startswith(str(ROOT / "frontend" / "build"))
    assert source_audio.read_bytes() == before_bytes
    check_ignore = subprocess.run(["git", "check-ignore", str(output_path)], check=False, capture_output=True, text=True)
    assert check_ignore.returncode == 0


def test_no_listen_now_or_audio_object_metadata_is_introduced():
    write_candidate("candidate-safe", objective=8.8, sync=8.0)

    run_triage(TRIAGE_DIR, mode="triage", limit=1, write_root_reports=False)

    generated = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (TRIAGE_DIR / "candidate-safe").glob("*")
        if path.is_file() and path.suffix in {".md", ".json"}
    )
    assert "Listen Now" not in generated
    assert "AudioObject" not in generated
    decision = json.loads((TRIAGE_DIR / "candidate-safe" / "triage_decision.json").read_text(encoding="utf-8"))
    assert decision["release_path"]["ready_for_public_release_candidate"] is False
