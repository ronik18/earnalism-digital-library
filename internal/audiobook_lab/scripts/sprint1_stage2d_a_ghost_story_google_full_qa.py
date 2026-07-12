#!/usr/bin/env python3
"""Run bounded full release QA for the private Stage 2D Google candidate."""

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
RUN_DIR = Path("/tmp/earnalism-a-ghost-stage2d-google-full-tts")
TTS_RESULT_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_full_tts_runtime.json"
RESULT_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_full_qa_runtime.json"
HOLDER = "sprint1_publication_stage2d"
PRIOR_ESTIMATED_SPEND_USD = 3.2153
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
    "EARNALISM_LISTENING_POLICY_VERSION": "tiered_audiobook_acceptance_v1",
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
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: dict, estimate: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story Stage 2D private Google candidate only; bounded OpenAI ASR and six-sample "
                f"listening QA; estimated {estimate['estimated_current_qa_usd']:.4f} USD; no upload, publication, or release mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any runtime gate or OPENAI_API_KEY is missing",
                "Google TTS evidence or audio hash changes",
                "ASR or listening QA estimate exceeds its cap",
                "The same audio hash already reached full QA providers",
                "Any upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def full_tts_evidence() -> tuple[dict, Path]:
    evidence = json.loads(TTS_RESULT_PATH.read_text(encoding="utf-8"))
    if evidence.get("status") != "FULL_TTS_PASS_QA_PENDING":
        raise RuntimeError("Stage 2D full TTS evidence is not ready for QA")
    if evidence.get("provider") != "google" or evidence.get("voice") != "en-GB-Studio-C":
        raise RuntimeError("Stage 2D provider/voice changed")
    if evidence.get("prosody") != "source_preserving_ssml_88_percent":
        raise RuntimeError("Stage 2D prosody evidence changed")
    audio = Path(str(evidence.get("final_audio_path") or ""))
    if not audio.is_file() or audio.stat().st_size <= 0:
        raise RuntimeError("Stage 2D final audio is missing")
    if evidence.get("final_audio_hash") != hashlib.sha256(audio.read_bytes()).hexdigest():
        raise RuntimeError("Stage 2D final audio hash changed")
    return evidence, audio


def budget_estimate(duration_seconds: float) -> dict:
    asr = round(duration_seconds / 60.0 * float(os.environ["EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE"]), 4)
    qa = round(6 * float(os.environ["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"]), 4)
    current = round(asr + qa, 4)
    cumulative = round(PRIOR_ESTIMATED_SPEND_USD + current, 4)
    blockers = []
    if asr > float(os.environ["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"]):
        blockers.append("ASR estimate exceeds its cap")
    if asr > float(os.environ["EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD"]):
        blockers.append("ASR estimate exceeds its retry cap")
    if qa > float(os.environ["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"]):
        blockers.append("Listening QA estimate exceeds its cap")
    if cumulative > float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]):
        blockers.append("A Ghost Story cumulative estimate exceeds the per-title cap")
    if cumulative > float(os.environ["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]):
        blockers.append("Cumulative estimate exceeds the sprint cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_asr_usd": asr,
        "estimated_listening_qa_usd": qa,
        "estimated_current_qa_usd": current,
        "estimated_stage2b_through_full_qa_usd": cumulative,
        "blockers": blockers,
    }


def owner_listening_gate(samples: list[dict]) -> dict:
    scores = [float((item.get("scores") or {}).get("overall_listening_score") or 0) for item in samples]
    confidences = [float((item.get("scores") or {}).get("confidence_score") or item.get("confidence") or 0) for item in samples]
    fatal_fields = {
        "robotic_texture_detected",
        "mechanical_cadence_detected",
        "choppy_joins_detected",
        "fallback_tts_detected",
        "list_reading_rhythm_detected",
        "repeated_identical_sentence_endings_detected",
        "abrupt_tts_resets_detected",
        "placeholder_audio_detected",
    }
    fatal = sorted({field for item in samples for field in fatal_fields if (item.get("judge_flags") or {}).get(field)})
    minimum_score = min(scores) if scores else 0.0
    minimum_confidence = min(confidences) if confidences else 0.0
    return {
        "passes": len(samples) >= 6 and minimum_score >= 9.4 and minimum_confidence >= 0.9 and not fatal,
        "sample_count": len(samples),
        "minimum_overall_score": minimum_score,
        "minimum_confidence": minimum_confidence,
        "fatal_flags": fatal,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", default=os.environ.get("EARNALISM_STAGE2D_ASSET_ROOT", str(ROOT)))
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    tts, audio = full_tts_evidence()
    run_dir = Path(args.run_dir).expanduser().resolve()
    if run_dir != audio.parent:
        raise RuntimeError("QA run directory does not own the Stage 2D audio")
    audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
    if RESULT_PATH.exists():
        prior = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if prior.get("audio_hash") == audio_hash and prior.get("provider_calls_ran") is True:
            print(json.dumps({"status": "BLOCKED_REPEAT_FULL_QA", "audio_hash": audio_hash}, indent=2))
            return 4
    estimate = budget_estimate(float(tts["final_audio_duration_seconds"]))
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3
    asset_root = Path(args.asset_root).expanduser().resolve()
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    preflight = {
        "status": "PASS",
        "owner_decision": "AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS",
        "slug": "a-ghost-story",
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "prosody": "source_preserving_ssml_88_percent",
        "audio_path": str(audio),
        "audio_hash": audio_hash,
        "audio_size_bytes": audio.stat().st_size,
        "audio_duration_seconds": tts["final_audio_duration_seconds"],
        "listening_policy": os.environ["EARNALISM_LISTENING_POLICY_VERSION"],
        **estimate,
        "provider_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    command = [
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
    process: subprocess.CompletedProcess | None = None
    error = ""
    started_at = iso_now()
    try:
        atomic_write(lock_path, json.dumps(acquired_lock_payload(lock, estimate), indent=2).encode("utf-8") + b"\n")
        process = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    hook_path = run_dir / "asr_sync_hook_result.json"
    hook = json.loads(hook_path.read_text(encoding="utf-8")) if hook_path.exists() else {}
    diagnosis_path = run_dir / "asr_alignment_diagnosis.json"
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8")) if diagnosis_path.exists() else {}
    listening_path = run_dir / "listening_quality_report.json"
    listening = json.loads(listening_path.read_text(encoding="utf-8")) if listening_path.exists() else {}
    samples = ((listening.get("listening_quality") or {}).get("samples") or [])
    owner_gate = owner_listening_gate(samples)
    objective_pass = (
        float(diagnosis.get("score") or 0) >= 9.7
        and diagnosis.get("first_words_match") is True
        and diagnosis.get("last_words_match") is True
        and owner_gate["passes"]
        and hook.get("status") == "PASS"
    )
    runtime = {
        **preflight,
        "status": "FULL_RELEASE_QA_PASS" if objective_pass else "FULL_RELEASE_QA_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": process is not None,
        "process_returncode": process.returncode if process else None,
        "hook_status": hook.get("status", "MISSING"),
        "hook_blocker_category": hook.get("blocker_category"),
        "hook_blockers": hook.get("blockers") or [],
        "asr_source_score": diagnosis.get("score"),
        "first_words_match": diagnosis.get("first_words_match"),
        "last_words_match": diagnosis.get("last_words_match"),
        "owner_listening_gate": owner_gate,
        "listening_samples": samples,
        "error": error or None,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if objective_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
