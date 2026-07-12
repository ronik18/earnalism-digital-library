#!/usr/bin/env python3
"""Run one bounded Google TTS audition for A Ghost Story."""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    LISTENING_THRESHOLDS,
    evaluate_listening_evidence,
    judge_audio_sample_with_openai,
)
from common import ffprobe_duration, sha256_file, sha256_text  # noqa: E402


OWNER_DECISION = "AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS"
EXPECTED_SOURCE_SHA256 = "0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4"
HOLDER = "sprint1_publication_stage2d"
SUPPORTED_VOICES = {"en-GB-Studio-B", "en-GB-Studio-C"}
PRIOR_ESTIMATED_SPEND_USD = 2.3295
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS": "true",
    "EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD": "1",
    "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.02",
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
    for name in ("OPENAI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"):
        if not os.environ.get(name):
            errors.append(f"{name} is required")
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


def acquired_lock_payload(lock: dict, *, voice: str, estimate: dict, prosody_repair: bool = False) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                f"A Ghost Story Stage 2D Google representative audition only; {voice}; three passages; "
                f"prosody repair {prosody_repair}; "
                f"estimated provider plus listening QA {estimate['estimated_current_usd']:.4f} USD; "
                "no full TTS, upload, publication, or release mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any runtime gate or provider credential is missing",
                "Voice is not in the capability-proven allowlist",
                "Estimated spend exceeds the Google, title, or sprint cap",
                "The same voice and passage fingerprint already reached providers",
                "Any full TTS, upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def flatten_source(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def source_passages(manuscript: str) -> list[dict]:
    flattened = flatten_source(manuscript)
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", flattened) if item.strip()]

    def compact(items: list[str], limit: int = 1000) -> str:
        selected: list[str] = []
        total = 0
        for sentence in items:
            if selected and total + len(sentence) + 1 > limit:
                break
            selected.append(sentence)
            total += len(sentence) + 1
        return " ".join(selected)

    middle_start = flattened.index("Then I heard the rustle")
    middle_end = flattened.index("fascinated eyes.", middle_start) + len("fascinated eyes.")
    passages = [
        {"passage_id": "opening", "text": compact(sentences)},
        {"passage_id": "failed_middle", "text": flattened[middle_start:middle_end]},
        {"passage_id": "ending", "text": compact(list(reversed(sentences)), 1000)},
    ]
    passages[2]["text"] = " ".join(reversed(re.split(r"(?<=[.!?])\s+", passages[2]["text"])))
    for passage in passages:
        passage["text"] = passage["text"].strip()
        passage["text_hash"] = sha256_text(passage["text"])
        passage["characters"] = len(passage["text"])
    return passages


