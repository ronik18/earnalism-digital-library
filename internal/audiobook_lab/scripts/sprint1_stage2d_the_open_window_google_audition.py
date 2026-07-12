#!/usr/bin/env python3
"""Run one bounded Google replacement-provider audition for The Open Window."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_stage2d_a_ghost_story_google_audition as shared  # noqa: E402


OWNER_DECISION = "AUTHORIZE_STAGE_2E_THE_OPEN_WINDOW_STUDIO_B_AUDITION_AND_PUBLICATION_IF_PASS"
SLUG = "the-open-window"
TITLE = "The Open Window"
AUTHOR = "Saki"
HOLDER = "sprint1_publication_stage2e_the_open_window"
EXPECTED_SANITIZED_SHA256 = "f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be"
PRIOR_SPRINT_ESTIMATED_SPEND_USD = 4.0684
SUPPORTED_VOICES = {"en-GB-Studio-B"}
RESULT_DIR = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs"
MAX_SAMPLE_SECONDS = 30.0
LISTENING_POLICY = "schema3_universal_9_7"


def source_passages(manuscript: str) -> list[dict]:
    flattened = shared.flatten_source(manuscript)

    def extract(start_marker: str | None, end_marker: str) -> str:
        start = 0 if start_marker is None else flattened.index(start_marker)
        end = flattened.index(end_marker, start) + len(end_marker)
        return flattened[start:end]

    passages = [
        {
            "passage_id": "opening_dialogue",
            "text": extract(None, "young lady of fifteen; “in the meantime you must try and put up with me.”"),
        },
        {
            "passage_id": "shooting_party_tragedy",
            "text": extract("“Out through that window", "treacherous piece of bog."),
        },
        {
            "passage_id": "twilight_return",
            "text": extract("A tired brown spaniel", "said, Bertie, why do you bound?”"),
        },
        {
            "passage_id": "spaniel_explanation_ending",
            "text": extract("He was once hunted", "Romance at short notice was her speciality."),
        },
    ]
    for passage in passages:
        passage["text_hash"] = shared.sha256_text(passage["text"])
        passage["characters"] = len(passage["text"])
    return passages


def validated_manuscript(chapter: dict) -> str:
    manuscript = str(chapter.get("content") or "")
    if chapter.get("processing_status") != "ready" or chapter.get("processing_warnings") != []:
        raise RuntimeError("The Open Window controlled source is not clean and ready")
    if chapter.get("sanitizedSha256") != EXPECTED_SANITIZED_SHA256:
        raise RuntimeError("The Open Window recorded sanitized hash changed")
    if shared.sha256_text(manuscript) != EXPECTED_SANITIZED_SHA256:
        raise RuntimeError("The Open Window controlled content hash changed")
    return manuscript


def validate_sample_duration(duration: float | None, passage_id: str) -> None:
    if not duration:
        raise RuntimeError(f"Google returned invalid audio for {passage_id}")
    if duration > MAX_SAMPLE_SECONDS:
        raise RuntimeError(f"Google sample exceeded {MAX_SAMPLE_SECONDS:.0f}s cap for {passage_id}: {duration:.3f}s")


def budget_estimate(
    passages: list[dict],
    *,
    prior_sprint_estimated_spend_usd: float = PRIOR_SPRINT_ESTIMATED_SPEND_USD,
    prior_title_estimated_spend_usd: float = 0.0,
) -> dict:
    tts_rate = float(os.environ["EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS"])
    qa_rate = float(os.environ["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
    tts = round(sum(item["characters"] for item in passages) / 1000.0 * tts_rate, 4)
    qa = round(len(passages) * qa_rate, 4)
    current = round(tts + qa, 4)
    title_total = round(prior_title_estimated_spend_usd + current, 4)
    sprint_total = round(prior_sprint_estimated_spend_usd + current, 4)
    blockers: list[str] = []
    if current > float(os.environ["EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD"]):
        blockers.append("Google audition estimate exceeds its sub-cap")
    if qa > float(os.environ["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"]):
        blockers.append("Listening QA estimate exceeds its sub-cap")
    if title_total > float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]):
        blockers.append("The Open Window estimate exceeds the per-title cap")
    if sprint_total > float(os.environ["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]):
        blockers.append("Sprint estimate exceeds the authorized cap")
    if sprint_total > float(os.environ["MAX_TTS_BUDGET_USD"]):
        blockers.append("Sprint estimate exceeds MAX_TTS_BUDGET_USD")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_google_tts_usd": tts,
        "estimated_listening_qa_usd": qa,
        "estimated_current_usd": current,
        "prior_title_estimated_spend_usd": round(prior_title_estimated_spend_usd, 4),
        "estimated_title_total_usd": title_total,
        "prior_sprint_estimated_spend_usd": round(prior_sprint_estimated_spend_usd, 4),
        "estimated_sprint_total_usd": sprint_total,
        "estimated_sprint_remaining_usd": round(float(os.environ["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]) - sprint_total, 4),
        "blockers": blockers,
    }


def attempt_fingerprint(*, voice: str, passages: list[dict], prosody_repair: bool) -> str:
    payload = json.dumps(
        {
            "slug": SLUG,
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


def run_id(*, voice: str, prosody_repair: bool) -> str:
    suffix = "-prosody-repair" if prosody_repair else ""
    return f"sprint1-stage2e-the-open-window-{voice.lower()}{suffix}"


def acquired_lock_payload(lock: dict, *, voice: str, estimate: dict, prosody_repair: bool) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": shared.iso_now(),
            "budget_cap_usd": 175,
            "run_id": run_id(voice=voice, prosody_repair=prosody_repair),
            "approved_scope": (
                f"Stage 2E final The Open Window Google Studio-B representative audition only; {voice}; "
                "four passages up to 30 seconds; "
                f"prosody repair {prosody_repair}; estimated provider plus QA "
                f"{estimate['estimated_current_usd']:.4f} USD; no full TTS, upload, publication, or release mutation."
            ),
            "allowed_slugs": [SLUG],
            "stop_conditions": [
                "Any runtime gate or provider credential is missing",
                "The controlled source hash or readiness status changes",
                "Estimated spend exceeds a provider, title, or sprint cap",
                "The same provider/voice/source fingerprint already reached providers",
                "Any full TTS, upload, publication, or release mutation is attempted",
            ],
            "updated_at": shared.iso_now(),
        }
    )
    return payload


def result_path(voice: str, prosody_repair: bool) -> Path:
    suffix = "_prosody_repair" if prosody_repair else ""
    safe_voice = voice.lower().replace("-", "_")
    return RESULT_DIR / f"the-open-window_stage2e_google_audition_{safe_voice}{suffix}.json"


def runtime_gate_errors(*, prosody_repair: bool = False) -> list[str]:
    errors = shared.runtime_gate_errors()
    if prosody_repair and os.environ.get("EARNALISM_APPROVE_THE_OPEN_WINDOW_STUDIO_B_PROSODY_REPAIR") != "true":
        errors.append("EARNALISM_APPROVE_THE_OPEN_WINDOW_STUDIO_B_PROSODY_REPAIR must equal true")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="en-GB-Studio-B", choices=sorted(SUPPORTED_VOICES))
    parser.add_argument(
        "--asset-root",
        default=os.environ.get("EARNALISM_STAGE2E_ASSET_ROOT", os.environ.get("EARNALISM_STAGE2D_ASSET_ROOT", str(ROOT))),
    )
    parser.add_argument("--output-root", default="/tmp/earnalism-the-open-window-stage2e-google-audition")
    parser.add_argument("--prior-sprint-estimated-spend-usd", type=float, default=PRIOR_SPRINT_ESTIMATED_SPEND_USD)
    parser.add_argument("--prior-title-estimated-spend-usd", type=float, default=0.0)
    parser.add_argument("--prosody-repair", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors(prosody_repair=args.prosody_repair)
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2

    asset_root = Path(args.asset_root).expanduser().resolve()
    chapter_path = asset_root / "data/controlled_publications/the-open-window/chapters/chapter-001.json"
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    chapter = json.loads(chapter_path.read_text(encoding="utf-8"))
    manuscript = validated_manuscript(chapter)

    passages = source_passages(manuscript)
    estimate = budget_estimate(
        passages,
        prior_sprint_estimated_spend_usd=args.prior_sprint_estimated_spend_usd,
        prior_title_estimated_spend_usd=args.prior_title_estimated_spend_usd,
    )
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3

    fingerprint = attempt_fingerprint(voice=args.voice, passages=passages, prosody_repair=args.prosody_repair)
    evidence_path = result_path(args.voice, args.prosody_repair)
    if evidence_path.exists():
        prior = json.loads(evidence_path.read_text(encoding="utf-8"))
        if prior.get("attempt_fingerprint") == fingerprint and prior.get("provider_calls_ran") is True:
            print(json.dumps({"status": "BLOCKED_REPEAT_ATTEMPT", "attempt_fingerprint": fingerprint}, indent=2))
            return 4

    original_lock = lock_path.read_bytes()
    lock = shared.load_lock(original_lock)
    preflight = {
        "status": "PASS",
        "owner_decision": OWNER_DECISION,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "provider": "google",
        "voice": args.voice,
        "run_id": run_id(voice=args.voice, prosody_repair=args.prosody_repair),
        "listening_policy": LISTENING_POLICY,
        "language_code": "en-GB",
        "speaking_rate": 0.88 if args.prosody_repair else 0.94,
        "prosody_repair": bool(args.prosody_repair),
        "source_path": str(chapter_path),
        "sanitized_sha256": EXPECTED_SANITIZED_SHA256,
        "passages": [{key: value for key, value in item.items() if key != "text"} for item in passages],
        "attempt_fingerprint": fingerprint,
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
        slug = SLUG
        title = TITLE
        author = AUTHOR
        language = "eng"

    output_root = Path(args.output_root).expanduser().resolve()
    output_dir = output_root / args.voice / ("prosody_repair" if args.prosody_repair else "baseline")
    judgments: list[dict] = []
    run_errors: list[str] = []
    provider_calls_ran = False
    started_at = shared.iso_now()
    try:
        shared.atomic_write(
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
            provider_calls_ran = True
            target = output_dir / f"{passage['passage_id']}.mp3"
            synthesis_input = (
                texttospeech.SynthesisInput(ssml=shared.source_preserving_ssml(passage["text"]))
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
            shared.atomic_write(target, response.audio_content)
            duration = shared.ffprobe_with_retry(target)
            if not response.audio_content:
                raise RuntimeError(f"Google returned invalid audio for {passage['passage_id']}")
            validate_sample_duration(duration, passage["passage_id"])
            sample = {
                "sample_label": passage["passage_id"],
                "start_time": 0.0,
                "duration": duration,
                "sample_audio_path": str(target),
                "sample_audio_hash": shared.sha256_file(target),
                "source_text_hash": passage["text_hash"],
            }
            judgments.append(shared.judge_audio_sample_with_openai(openai_client, JudgeArgs(), sample))
    except Exception as exc:  # noqa: BLE001
        run_errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        shared.atomic_write(lock_path, original_lock)

    passed, blockers = shared.audition_pass(judgments) if len(judgments) == len(passages) else (False, run_errors or ["AUDITION_INCOMPLETE"])
    runtime = {
        **preflight,
        "status": "AUDITION_PASS" if passed else "AUDITION_REPAIR_REQUIRED",
        "started_at": started_at,
        "finished_at": shared.iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "judgments": judgments,
        "minimum_overall_score": min((item.get("scores") or {}).get("overall_listening_score", 0) for item in judgments) if judgments else 0,
        "minimum_confidence": min((item.get("scores") or {}).get("confidence_score", 0) for item in judgments) if judgments else 0,
        "fatal_flags": sorted(
            {
                field
                for item in judgments
                for field in shared.BINARY_LISTENING_FLAGS
                if (item.get("judge_flags") or {}).get(field)
            }
        ),
        "blockers": blockers,
        "errors": run_errors,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    shared.atomic_write(evidence_path, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
