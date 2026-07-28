#!/usr/bin/env python3
"""Run the one bounded OpenAI v3.90 representative pilot for Call of the Wild.

The script is deliberately title-scoped.  It binds the canonical sanitized
source and rights manifest, four deterministic passages, model, voice,
instructions, paid lock, budget and pinned local Whisper model.  Audio stays in
a private directory.  It cannot upload, publish, mutate release truth, or
authorize a full title without both raw ASR/source and separate listening QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
sys.path[:0] = [str(SCRIPT_DIR), str(HOOK_DIR)]

import sprint1_gift_kokoro_full_title_private_qa as asr_common  # noqa: E402
import sprint1_google_english_private_pipeline as source_pipeline  # noqa: E402
import sprint1_kokoro_title_private_audition as kokoro_common  # noqa: E402
from common import ffprobe_duration, sha256_file  # noqa: E402
from tts_hook import speech_create  # noqa: E402


SCHEMA = "earnalism.call_wild_openai_v390_representative.v1"
LISTENING_SCHEMA = "earnalism.google_english_listening_evidence.v1"
SLUG = "the-call-of-the-wild"
TITLE = "The Call of the Wild"
AUTHOR = "Jack London"
SOURCE_SHA256 = "36bf2714954e352c1c6a5fbbe65af1e77ab622e709e42907cd9451eda0982916"
MODEL = "gpt-4o-mini-tts"
VOICE = "verse"
PROFILE = "call-wild-rugged-literary-restraint-v1"
INSTRUCTIONS = (
    "Narrate as a premium American literary audiobook performer. Use a warm, "
    "rugged, natural voice with restrained adventure energy, precise diction, "
    "human phrasing, punctuation-aware pauses, and steady unhurried pacing. "
    "Keep dialogue distinct without theatrical character acting. Never sound "
    "robotic, breathless, sing-song, or like list reading. Read only the exact "
    "manuscript text."
)
USD_PER_1K_CHARS = 0.015
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
WHISPER_MODEL = kokoro_common.WHISPER_MODEL
WHISPER_FILENAME = kokoro_common.WHISPER_FILENAME
WHISPER_SHA256 = kokoro_common.WHISPER_SHA256
ASR_SETTINGS = asr_common.ASR_SETTINGS
PASSAGE_IDS = tuple(source_pipeline.PASSAGE_IDS)
FATAL_LISTENING_FLAGS = tuple(source_pipeline.FATAL_LISTENING_FLAGS)
DEFAULT_SOURCE = (
    ROOT
    / "internal/audiobook_lab/private_runs/inputs/"
    "the-call-of-the-wild/sanitized_source.txt"
)
DEFAULT_INPUT_MANIFEST = (
    ROOT
    / "internal/audiobook_lab/private_runs/inputs/"
    "the-call-of-the-wild/input_manifest.json"
)
DEFAULT_PRIVATE_OUTPUT = Path("/private/tmp/earnalism-call-wild-openai-v390")
DEFAULT_OUTPUT = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_openai_verse_v390_representative_20260728.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)


class CallWildPilotError(RuntimeError):
    """Raised when the exact bounded pilot contract is not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CallWildPilotError(message)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_bundle(
    source_path: Path, manifest_path: Path
) -> tuple[source_pipeline.SourceBundle, list[dict[str, Any]]]:
    bundle = source_pipeline.load_source_bundle(source_path, manifest_path)
    require(bundle.slug == SLUG, f"expected slug {SLUG}, got {bundle.slug}")
    require(bundle.title == TITLE, f"expected title {TITLE}, got {bundle.title}")
    require(bundle.author == AUTHOR, f"expected author {AUTHOR}, got {bundle.author}")
    require(
        bundle.source_sha256 == SOURCE_SHA256,
        "The Call of the Wild sanitized source hash changed",
    )
    passages = source_pipeline.select_representative_passages(bundle.source_text)
    require(
        tuple(item["passage_id"] for item in passages) == PASSAGE_IDS,
        "representative passage order changed",
    )
    return bundle, passages