def budget_estimate(passages: list[dict]) -> dict:
    tts_rate = float(os.environ["EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS"])
    qa_rate = float(os.environ["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
    tts = round(sum(item["characters"] for item in passages) / 1000.0 * tts_rate, 4)
    qa = round(len(passages) * qa_rate, 4)
    current = round(tts + qa, 4)
    cumulative = round(PRIOR_ESTIMATED_SPEND_USD + current, 4)
    blockers = []
    if current > float(os.environ["EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD"]):
        blockers.append("Google audition estimate exceeds its sub-cap")
    if qa > float(os.environ["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"]):
        blockers.append("Listening QA estimate exceeds its sub-cap")
    if cumulative > float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]):
        blockers.append("A Ghost Story cumulative estimate exceeds the per-title cap")
    if cumulative > float(os.environ["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]):
        blockers.append("Cumulative estimate exceeds the sprint cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_google_tts_usd": tts,
        "estimated_listening_qa_usd": qa,
        "estimated_current_usd": current,
        "estimated_stage2b_through_stage2d_usd": cumulative,
        "blockers": blockers,
    }


def attempt_fingerprint(*, voice: str, passages: list[dict], prosody_repair: bool = False) -> str:
    payload = json.dumps(
        {
            "provider": "google",
            "voice": voice,
            "passage_hashes": [item["text_hash"] for item in passages],
            "speaking_rate": 0.88 if prosody_repair else 0.94,
            "prosody_repair": prosody_repair,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audition_pass(judgments: list[dict]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    for judgment in judgments:
        scores = judgment.get("scores") if isinstance(judgment.get("scores"), dict) else {}
        flags = judgment.get("judge_flags") if isinstance(judgment.get("judge_flags"), dict) else {}
        passed, sample_blockers, _ = evaluate_listening_evidence(scores, flags, language="eng")
        if not passed:
            blockers.extend(f"{judgment.get('sample_label')}: {item}" for item in sample_blockers)
        if float(scores.get("overall_listening_score") or 0) < 9.4:
            blockers.append(f"{judgment.get('sample_label')}: overall score below owner minimum 9.4")
        if float(scores.get("confidence_score") or judgment.get("confidence") or 0) < 0.9:
            blockers.append(f"{judgment.get('sample_label')}: confidence below owner minimum 0.9")
        if judgment.get("blocker_reason"):
            blockers.append(f"{judgment.get('sample_label')}: {judgment['blocker_reason']}")
    return not blockers, sorted(set(blockers))


def result_path(voice: str, prosody_repair: bool = False) -> Path:
    safe = voice.lower().replace("-", "_")
    suffix = "_prosody_repair" if prosody_repair else ""
    return ROOT / "internal/audiobook_lab/sprint1_publication/title_runs" / f"a-ghost-story_stage2d_google_audition_{safe}{suffix}.json"


def source_preserving_ssml(text: str) -> str:
    pauses = {",": "180ms", ";": "260ms", ":": "240ms", ".": "360ms", "!": "360ms", "?": "360ms"}
    rendered: list[str] = []
    for token in re.split(r"([,;:.!?])", text):
        rendered.append(html.escape(token, quote=False))
        if token in pauses:
            rendered.append(f"<break time=\"{pauses[token]}\"/>")
    return f"<speak><prosody rate=\"88%\">{''.join(rendered)}</prosody></speak>"


def ffprobe_with_retry(path: Path, attempts: int = 3) -> float | None:
    for attempt in range(attempts):
        duration = ffprobe_duration(path)
        if duration:
            return duration
        if attempt + 1 < attempts:
            time.sleep(0.2)
    return None


def local_validation_retry_allowed(prior: dict, output_root: Path, voice: str) -> tuple[bool, str]:
    if prior.get("errors") != ["RuntimeError: Google returned invalid audio for opening"]:
        return False, "Prior blocker was not the exact repaired local validation case"
    if prior.get("judgments"):
        return False, "Prior attempt already reached listening QA"
    if prior.get("lock_restored") is not True:
        return False, "Prior attempt did not prove lock restoration"
    opening = output_root / voice / "opening.mp3"
    if not opening.is_file() or opening.stat().st_size <= 0 or not ffprobe_with_retry(opening):
        return False, "Prior opening artifact is not locally valid"
    return True, "VALID_OPENING_ARTIFACT_REUSE_AFTER_FFPROBE_REPAIR"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", required=True, choices=sorted(SUPPORTED_VOICES))
    parser.add_argument("--asset-root", default=os.environ.get("EARNALISM_STAGE2D_ASSET_ROOT", str(ROOT)))
    parser.add_argument("--output-root", default="/tmp/earnalism-a-ghost-stage2d-google-auditions")
    parser.add_argument("--resume-after-local-validation-repair", action="store_true")
    parser.add_argument("--prosody-repair", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    asset_root = Path(args.asset_root).expanduser().resolve()
    manuscript_path = asset_root / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt"
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    manuscript = manuscript_path.read_text(encoding="utf-8")
    if sha256_text(manuscript) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("A Ghost Story source hash changed")
    passages = source_passages(manuscript)
    estimate = budget_estimate(passages)
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3
    fingerprint = attempt_fingerprint(voice=args.voice, passages=passages, prosody_repair=args.prosody_repair)
    evidence_path = result_path(args.voice, args.prosody_repair)
    output_root = Path(args.output_root).expanduser().resolve()
    retry_reason = ""
    if evidence_path.exists():
        prior = json.loads(evidence_path.read_text(encoding="utf-8"))
        if prior.get("attempt_fingerprint") == fingerprint and prior.get("provider_calls_ran") is True:
            retry_allowed, retry_reason = local_validation_retry_allowed(prior, output_root, args.voice)
            if not args.resume_after_local_validation_repair or not retry_allowed:
                print(
                    json.dumps(
                        {
                            "status": "BLOCKED_REPEAT_ATTEMPT",
                            "attempt_fingerprint": fingerprint,
                            "local_validation_retry_allowed": retry_allowed,
                            "local_validation_retry_reason": retry_reason,
                        },
                        indent=2,
                    )
                )
                return 4
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    preflight = {
        "status": "PASS",
        "owner_decision": OWNER_DECISION,
        "slug": "a-ghost-story",
        "provider": "google",
        "voice": args.voice,
        "language_code": "en-GB",
        "speaking_rate": 0.88 if args.prosody_repair else 0.94,
        "prosody_repair": bool(args.prosody_repair),
        "passages": [{key: value for key, value in item.items() if key != "text"} for item in passages],
        "attempt_fingerprint": fingerprint,
        "resume_after_local_validation_repair": bool(args.resume_after_local_validation_repair),
        "local_validation_retry_reason": retry_reason or None,
        **estimate,
        "provider_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    from google.cloud import texttospeech  # noqa: PLC0415
    from openai import OpenAI  # noqa: PLC0415

    class JudgeArgs:
        slug = "a-ghost-story"
        title = "A Ghost Story"
        author = "Mark Twain"
        language = "eng"

    output_dir = output_root / args.voice / ("prosody_repair" if args.prosody_repair else "baseline")
    judgments: list[dict] = []
    errors_run: list[str] = []
    provider_calls_ran = False
    google_synthesis_calls = 0
    reused_valid_audio: list[str] = []
    started_at = iso_now()
    try:
        atomic_write(
            lock_path,
            json.dumps(
                acquired_lock_payload(lock, voice=args.voice, estimate=estimate, prosody_repair=args.prosody_repair),
                indent=2,
            ).encode("utf-8")
            + b"\n",
        )
        google_client = texttospeech.TextToSpeechClient()
        available = {voice.name for voice in google_client.list_voices(language_code="en-GB").voices}
        if args.voice not in available:
            raise RuntimeError(f"Selected Google voice is unavailable: {args.voice}")
        openai_client = OpenAI()
        for passage in passages:
            target = output_dir / f"{passage['passage_id']}.mp3"
            duration = ffprobe_with_retry(target) if args.resume_after_local_validation_repair else None
            if duration:
                reused_valid_audio.append(passage["passage_id"])
            else:
                provider_calls_ran = True
                google_synthesis_calls += 1
                synthesis_input = (
                    texttospeech.SynthesisInput(ssml=source_preserving_ssml(passage["text"]))
                    if args.prosody_repair
                    else texttospeech.SynthesisInput(text=passage["text"])
                )
                response = google_client.synthesize_speech(
                    input=synthesis_input,
                    voice=texttospeech.VoiceSelectionParams(language_code="en-GB", name=args.voice),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3,
                        speaking_rate=1.0 if args.prosody_repair else 0.94,
                        pitch=0.0,
                    ),
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(response.audio_content)
                duration = ffprobe_with_retry(target)
                if not response.audio_content or not duration:
                    raise RuntimeError(f"Google returned invalid audio for {passage['passage_id']}")
            sample = {
                "sample_label": passage["passage_id"],
                "start_time": 0.0,
                "duration": duration,
                "sample_audio_path": str(target),
                "sample_audio_hash": sha256_file(target),
                "source_text_hash": passage["text_hash"],
            }
            judgments.append(judge_audio_sample_with_openai(openai_client, JudgeArgs(), sample))
    except Exception as exc:  # noqa: BLE001
        errors_run.append(f"{type(exc).__name__}: {exc}")
    finally:
        atomic_write(lock_path, original_lock)

    passed, blockers = audition_pass(judgments) if len(judgments) == len(passages) else (False, errors_run or ["AUDITION_INCOMPLETE"])
    runtime = {
        **preflight,
        "status": "AUDITION_PASS" if passed else "AUDITION_REPAIR_REQUIRED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "google_synthesis_calls": google_synthesis_calls,
        "reused_valid_audio": reused_valid_audio,
        "judgments": judgments,
        "minimum_overall_score": min((item.get("scores") or {}).get("overall_listening_score", 0) for item in judgments) if judgments else 0,
        "minimum_confidence": min((item.get("scores") or {}).get("confidence_score", 0) for item in judgments) if judgments else 0,
        "fatal_flags": sorted({field for item in judgments for field in BINARY_LISTENING_FLAGS if (item.get("judge_flags") or {}).get(field)}),
        "blockers": blockers,
        "errors": errors_run,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(evidence_path, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
