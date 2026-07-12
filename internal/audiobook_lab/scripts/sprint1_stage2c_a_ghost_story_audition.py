#!/usr/bin/env python3
"""Run one bounded new-voice audition for A Ghost Story's failed passage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]

from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    LISTENING_THRESHOLDS,
    evaluate_listening_evidence,
    judge_audio_sample_with_openai,
    openai_listening_qa_budget_guard,
)
from common import ffprobe_duration, sha256_file, sha256_text  # noqa: E402
from tts_hook import estimated_tts_cost_usd, profile_instructions, speech_create  # noqa: E402


EXPECTED_SOURCE_SHA256 = "0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_PAID_OPENAI_TTS": "true",
    "EARNALISM_TTS_MAX_ESTIMATED_USD": "1",
    "EARNALISM_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.015",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
}
HOLDER = "sprint1_publication_stage2c"
RESULT_DIR = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs"
)


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


def acquired_lock_payload(lock: dict, *, voice: str, profile: str, estimate: float) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                f"A Ghost Story failed-middle representative audition only; OpenAI {voice}/{profile}; "
                f"estimated TTS plus QA {estimate:.4f} USD; no full TTS, ASR, upload, publication, or release mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any paid gate or OPENAI_API_KEY is missing",
                "Source hash or passage extraction changes",
                "Estimated TTS plus QA exceeds configured caps",
                "The same text/model/voice/profile attempt already completed",
                "Any full TTS, ASR, upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def extract_passage(manuscript: str) -> str:
    start_marker = "Then I heard the rustle"
    end_marker = "fascinated eyes."
    start = manuscript.index(start_marker)
    end = manuscript.index(end_marker, start) + len(end_marker)
    return " ".join(manuscript[start:end].split())


def attempt_fingerprint(*, text: str, model: str, voice: str, profile: str) -> str:
    payload = json.dumps(
        {
            "text_hash": sha256_text(text),
            "model": model,
            "voice": voice,
            "profile": profile,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result_path(voice: str, profile: str) -> Path:
    safe_voice = "".join(char if char.isalnum() or char in "-_" else "-" for char in voice)
    safe_profile = "".join(char if char.isalnum() or char in "-_" else "-" for char in profile)
    return RESULT_DIR / f"a-ghost-story_stage2c_middle_audition_{safe_voice}_{safe_profile}.json"


def completed_attempt_exists(fingerprint: str) -> bool:
    candidates = [*RESULT_DIR.glob("a-ghost-story_stage2c_middle_audition_*.json")]
    legacy = RESULT_DIR / "a-ghost-story_stage2c_middle_audition_runtime.json"
    if legacy.exists():
        candidates.append(legacy)
    for path in candidates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("attempt_fingerprint") == fingerprint and payload.get("provider_calls_ran") is True:
            return True
    return False


def audition_pass(judgment: dict) -> tuple[bool, list[str]]:
    scores = judgment.get("scores") if isinstance(judgment.get("scores"), dict) else {}
    flags = judgment.get("judge_flags") if isinstance(judgment.get("judge_flags"), dict) else {}
    passed, blockers, _ = evaluate_listening_evidence(scores, flags, language="eng")
    if judgment.get("frontmatter_present") is True:
        blockers.append("AUDIO_LISTENING_QUALITY_FAILED: frontmatter present in audition.")
    if judgment.get("blocker_reason"):
        blockers.append(str(judgment["blocker_reason"]))
    return passed and not blockers, sorted(set(blockers))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-root",
        default=os.environ.get("EARNALISM_STAGE2C_ASSET_ROOT", str(ROOT)),
    )
    parser.add_argument("--voice", default="verse")
    parser.add_argument("--profile", default="mystery_suspense_narrator")
    parser.add_argument(
        "--output-dir",
        default="/tmp/earnalism-a-ghost-stage2c-middle-repair/auditions",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    if args.profile not in {"classic_literary_narrator", "mystery_suspense_narrator"}:
        print(json.dumps({"status": "BLOCKED_PROFILE", "profile": args.profile}, indent=2))
        return 2

    asset_root = Path(args.asset_root).expanduser().resolve()
    manuscript_path = (
        asset_root
        / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt"
    )
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    if not manuscript_path.is_file() or not lock_path.is_file():
        raise RuntimeError("Stage 2C manuscript or paid lock is missing")
    manuscript = manuscript_path.read_text(encoding="utf-8")
    if sha256_text(manuscript) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("A Ghost Story source hash changed; refusing paid audition")
    passage = extract_passage(manuscript)
    if len(passage) != 956 or len(passage.split()) != 183:
        raise RuntimeError("A Ghost Story audition passage changed")

    tts_estimate = estimated_tts_cost_usd(passage)
    qa_budget = openai_listening_qa_budget_guard(sample_count=1, prior_estimated_usd=tts_estimate)
    if not qa_budget.get("ok"):
        print(json.dumps({"status": "BLOCKED_BUDGET", "budget": qa_budget}, indent=2))
        return 2
    combined_estimate = round(tts_estimate + float(qa_budget["estimated_qa_cost_usd"]), 4)
    if combined_estimate > float(os.environ["EARNALISM_TTS_MAX_ESTIMATED_USD"]):
        print(json.dumps({"status": "BLOCKED_PER_TITLE_BUDGET", "estimated_usd": combined_estimate}, indent=2))
        return 2

    fingerprint = attempt_fingerprint(
        text=passage,
        model=os.environ.get("EARNALISM_FACTORY_TTS_MODEL", "gpt-4o-mini-tts"),
        voice=args.voice,
        profile=args.profile,
    )
    if completed_attempt_exists(fingerprint):
        print(json.dumps({"status": "BLOCKED_REPEAT_ATTEMPT", "attempt_fingerprint": fingerprint}, indent=2))
        return 4

    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    passage_path = output_dir / "middle_source.txt"
    passage_path.write_text(passage + "\n", encoding="utf-8")
    audio_path = output_dir / f"{args.voice}_{args.profile}.mp3"
    preflight = {
        "status": "PASS",
        "owner_decision": "AUTHORIZE_STAGE_2C_A_GHOST_STORY_AUDIO_REPAIR_AND_PUBLICATION_IF_QUALITY_10_TARGET_PASSES",
        "slug": "a-ghost-story",
        "provider": "openai",
        "model": os.environ.get("EARNALISM_FACTORY_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": args.voice,
        "profile": args.profile,
        "passage_chars": len(passage),
        "passage_words": len(passage.split()),
        "passage_hash": sha256_text(passage),
        "attempt_fingerprint": fingerprint,
        "estimated_tts_usd": tts_estimate,
        "estimated_listening_qa_usd": qa_budget["estimated_qa_cost_usd"],
        "estimated_total_usd": combined_estimate,
        "provider_calls_ran": False,
        "full_tts_ran": False,
        "asr_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    from openai import OpenAI  # noqa: PLC0415

    class JudgeArgs:
        slug = "a-ghost-story"
        title = "A Ghost Story"
        author = "Mark Twain"
        language = "eng"

    judgment: dict = {}
    error = ""
    provider_calls_ran = False
    started_at = iso_now()
    try:
        atomic_write(
            lock_path,
            json.dumps(
                acquired_lock_payload(lock, voice=args.voice, profile=args.profile, estimate=combined_estimate),
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            + b"\n",
        )
        client = OpenAI()
        provider_calls_ran = True
        speech_create(
            client,
            voice=args.voice,
            instructions=profile_instructions("eng", args.profile),
            text=passage,
            out_path=audio_path,
        )
        duration = ffprobe_duration(audio_path)
        if not audio_path.is_file() or audio_path.stat().st_size <= 0 or not duration:
            raise RuntimeError("OpenAI audition audio is missing or invalid")
        sample = {
            "sample_label": "middle_repair_audition",
            "start_time": 0.0,
            "duration": duration,
            "sample_audio_path": str(audio_path),
            "sample_audio_hash": sha256_file(audio_path),
            "source_text_hash": sha256_text(passage),
        }
        judgment = judge_audio_sample_with_openai(client, JudgeArgs(), sample)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    passed, blockers = audition_pass(judgment) if judgment else (False, [error or "AUDITION_NOT_RUN"])
    runtime = {
        **preflight,
        "status": "AUDITION_PASS" if passed else "AUDITION_REPAIR_REQUIRED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "actual_provider_billing": "NOT_REPORTED",
        "audio_path": str(audio_path) if audio_path.exists() else "",
        "audio_size_bytes": audio_path.stat().st_size if audio_path.exists() else 0,
        "audio_duration_seconds": ffprobe_duration(audio_path) if audio_path.exists() else None,
        "scores": judgment.get("scores", {}),
        "confidence": judgment.get("confidence", 0.0),
        "fatal_flags": [
            field
            for field in BINARY_LISTENING_FLAGS
            if bool((judgment.get("judge_flags") or {}).get(field))
        ],
        "notes": judgment.get("notes", ""),
        "blockers": blockers,
        "error": error or None,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
    }
    atomic_write(
        result_path(args.voice, args.profile),
        json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
    )
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