def fingerprint(
    bundle: source_pipeline.SourceBundle, passages: Sequence[Mapping[str, Any]]
) -> str:
    return canonical_hash(
        {
            "schema": SCHEMA,
            "slug": SLUG,
            "source_sha256": bundle.source_sha256,
            "input_manifest_sha256": bundle.manifest_sha256,
            "passage_hashes": {
                item["passage_id"]: item["text_sha256"] for item in passages
            },
            "provider": "openai",
            "model": MODEL,
            "voice": VOICE,
            "profile": PROFILE,
            "instructions_sha256": source_pipeline.sha256_text(INSTRUCTIONS),
            "whisper_model": WHISPER_MODEL,
            "whisper_sha256": WHISPER_SHA256,
            "asr_settings": ASR_SETTINGS,
            "policy": "sprint1_audiobook_acceptance_v3_89",
            "scope": "one_private_four_passage_candidate_no_upload_or_publication",
        }
    )


def budget(
    passages: Sequence[Mapping[str, Any]],
    *,
    run_cap: float,
    title_cap: float,
    title_spend: float,
    sprint_cap: float,
    sprint_spend: float,
) -> dict[str, Any]:
    characters = sum(int(item["characters"]) for item in passages)
    estimate = round(characters / 1000 * USD_PER_1K_CHARS, 6)
    projected_title = round(title_spend + estimate, 6)
    projected_sprint = round(sprint_spend + estimate, 6)
    blockers = []
    if estimate > run_cap:
        blockers.append("estimated run spend exceeds run cap")
    if projected_title > title_cap:
        blockers.append("projected title spend exceeds title cap")
    if projected_sprint > sprint_cap:
        blockers.append("projected sprint spend exceeds sprint cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "billable_characters": characters,
        "usd_per_1k_characters": USD_PER_1K_CHARS,
        "estimated_tts_usd": estimate,
        "run_cap_usd": run_cap,
        "prior_title_spend_usd": title_spend,
        "projected_title_spend_usd": projected_title,
        "title_cap_usd": title_cap,
        "prior_sprint_spend_usd": sprint_spend,
        "projected_sprint_spend_usd": projected_sprint,
        "sprint_cap_usd": sprint_cap,
        "blockers": blockers,
    }


