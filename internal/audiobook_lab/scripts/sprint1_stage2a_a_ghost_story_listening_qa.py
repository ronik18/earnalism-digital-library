#!/usr/bin/env python3
"""Run only bounded A Ghost Story listening QA with paid-lock closeout."""

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
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
RUN_DIR = ROOT / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z"
AUDIO_PATH = (
    ROOT
    / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/a-ghost-story_existing_audio_candidate.mp3"
)
LOCK_PATH = ROOT / "internal/earnalism_intelligence/locks/paid_tts.lock"
RESULT_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2a_listening_qa_runtime.json"
)
HOLDER = "sprint1_publication_stage2a"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "10",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "10",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def runtime_gate_errors() -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if os.environ.get(name) != expected
    ]
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active":
        raise RuntimeError("paid_tts.lock must remain active")
    if payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock already has a holder")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty before bounded acquisition")
    return payload


def verified_sidecar_reuse() -> dict:
    sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]
    from asr_sync_hook import existing_sidecar_reuse  # noqa: PLC0415

    class Args:
        slug = "a-ghost-story"

    manuscript = (RUN_DIR / "clean_manuscript.txt").read_text(encoding="utf-8")
    result = existing_sidecar_reuse(Args(), RUN_DIR, {}, AUDIO_PATH, manuscript)
    if not result or result.get("status") != "PASS":
        raise RuntimeError("Hash-bound local ASR/sync evidence is not reusable; refusing paid listening QA")
    return result


def completed_attempt_blocker(audio_hash: str) -> str:
    report_path = RUN_DIR / "listening_quality_report.json"
    if not report_path.exists():
        return ""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    listening = report.get("listening_quality") if isinstance(report.get("listening_quality"), dict) else {}
    samples = listening.get("samples") if isinstance(listening.get("samples"), list) else []
    if (
        report.get("audio_hash") == audio_hash
        and listening.get("model_or_judge") == "openai:gpt-audio"
        and len(samples) >= 6
    ):
        return "REPEAT_QA_ATTEMPT_BLOCKED: the same audio hash/model already has a completed six-sample QA result"
    return ""


def acquired_lock_payload(lock: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story existing-audio schema-3 listening QA only; total cap 175 USD, "
                "per-title cap 30 USD, listening-QA cap 2 USD; no ASR, TTS, upload, publication, "
                "frontend exposure, or release-gate mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any required runtime gate or OPENAI_API_KEY is missing",
                "Hash-bound local sidecar validation fails",
                "Listening-QA budget guard blocks",
                "The same audio hash/model already has completed QA evidence",
                "Any ASR, TTS, upload, publication, or public release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def hook_command() -> list[str]:
    return [
        sys.executable,
        str(HOOK_DIR / "asr_sync_hook.py"),
        "--slug",
        "a-ghost-story",
        "--run-dir",
        str(RUN_DIR),
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
        "--resume",
        "--fail-closed",
    ]


def hook_exit_code(process_returncode: int, hook_status: str) -> int:
    if process_returncode != 0:
        return process_returncode
    return 0 if hook_status == "PASS" else 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate gates, lock, and reuse evidence only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2

    original_lock = LOCK_PATH.read_bytes()
    lock = load_lock(original_lock)
    reuse = verified_sidecar_reuse()
    repeat_blocker = completed_attempt_blocker(str(reuse.get("final_audio_hash") or ""))
    preflight = {
        "status": "PASS",
        "slug": "a-ghost-story",
        "holder": HOLDER,
        "lock_sha256": hashlib.sha256(original_lock).hexdigest(),
        "reuse_source": reuse.get("reuse_source"),
        "audio_hash": reuse.get("final_audio_hash"),
        "transcript_match_score": reuse.get("transcript_match_score"),
        "sync_score": reuse.get("sync_score"),
        "provider_calls_ran": False,
    }
    if repeat_blocker:
        print(json.dumps({**preflight, "status": "BLOCKED_REPEAT_ATTEMPT", "blocker": repeat_blocker}, indent=2))
        return 4
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    acquired = json.dumps(acquired_lock_payload(lock), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    process_result: subprocess.CompletedProcess | None = None
    try:
        atomic_write(LOCK_PATH, acquired)
        child_env = {**os.environ, "EARNALISM_LISTENING_QA_ONLY": "true"}
        process_result = subprocess.run(hook_command(), cwd=ROOT, env=child_env, check=False)
    finally:
        atomic_write(LOCK_PATH, original_lock)

    hook_result_path = RUN_DIR / "asr_sync_hook_result.json"
    hook_result = json.loads(hook_result_path.read_text(encoding="utf-8")) if hook_result_path.exists() else {}
    hook_status = str(hook_result.get("status") or "MISSING")
    runtime_result = {
        **preflight,
        "status": "LISTENING_QA_PASS" if hook_status == "PASS" else "LISTENING_QA_BLOCKED",
        "finished_at": iso_now(),
        "process_returncode": process_result.returncode if process_result else None,
        "hook_status": hook_status,
        "hook_blocker_category": hook_result.get("blocker_category"),
        "hook_blockers": hook_result.get("blockers") or [],
        "listening_quality_report": str((RUN_DIR / "listening_quality_report.json").relative_to(ROOT)),
        "lock_restored": LOCK_PATH.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest(),
    }
    atomic_write(
        RESULT_PATH,
        json.dumps(runtime_result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
    )
    return hook_exit_code(process_result.returncode if process_result else 1, hook_status)


if __name__ == "__main__":
    raise SystemExit(main())
