#!/usr/bin/env python3
"""Run bounded ASR and listening QA for the private Stage 2C audio."""

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
HOOK = ROOT / "internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py"
RUN_DIR = Path("/tmp/earnalism-a-ghost-stage2c-full-tts")
RESULT_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "a-ghost-story_stage2c_full_qa_runtime.json"
)
HOLDER = "sprint1_publication_stage2c"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "10",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "10",
    "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
}
STAGE2C_PRIOR_ESTIMATED_USD = 0.8411


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
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def ffprobe_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {completed.stderr.strip()}")
    return float(completed.stdout.strip())


def budget_estimate(
    duration_seconds: float,
    *,
    sample_count: int = 6,
    prior_estimated_usd: float = STAGE2C_PRIOR_ESTIMATED_USD,
) -> dict:
    asr_rate = float(os.environ["EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE"])
    asr_cap = float(os.environ["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"])
    retry_cap = float(os.environ["EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD"])
    qa_unit = float(os.environ["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
    qa_cap = float(os.environ["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"])
    total_cap = float(os.environ["MAX_TTS_BUDGET_USD"])
    title_cap = float(os.environ["SPRINT1_MAX_USD_PER_TITLE"])
    asr = round(duration_seconds / 60.0 * asr_rate, 4)
    qa = round(sample_count * qa_unit, 4)
    current = round(asr + qa, 4)
    cumulative = round(prior_estimated_usd + current, 4)
    blockers = []
    if asr > asr_cap:
        blockers.append(f"ASR estimate ${asr:.4f} exceeds ASR cap ${asr_cap:.4f}")
    if asr > retry_cap:
        blockers.append(f"ASR estimate ${asr:.4f} exceeds retry cap ${retry_cap:.4f}")
    if qa > qa_cap:
        blockers.append(f"Listening-QA estimate ${qa:.4f} exceeds QA cap ${qa_cap:.4f}")
    if cumulative > title_cap:
        blockers.append(f"A Ghost Story cumulative estimate ${cumulative:.4f} exceeds title cap ${title_cap:.4f}")
    if cumulative > total_cap:
        blockers.append(f"Cumulative estimate ${cumulative:.4f} exceeds sprint cap ${total_cap:.4f}")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "duration_seconds": round(duration_seconds, 3),
        "sample_count": sample_count,
        "estimated_asr_usd": asr,
        "estimated_listening_qa_usd": qa,
        "estimated_current_run_usd": current,
        "estimated_stage2b_and_stage2c_cumulative_usd": cumulative,
        "blockers": blockers,
    }


def acquired_lock_payload(lock: dict, estimate: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story Stage 2C private replacement audio only; bounded Whisper ASR/source validation "
                "and six-sample OpenAI listening QA; no TTS, upload, publication, frontend exposure, or "
                "release-gate mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "estimated_run_cost_usd": estimate["estimated_current_run_usd"],
            "stop_conditions": [
                "Any runtime gate or OPENAI_API_KEY is missing",
                "ASR or listening-QA estimate exceeds its cap",
                "The private TTS result or audio artifact is missing",
                "The same audio/model already has a completed provider attempt",
                "Any upload, publication, frontend exposure, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def full_tts_evidence(run_dir: Path) -> tuple[dict, Path]:
    result_path = run_dir / "tts_hook_result.json"
    if not result_path.is_file():
        raise RuntimeError("Stage 2C TTS hook evidence is missing")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "PASS":
        raise RuntimeError("Stage 2C TTS hook is not PASS")
    metrics = result.get("metrics") or {}
    if metrics.get("fallback_tts_used") is not False or metrics.get("audio_regenerated") is not True:
        raise RuntimeError("Stage 2C TTS provenance is not release-safe")
    if metrics.get("voice") != "verse" or metrics.get("profile") != "mystery_suspense_narrator":
        raise RuntimeError("Stage 2C TTS voice/profile changed")
    audio_value = (result.get("artifacts") or {}).get("final_audio_path") or ""
    audio = Path(audio_value)
    if not audio.is_file() or audio.stat().st_size <= 0:
        raise RuntimeError("Stage 2C final audio is missing or empty")
    return result, audio


def completed_attempt_blocker(audio_hash: str) -> str:
    if not RESULT_PATH.is_file():
        return ""
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result.get("audio_hash") == audio_hash and result.get("provider_calls_ran") is True:
        return "REPEAT_FULL_QA_ATTEMPT_BLOCKED: this audio hash already reached the ASR/listening providers"
    return ""


def verifier_repair_retry_allowed(run_dir: Path, audio_hash: str) -> tuple[bool, str]:
    if not RESULT_PATH.is_file():
        return False, "Prior full-QA runtime evidence is missing"
    prior = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if prior.get("audio_hash") != audio_hash or prior.get("provider_calls_ran") is not True:
        return False, "Prior full-QA evidence does not bind this audio hash"
    if prior.get("hook_blockers") != ["ASR last narrated words do not match the manuscript ending."]:
        return False, "Prior blocker was not the repaired boundary-verifier case"
    if (run_dir / "asr_provider_checkpoint.json").exists():
        return False, "An ASR provider checkpoint already exists; use checkpoint resume instead"
    transcript_path = run_dir / "asr_transcript.txt"
    manuscript_path = run_dir / "clean_manuscript.txt"
    if not transcript_path.is_file() or not manuscript_path.is_file():
        return False, "Saved transcript or manuscript is missing"
    sys.path.insert(0, str(ROOT / "internal/audiobook_lab/scripts/factory_hooks"))
    from asr_sync_hook import transcript_similarity  # noqa: PLC0415

    metrics = transcript_similarity(
        manuscript_path.read_text(encoding="utf-8"),
        transcript_path.read_text(encoding="utf-8"),
    )
    if float(metrics.get("score") or 0) < 9.7 or not metrics.get("first_words_match") or not metrics.get("last_words_match"):
        return False, "Saved transcript does not pass the repaired verifier"
    return True, "BOUNDARY_VERIFIER_REPAIR_CONFIRMED"


def hook_command(run_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(HOOK),
        "--slug",
        "a-ghost-story",
        "--run-dir",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    parser.add_argument("--asset-root", default=os.environ.get("EARNALISM_STAGE2C_ASSET_ROOT", str(ROOT)))
    parser.add_argument("--prior-estimated-usd", type=float, default=STAGE2C_PRIOR_ESTIMATED_USD)
    parser.add_argument("--resume-after-verifier-repair", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    run_dir = Path(args.run_dir).expanduser().resolve()
    _, audio = full_tts_evidence(run_dir)
    audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
    repeat = completed_attempt_blocker(audio_hash)
    retry_reason = ""
    if repeat:
        retry_allowed, retry_reason = verifier_repair_retry_allowed(run_dir, audio_hash)
        if not args.resume_after_verifier_repair or not retry_allowed:
            print(
                json.dumps(
                    {
                        "status": "BLOCKED_REPEAT_ATTEMPT",
                        "blocker": repeat,
                        "verifier_repair_retry_allowed": retry_allowed,
                        "verifier_repair_reason": retry_reason,
                    },
                    indent=2,
                )
            )
            return 4
    estimate = budget_estimate(
        ffprobe_duration(audio),
        prior_estimated_usd=args.prior_estimated_usd,
    )
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3
    asset_root = Path(args.asset_root).expanduser().resolve()
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    preflight = {
        "status": "PASS",
        "owner_decision": "AUTHORIZE_STAGE_2C_A_GHOST_STORY_AUDIO_REPAIR_AND_PUBLICATION_IF_QUALITY_10_TARGET_PASSES",
        "slug": "a-ghost-story",
        "audio_path": str(audio),
        "audio_hash": audio_hash,
        "audio_size_bytes": audio.stat().st_size,
        "asr_provider": "openai",
        "asr_model": os.environ.get("EARNALISM_FACTORY_ASR_MODEL", "whisper-1"),
        "listening_qa_model": os.environ["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
        "resume_after_verifier_repair": bool(args.resume_after_verifier_repair),
        "verifier_repair_reason": retry_reason or None,
        **estimate,
        "provider_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    process: subprocess.CompletedProcess | None = None
    error = ""
    started_at = iso_now()
    try:
        atomic_write(
            lock_path,
            json.dumps(acquired_lock_payload(lock, estimate), ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
        )
        process = subprocess.run(hook_command(run_dir), cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    hook_path = run_dir / "asr_sync_hook_result.json"
    hook = json.loads(hook_path.read_text(encoding="utf-8")) if hook_path.is_file() else {}
    diagnosis_path = run_dir / "asr_alignment_diagnosis.json"
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8")) if diagnosis_path.is_file() else {}
    listening_path = run_dir / "listening_quality_report.json"
    listening = json.loads(listening_path.read_text(encoding="utf-8")) if listening_path.is_file() else {}
    listening_quality = listening.get("listening_quality") or {}
    hook_status = str(hook.get("status") or "MISSING")
    runtime = {
        **preflight,
        "status": "FULL_RELEASE_QA_PASS" if hook_status == "PASS" else "FULL_RELEASE_QA_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": process is not None,
        "process_returncode": process.returncode if process else None,
        "hook_status": hook_status,
        "hook_blocker_category": hook.get("blocker_category"),
        "hook_blockers": hook.get("blockers") or [],
        "asr_source_score": diagnosis.get("score"),
        "first_words_match": diagnosis.get("first_words_match"),
        "last_words_match": diagnosis.get("last_words_match"),
        "listening_qa_status": listening_quality.get("status", "NOT_RUN"),
        "listening_qa_samples": listening_quality.get("samples") or [],
        "listening_qa_scores": (hook.get("metrics") or {}).get("audio_quality_scores") or {},
        "actual_provider_billing": "NOT_REPORTED",
        "error": error or None,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if hook_status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