def validate_lock(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CallWildPilotError("paid lock must be valid UTF-8 JSON") from exc
    require(payload.get("status") == "active", "paid lock must remain active")
    require(payload.get("current_holder") == "none", "paid lock already has a holder")
    require(
        payload.get("allowed_next_holders", []) == [],
        "paid lock allowed_next_holders must be empty",
    )
    require(
        SLUG in (payload.get("allowed_slugs") or []),
        f"paid lock does not allow {SLUG}",
    )
    return payload


def acquired_lock(
    payload: Mapping[str, Any], *, attempt_fingerprint: str, estimate: float
) -> dict[str, Any]:
    return {
        **payload,
        "current_holder": f"sprint1_call_wild_openai_v390:{SLUG}",
        "allowed_next_holders": [],
        "allowed_slugs": [SLUG],
        "approved_scope": (
            "One private OpenAI gpt-4o-mini-tts/verse four-passage audition "
            f"for {SLUG}; fingerprint {attempt_fingerprint}; estimated TTS "
            f"${estimate:.6f}; no full title, upload, publication, or release mutation."
        ),
        "estimated_cost_usd": estimate,
        "updated_at": source_pipeline.iso_now(),
    }


def reject_repeat(output: Path, attempt_fingerprint: str) -> None:
    if not output.is_file():
        return
    prior = json.loads(output.read_text(encoding="utf-8"))
    if (
        prior.get("attempt_fingerprint") == attempt_fingerprint
        and prior.get("provider_calls_ran") is True
    ):
        raise CallWildPilotError(
            "the exact Call of the Wild OpenAI fingerprint already reached the provider"
        )


def audio_record(
    passage: Mapping[str, Any], audio_path: Path
) -> dict[str, Any]:
    duration = ffprobe_duration(audio_path)
    require(
        audio_path.is_file()
        and audio_path.stat().st_size > 0
        and duration is not None
        and duration > 0,
        f"invalid private audio: {passage['passage_id']}",
    )
    header = audio_path.read_bytes()[:3]
    require(
        header.startswith(b"ID3") or header[:1] == b"\xff",
        f"private audio is not MP3: {passage['passage_id']}",
    )
    return {
        "passage_id": passage["passage_id"],
        "source_text_sha256": passage["text_sha256"],
        "characters": passage["characters"],
        "audio_path": str(audio_path),
        "audio_sha256": sha256_file(audio_path),
        "audio_size_bytes": audio_path.stat().st_size,
        "duration_seconds": round(float(duration), 6),
    }


def run_local_asr(
    records: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_cache: Path,
    *,
    model_loader: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    model_path = whisper_cache.expanduser().resolve() / WHISPER_FILENAME
    require(model_path.is_file(), f"pinned Whisper model missing: {model_path}")
    require(
        sha256_file(model_path) == WHISPER_SHA256,
        "pinned Whisper model hash mismatch",
    )
    if model_loader is None:
        try:
            import whisper  # noqa: PLC0415
        except ImportError as exc:
            raise CallWildPilotError("openai-whisper is required") from exc
        model_loader = whisper.load_model
    model = model_loader(WHISPER_MODEL, download_root=str(whisper_cache))
    source_by_id = {item["passage_id"]: item for item in passages}
    reports: list[dict[str, Any]] = []
    for record in records:
        passage_id = str(record["passage_id"])
        source = source_by_id[passage_id]
        result = model.transcribe(str(record["audio_path"]), **ASR_SETTINGS)
        transcript = str(result.get("text") or "").strip()
        metrics = asr_common.ordered_metrics(str(source["text"]), transcript)
        words, anomalies = asr_common.verified_words(
            result, float(record["duration_seconds"])
        )
        passed = bool(metrics["pass"] and words and not anomalies)
        reports.append(
            {
                "passage_id": passage_id,
                "source_text_sha256": source["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "transcript": transcript,
                "transcript_sha256": source_pipeline.sha256_text(transcript),
                "audio_derived_word_timestamps": words,
                "word_timestamp_anomalies": anomalies,
                "word_timestamp_evidence_valid": bool(words) and not anomalies,
                **metrics,
                "pass": passed,
            }
        )
    passed = bool(reports and all(item["pass"] for item in reports))
    return {
        "status": "PASS" if passed else "FAIL",
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "settings": ASR_SETTINGS,
        "required_score": ASR_SCORE_MIN,
        "required_coverage": ASR_COVERAGE_MIN,
        "audio_derived": True,
        "reports": reports,
    }


def listening_evidence(
    *,
    result_path: Path,
    result_sha256: str,
    bundle: source_pipeline.SourceBundle,
    attempt_fingerprint: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": LISTENING_SCHEMA,
        "status": "PENDING_LISTENING_REVIEW",
        "slug": SLUG,
        "title": TITLE,
        "provider": "openai",
        "voice": VOICE,
        "language_code": "en-US",
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "audition_fingerprint": attempt_fingerprint,
        "audition_manifest_path": str(result_path),
        "audition_manifest_sha256": result_sha256,
        "minimum_listening_score": 8.9,
        "minimum_listening_confidence": 0.90,
        "per_dimension_score_min": 8.9,
        "anti_robotic_texture_score_min": 9.2,
        "anti_choppy_join_score_min": 9.2,
        "required_passages": list(PASSAGE_IDS),
        "fatal_flags_required_false": list(FATAL_LISTENING_FLAGS),
        "private_output_only": True,
        "provider_calls_ran": True,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "samples": [
            {
                "passage_id": item["passage_id"],
                "source_text_sha256": item["source_text_sha256"],
                "audio_path": item["audio_path"],
                "audio_sha256": item["audio_sha256"],
                "overall_listening_score": None,
                "confidence_score": None,
                "scores": {},
                "fatal_flags": [],
                "judge_flags": {
                    flag: False for flag in FATAL_LISTENING_FLAGS
                },
                "review_notes": "",
            }
            for item in records
        ],
    }


def preflight(args: argparse.Namespace) -> tuple[dict[str, Any], Any, list[dict[str, Any]]]:
    bundle, passages = validate_bundle(args.sanitized_source, args.input_manifest)
    attempt_fingerprint = fingerprint(bundle, passages)
    reject_repeat(args.output, attempt_fingerprint)
    private_root = source_pipeline.validate_private_output_dir(args.private_output_dir)
    run_budget = budget(
        passages,
        run_cap=args.run_budget_usd,
        title_cap=args.title_budget_usd,
        title_spend=args.title_spend_usd,
        sprint_cap=args.sprint_budget_usd,
        sprint_spend=args.sprint_spend_usd,
    )
    require(run_budget["status"] == "PASS", "; ".join(run_budget["blockers"]))
    lock_raw = args.paid_lock.expanduser().resolve().read_bytes()
    validate_lock(lock_raw)
    payload = {
        "schema_version": SCHEMA,
        "status": "PREFLIGHT_PASS",
        "generated_at": source_pipeline.iso_now(),
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "provider": "openai",
        "model": MODEL,
        "voice": VOICE,
        "profile": PROFILE,
        "instructions_sha256": source_pipeline.sha256_text(INSTRUCTIONS),
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "attempt_fingerprint": attempt_fingerprint,
        "representative_passages": [
            {
                key: item[key]
                for key in ("passage_id", "text_sha256", "characters")
            }
            for item in passages
        ],
        "budget": run_budget,
        "private_run_dir": str(private_root / SLUG / attempt_fingerprint[:16]),
        "provider_calls_ran": False,
        "synthesis_calls": 0,
        "actual_provider_spend_usd": 0.0,
        "model_attempt_consumed": False,
        "paid_lock_touched": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_gate_mutated": False,
        "public_audio_status": "AUDIO_HIDDEN",
    }
    return payload, bundle, passages


def execute(
    args: argparse.Namespace,
    payload: dict[str, Any],
    bundle: source_pipeline.SourceBundle,
    passages: list[dict[str, Any]],
    *,
    speech: Callable[..., None] = speech_create,
    client_factory: Callable[[], Any] | None = None,
    model_loader: Callable[..., Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    if os.environ.get("EARNALISM_APPROVE_PAID_OPENAI_TTS", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        raise CallWildPilotError(
            "EARNALISM_APPROVE_PAID_OPENAI_TTS=true is required"
        )
    require(bool(os.environ.get("OPENAI_API_KEY")), "OPENAI_API_KEY is required")
    if client_factory is None:
        from openai import OpenAI  # noqa: PLC0415

        client_factory = OpenAI

    original_lock = args.paid_lock.expanduser().resolve().read_bytes()
    lock = validate_lock(original_lock)
    run_dir = Path(payload["private_run_dir"])
    audio_dir = run_dir / "audio"
    source_pipeline.atomic_write_bytes(run_dir / "sanitized_source.txt", bundle.source_bytes)
    source_pipeline.atomic_write_bytes(run_dir / "input_manifest.json", bundle.manifest_bytes)
    provider_calls_ran = False
    synthesis_calls = 0
    records: list[dict[str, Any]] = []
    error = ""
    try:
        source_pipeline.atomic_write_json(
            args.paid_lock,
            acquired_lock(
                lock,
                attempt_fingerprint=payload["attempt_fingerprint"],
                estimate=float(payload["budget"]["estimated_tts_usd"]),
            ),
        )
        client = client_factory()
        for passage in passages:
            audio_path = audio_dir / f"{passage['passage_id']}.mp3"
            provider_calls_ran = True
            speech(
                client,
                voice=VOICE,
                instructions=INSTRUCTIONS,
                text=passage["text"],
                out_path=audio_path,
            )
            synthesis_calls += 1
            records.append(audio_record(passage, audio_path))
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        source_pipeline.atomic_write_bytes(args.paid_lock, original_lock)

    lock_restored = args.paid_lock.read_bytes() == original_lock
    require(lock_restored, "paid lock was not restored byte-for-byte")
    result = {
        **payload,
        "finished_at": source_pipeline.iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "synthesis_calls": synthesis_calls,
        "model_attempt_consumed": provider_calls_ran,
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": lock_restored,
        "paid_lock_sha256_before": source_pipeline.sha256_bytes(original_lock),
        "paid_lock_sha256_after": source_pipeline.sha256_bytes(
            args.paid_lock.read_bytes()
        ),
        "generated_audio": records,
        "error": error or None,
        "actual_provider_billing": "NOT_REPORTED",
    }
    if error:
        result.update(
            {
                "status": "PRIVATE_PROVIDER_FAILED_SOURCE_BOUND_DELIVERY_REQUIRED",
                "blockers": [error],
                "next_state": "SOURCE_BOUND_DELIVERY_REQUIRED",
            }
        )
        source_pipeline.atomic_write_json(args.output, result)
        return 3, result

    asr = run_local_asr(
        records, passages, args.whisper_cache_dir, model_loader=model_loader
    )
    result["asr"] = asr
    if asr["status"] != "PASS":
        result.update(
            {
                "status": "PRIVATE_REPRESENTATIVE_ASR_FAIL_SOURCE_BOUND_DELIVERY_REQUIRED",
                "blockers": ["REPRESENTATIVE_ASR_SOURCE_GATE_FAILED"],
                "next_state": "SOURCE_BOUND_DELIVERY_REQUIRED",
            }
        )
        source_pipeline.atomic_write_json(args.output, result)
        return 3, result

    evidence_path = run_dir / "audition_listening_evidence.json"
    result.update(
        {
            "status": "PRIVATE_REPRESENTATIVE_ASR_PASS_LISTENING_QA_REQUIRED",
            "blockers": ["REPRESENTATIVE_LISTENING_QA_REQUIRED"],
            "listening_evidence_path": str(evidence_path),
            "next_state": "REPRESENTATIVE_LISTENING_QA",
        }
    )
    source_pipeline.atomic_write_json(args.output, result)
    source_pipeline.atomic_write_json(
        evidence_path,
        listening_evidence(
            result_path=args.output.resolve(),
            result_sha256=sha256_file(args.output),
            bundle=bundle,
            attempt_fingerprint=payload["attempt_fingerprint"],
            records=records,
        ),
    )
    return 0, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--sanitized-source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--input-manifest", type=Path, default=DEFAULT_INPUT_MANIFEST)
    parser.add_argument("--private-output-dir", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--whisper-cache-dir", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--run-budget-usd", type=float, default=0.15)
    parser.add_argument("--title-budget-usd", type=float, default=8.0)
    parser.add_argument("--title-spend-usd", type=float, default=0.0)
    parser.add_argument("--sprint-budget-usd", type=float, default=75.0)
    parser.add_argument("--sprint-spend-usd", type=float, default=74.0826)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload, bundle, passages = preflight(args)
        if args.preflight:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        code, result = execute(args, payload, bundle, passages)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "attempt_fingerprint": result["attempt_fingerprint"],
                    "provider_calls_ran": result["provider_calls_ran"],
                    "synthesis_calls": result["synthesis_calls"],
                    "asr_status": (result.get("asr") or {}).get("status"),
                    "listening_evidence_path": result.get("listening_evidence_path"),
                    "blockers": result.get("blockers", []),
                    "paid_lock_restored_byte_for_byte": result.get(
                        "paid_lock_restored_byte_for_byte"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return code
    except (OSError, ValueError, CallWildPilotError, source_pipeline.PipelineError) as exc:
        print(
            json.dumps(
                {"status": "BLOCKED_BEFORE_PROVIDER", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
