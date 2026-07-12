#!/usr/bin/env python3
"""Upload the approved Stage 2D A Ghost Story candidate, fail closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
UPLOAD_HOOK = ROOT / "internal/audiobook_lab/scripts/factory_hooks/upload_hook.py"
RUN_DIR = Path("/tmp/earnalism-a-ghost-stage2d-google-full-tts")
TTS_EVIDENCE = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_full_tts_runtime.json"
QA_EVIDENCE = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_full_qa_runtime.json"
RESULT_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_upload_runtime.json"
HOLDER = "sprint1_publication_stage2d"
EXPECTED_AUDIO_HASH = "c0e52985ee1e3e178b81d83157189251a667d64ecbc22bbc0940e6e4fc7bf904"
EXPECTED_SOURCE_HASH = "0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_STAGE2D_PUBLIC_UPLOAD": "true",
}
REQUIRED_STORAGE_ENV = (
    "B2_ACCESS_KEY_ID",
    "B2_SECRET_ACCESS_KEY",
    "B2_BUCKET",
    "B2_S3_ENDPOINT",
    "B2_REGION",
)
FATAL_FLAGS = {
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "list_reading_rhythm_detected",
    "repeated_identical_sentence_endings_detected",
    "abrupt_tts_resets_detected",
    "placeholder_audio_detected",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_gate_errors() -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if os.environ.get(name) != expected
    ]
    errors.extend(f"{name} is required" for name in REQUIRED_STORAGE_ENV if not os.environ.get(name))
    return errors


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story Stage 2D checksum-verified B2 upload only; no TTS, ASR, public source mutation, "
                "deployment, or unrelated title work."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any runtime gate or B2 credential is missing",
                "Audio, source, ASR, listening, or sidecar evidence changes",
                "Any remote checksum does not match",
                "Any public source mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def validate_release_evidence(run_dir: Path) -> dict:
    tts = read_json(TTS_EVIDENCE)
    qa = read_json(QA_EVIDENCE)
    hook = read_json(run_dir / "asr_sync_hook_result.json")
    meta = read_json(run_dir / "meta.json")
    timestamps = read_json(run_dir / "timestamps.json")
    audio = Path(str(tts.get("final_audio_path") or ""))
    blockers: list[str] = []

    if tts.get("status") != "FULL_TTS_PASS_QA_PENDING":
        blockers.append("Full TTS evidence is not PASS_QA_PENDING")
    if qa.get("status") != "FULL_RELEASE_QA_PASS":
        blockers.append("Full release QA evidence is not PASS")
    if not audio.is_file() or audio.stat().st_size <= 0:
        blockers.append("Final audio is missing or empty")
    else:
        actual_audio_hash = sha256_file(audio)
        if actual_audio_hash != EXPECTED_AUDIO_HASH or qa.get("audio_hash") != actual_audio_hash:
            blockers.append("Final audio hash does not match Stage 2D evidence")
    if tts.get("source_hash") != EXPECTED_SOURCE_HASH or meta.get("source_text_hash") != EXPECTED_SOURCE_HASH:
        blockers.append("Source hash does not match the approved manuscript")
    if float(qa.get("asr_source_score") or 0) < 9.7:
        blockers.append("ASR/source score is below 9.7")
    if qa.get("first_words_match") is not True or qa.get("last_words_match") is not True:
        blockers.append("First/last checks are not PASS")
    owner_gate = qa.get("owner_listening_gate") or {}
    if owner_gate.get("passes") is not True or int(owner_gate.get("sample_count") or 0) < 6:
        blockers.append("Owner listening gate is not PASS with six samples")
    if float(owner_gate.get("minimum_overall_score") or 0) < 9.4:
        blockers.append("A listening sample is below 9.4")
    if float(owner_gate.get("minimum_confidence") or 0) < 0.9:
        blockers.append("Listening confidence is below 0.9")
    samples = qa.get("listening_samples") or []
    fatal = sorted(
        {
            flag
            for sample in samples
            for flag in FATAL_FLAGS
            if (sample.get("judge_flags") or {}).get(flag) is True
        }
    )
    if fatal:
        blockers.append(f"Fatal listening flags present: {', '.join(fatal)}")
    if hook.get("status") != "PASS" or hook.get("ready_for_next_stage") is not True:
        blockers.append("ASR/sync hook is not ready for the next stage")
    if (hook.get("metrics") or {}).get("auto_estimated_sync") is not False:
        blockers.append("Sidecar timing is estimated rather than provider-aligned")
    if meta.get("audio_hash") != EXPECTED_AUDIO_HASH or timestamps.get("audio_hash") != EXPECTED_AUDIO_HASH:
        blockers.append("Sidecars are not bound to the approved audio hash")
    if timestamps.get("source_text_hash") != EXPECTED_SOURCE_HASH:
        blockers.append("Timestamps are not bound to the approved source hash")
    if not qa.get("lock_restored") or not tts.get("lock_restored"):
        blockers.append("A prior paid stage did not restore paid_tts.lock")

    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "slug": "a-ghost-story",
        "audio_path": str(audio),
        "audio_hash": EXPECTED_AUDIO_HASH,
        "source_hash": EXPECTED_SOURCE_HASH,
        "asr_source_score": qa.get("asr_source_score"),
        "first_words_match": qa.get("first_words_match"),
        "last_words_match": qa.get("last_words_match"),
        "listening_gate": owner_gate,
        "fatal_flags": fatal,
        "alignment_method": timestamps.get("alignment_method"),
        "auto_estimated_sync": timestamps.get("auto_estimated_sync"),
        "blockers": blockers,
    }


def preupload_qa(evidence: dict) -> dict:
    return {
        "slug": "a-ghost-story",
        "schema_version": 3,
        "decision": "PREUPLOAD_APPROVED",
        "auto_approval_decision": True,
        "owner_decision": "AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS",
        "approved_scope": "Checksum-verified upload only; public source release requires verified upload evidence.",
        "audio_public_release": "PENDING_VERIFIED_UPLOAD",
        "quality_target_claimed": "MEASURED_RELEASE_MINIMUM_PASS_NO_10_OF_10_CLAIM",
        "release_gates": {
            "source_rights": "PASS",
            "text_sanitation": "PASS",
            "full_book_tts": "PASS",
            "asr_source_alignment": "PASS",
            "first_words_match": "PASS",
            "last_words_match": "PASS",
            "listening_qa": "PASS",
            "manifest_validation": "PASS",
            "remote_upload_checksum": "PENDING",
            "endpoint_validation": "PENDING",
            "frontend_release_state": "PENDING",
            "production_route_validation": "PENDING",
        },
        "measured_evidence": evidence,
        "created_at": iso_now(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", required=True)
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    run_dir = Path(args.run_dir).expanduser().resolve()
    evidence = validate_release_evidence(run_dir)
    if evidence["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_RELEASE_EVIDENCE", **evidence}, indent=2))
        return 3
    if args.dry_run:
        print(json.dumps({**evidence, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    asset_root = Path(args.asset_root).expanduser().resolve()
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    atomic_write(run_dir / "auto_premium_qa.json", json.dumps(preupload_qa(evidence), indent=2).encode("utf-8") + b"\n")
    command = [
        sys.executable,
        str(UPLOAD_HOOK),
        "--slug",
        "a-ghost-story",
        "--run-dir",
        str(run_dir),
        "--catalog-run-dir",
        str(run_dir),
        "--manifest",
        str(ROOT / "book_import_manifest.json"),
        "--language",
        "eng",
        "--title",
        "A Ghost Story",
        "--author",
        "Mark Twain",
        "--max-attempts",
        "1",
        "--fail-closed",
    ]
    process: subprocess.CompletedProcess | None = None
    error = ""
    started_at = iso_now()
    try:
        atomic_write(lock_path, json.dumps(acquired_lock_payload(lock), indent=2).encode("utf-8") + b"\n")
        process = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    hook_result = read_json(run_dir / "upload_hook_result.json") if (run_dir / "upload_hook_result.json").exists() else {}
    upload_manifest = read_json(run_dir / "upload_manifest.json") if (run_dir / "upload_manifest.json").exists() else {}
    checks = upload_manifest.get("checksums") or {}
    required = {"mp3", "timestamps", "vtt", "chapters", "meta"}
    checksum_pass = required.issubset(checks) and all(
        checks[name].get("resolves") is True
        and checks[name].get("match") is True
        and int(checks[name].get("local_size") or 0) > 0
        for name in required
    )
    upload_pass = (
        process is not None
        and process.returncode == 0
        and hook_result.get("status") == "PASS"
        and upload_manifest.get("status") == "PASS"
        and checksum_pass
    )
    runtime = {
        "status": "VERIFIED_UPLOAD_PASS" if upload_pass else "VERIFIED_UPLOAD_BLOCKED",
        "slug": "a-ghost-story",
        "owner_decision": "AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS",
        "started_at": started_at,
        "finished_at": iso_now(),
        "release_evidence": evidence,
        "process_returncode": process.returncode if process else None,
        "hook_status": hook_result.get("status", "MISSING"),
        "hook_blockers": hook_result.get("blockers") or [],
        "storage_backend": upload_manifest.get("storage_backend"),
        "urls": upload_manifest.get("urls") or {},
        "checksums": checks,
        "error": error or None,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "public_source_mutated": False,
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, indent=2))
    return 0 if upload_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
