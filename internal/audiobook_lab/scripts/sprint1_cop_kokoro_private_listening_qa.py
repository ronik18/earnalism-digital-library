#!/usr/bin/env python3
"""Judge the exact Cop and the Anthem Kokoro representative candidate.

This is a four-sample private screen. It may authorize the next private stage
only when both the active English premium policy and the owner's exact-10
target pass. It cannot generate, upload, publish, or mutate release truth.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]

from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    LISTENING_QA_HOOK_VERSION,
    LISTENING_QA_RUBRIC_VERSION,
    LISTENING_THRESHOLDS,
    TIERED_AUDIOBOOK_ACCEPTANCE_THRESHOLDS,
    safe_float,
)
from common import ffprobe_duration, sha256_file  # noqa: E402


SLUG = "the-cop-and-the-anthem"
TITLE = "The Cop and the Anthem"
AUTHOR = "O. Henry"
LANGUAGE = "eng"
SCOPE = "cop_kokoro_representative_listening_qa_v1"
HOLDER = "sprint1_cop_kokoro_private_listening_qa"
EXPECTED_SAMPLE_COUNT = 4
EXPECTED_SCHEMA = "earnalism.cop_kokoro_representative.v1"
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = "6d1ea462d37c72e71a92ec7267ec453b089838ec1ee78b30c1cc61363efd6530"
EXPECTED_SOURCE_SHA256 = "77a6d1c7ff6162cc7aad47b950666c6bb1dedf0beb55a08f3f476e27e57bd3ab"
EXPECTED_ATTEMPT_FINGERPRINT = "b693be6196019d6e44b22ac1cdcc7e1ea7099550f69eb326bb3cdacf4f27c6bf"
EXPECTED_ASR_CONFIG_FINGERPRINT = "3610d60e9094c3f80f4c22d65b63db45f622f48b7ea927301acf01a221444075"
EXPECTED_MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
EXPECTED_VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
EXPECTED_SAMPLE_BINDINGS: dict[str, dict[str, Any]] = {
    "opening_winter": {
        "source_text_sha256": "99ec90941755c7e7b70c98f2a122f1aeefdf7c996bd3e66bade805b8149f4a4c",
        "audio_sha256": "cdccca49984fac5f84eb27bab12050888936a3c6b27137d770f2a65e682c05ec",
        "size_bytes": 800_444,
        "duration_seconds": 16.675,
    },
    "waiter_dialogue": {
        "source_text_sha256": "9b7aa5abbd52519cc2fd4c155ceb43711cd287f068792c319b8e1cf4554e50b8",
        "audio_sha256": "60230065b6fb0181c9f2e0891d948ae901a5f85c986ec6c874a652bdb58559e9",
        "size_bytes": 1_336_844,
        "duration_seconds": 27.85,
    },
    "church_reckoning": {
        "source_text_sha256": "8af80b2d0f436da3933b2a50bed8dc98d299367d982d520110c0b07da8b364ae",
        "audio_sha256": "e6c8b69f1bb3ebd826c96522a506e4ac937848f34ed8fe8e9c7c78baf275dd5f",
        "size_bytes": 966_044,
        "duration_seconds": 20.125,
    },
    "ironic_ending": {
        "source_text_sha256": "cb03b2bf6553545bc323f4417dafced01e0042aca8d5f31f32245311357f3c3d",
        "audio_sha256": "986f2afe63ba4dfb28d72d7680d2f335ae7c6d534bcae6ace744402ef88b004b",
        "size_bytes": 2_834_444,
        "duration_seconds": 59.05,
    },
}

# This is the active tiered English premium policy: quality dimensions >= 9.0,
# overall >= 9.3, confidence >= 0.90, and no fatal flag.
PLATFORM_THRESHOLDS = dict(TIERED_AUDIOBOOK_ACCEPTANCE_THRESHOLDS)
QUALITY_DIMENSIONS = tuple(field for field in LISTENING_THRESHOLDS if field != "confidence_score")

EXPECTED_ENV = {
    "EARNALISM_APPROVE_COP_KOKORO_LISTENING_QA": "true",
    "EARNALISM_APPROVED_AUDIOBOOK_SLUG": SLUG,
    "EARNALISM_APPROVED_AUDIOBOOK_SCOPE": SCOPE,
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.20",
    "MAX_TTS_BUDGET_USD": "0.20",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
}
DEFAULT_EVIDENCE = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_representative_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_bella_listening_qa_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


class CopKokoroListeningQAError(RuntimeError):
    """Raised when exact private listening prerequisites do not match."""


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    assert_nonpublic_output(path)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


def canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def assert_nonpublic_output(path: Path) -> None:
    rendered = f"/{path.expanduser().resolve().as_posix().lower().strip('/')}/"
    forbidden = ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/")
    if any(marker in rendered for marker in forbidden):
        raise CopKokoroListeningQAError(f"public output path is forbidden: {path}")


def assert_private_audio(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    if "/internal/audiobook_lab/private_runs/" not in rendered:
        raise CopKokoroListeningQAError(f"audio is outside private_runs: {resolved}")
    if any(marker in rendered for marker in ("/frontend/public/", "/frontend/build/", "/public/audio/")):
        raise CopKokoroListeningQAError(f"public audio path is forbidden: {resolved}")
    return resolved


def runtime_gate_errors(env: Mapping[str, str]) -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if env.get(name) != expected
    ]
    if not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def budget_guard(env: Mapping[str, str]) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        unit = float(env["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
        stage_cap = float(env["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"])
        total_cap = float(env["MAX_TTS_BUDGET_USD"])
    except (KeyError, TypeError, ValueError):
        unit = stage_cap = total_cap = math.nan
        blockers.append("Listening-QA estimates and caps must be numeric")
    estimate = round(unit * EXPECTED_SAMPLE_COUNT, 4) if math.isfinite(unit) else math.nan
    if not all(math.isfinite(value) and value > 0 for value in (unit, stage_cap, total_cap)):
        blockers.append("Listening-QA estimates and caps must be positive finite values")
    if unit != 0.05:
        blockers.append("Estimated listening cost must be exactly 0.05 USD per sample")
    if stage_cap != 0.20 or total_cap != 0.20:
        blockers.append("Listening-QA stage and total caps must each be exactly 0.20 USD")
    if math.isfinite(estimate) and (estimate > stage_cap or estimate > total_cap):
        blockers.append("Four-sample estimate exceeds an approved cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "estimated_usd_per_sample": unit,
        "estimated_listening_qa_usd": estimate,
        "listening_qa_cap_usd": stage_cap,
        "total_budget_cap_usd": total_cap,
        "blockers": sorted(set(blockers)),
    }


def _require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise CopKokoroListeningQAError(f"{label} changed: expected {expected!r}, observed {observed!r}")


def load_evidence(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if not path.is_file():
        raise CopKokoroListeningQAError(f"Cop evidence is missing: {path}")
    _require_equal(sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    _require_equal(evidence.get("schema"), EXPECTED_SCHEMA, "evidence schema")
    _require_equal(evidence.get("status"), EXPECTED_STATUS, "evidence status")

    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "language": LANGUAGE,
        "passage_count": EXPECTED_SAMPLE_COUNT,
        "representative_only": True,
        "full_title_generated": False,
    }.items():
        _require_equal(scope.get(key), expected, f"scope.{key}")

    source = evidence.get("source") if isinstance(evidence.get("source"), dict) else {}
    _require_equal(source.get("source_sha256"), EXPECTED_SOURCE_SHA256, "source SHA-256")
    engine = evidence.get("engine") if isinstance(evidence.get("engine"), dict) else {}
    _require_equal(engine.get("package"), "kokoro", "engine package")
    _require_equal(engine.get("model_revision"), EXPECTED_MODEL_REVISION, "model revision")
    _require_equal(engine.get("voice"), "af_bella", "voice")
    _require_equal(engine.get("voice_sha256"), EXPECTED_VOICE_SHA256, "voice SHA-256")
    _require_equal(engine.get("attempt_fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")

    asr = evidence.get("asr") if isinstance(evidence.get("asr"), dict) else {}
    _require_equal(asr.get("status"), "PASS", "ASR status")
    _require_equal(asr.get("audio_derived"), True, "ASR audio-derived flag")
    _require_equal(asr.get("config_fingerprint"), EXPECTED_ASR_CONFIG_FINGERPRINT, "ASR config fingerprint")
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    _require_equal(len(reports), EXPECTED_SAMPLE_COUNT, "ASR report count")
    reports_by_id = {str(item.get("passage_id") or ""): item for item in reports}
    _require_equal(set(reports_by_id), set(EXPECTED_SAMPLE_BINDINGS), "ASR passage IDs")

    samples = evidence.get("samples") if isinstance(evidence.get("samples"), list) else []
    _require_equal(len(samples), EXPECTED_SAMPLE_COUNT, "sample count")
    samples_by_id = {str(item.get("passage_id") or ""): item for item in samples}
    _require_equal(set(samples_by_id), set(EXPECTED_SAMPLE_BINDINGS), "sample passage IDs")

    verified: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = samples_by_id[passage_id]
        report = reports_by_id[passage_id]
        for key in ("source_text_sha256", "audio_sha256", "size_bytes", "duration_seconds"):
            _require_equal(sample.get(key), expected[key], f"{passage_id} sample {key}")
        audio = assert_private_audio(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise CopKokoroListeningQAError(f"private audio is missing: {passage_id}")
        _require_equal(sha256_file(audio), expected["audio_sha256"], f"{passage_id} measured SHA-256")
        _require_equal(audio.stat().st_size, expected["size_bytes"], f"{passage_id} measured size")
        measured_duration = ffprobe_duration(audio) or 0.0
        if abs(measured_duration - float(expected["duration_seconds"])) > 0.005:
            raise CopKokoroListeningQAError(
                f"{passage_id} measured duration changed: expected {expected['duration_seconds']}, observed {measured_duration}"
            )
        for key, required in {
            "audio_sha256": expected["audio_sha256"],
            "source_text_sha256": expected["source_text_sha256"],
            "score": 10.0,
            "coverage": 1.0,
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_integrity_pass": True,
            "no_missing_content": True,
            "no_duplicate_content": True,
            "no_reordered_content": True,
            "no_unexpected_content": True,
            "pass": True,
        }.items():
            _require_equal(report.get(key), required, f"{passage_id} ASR {key}")
        verified.append(
            {
                "passage_id": passage_id,
                "sample_label": passage_id,
                "sample_audio_path": str(audio),
                "sample_audio_hash": expected["audio_sha256"],
                "sample_audio_size_bytes": expected["size_bytes"],
                "sample_audio_duration_seconds": expected["duration_seconds"],
                "source_text_sha256": expected["source_text_sha256"],
                "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
                "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
            }
        )

    sample_fingerprint = canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
            "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
            "sample_bindings": EXPECTED_SAMPLE_BINDINGS,
            "judge_model": EXPECTED_ENV["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
            "rubric_version": LISTENING_QA_RUBRIC_VERSION,
            "hook_version": LISTENING_QA_HOOK_VERSION,
            "platform_thresholds": PLATFORM_THRESHOLDS,
            "owner_quality_target": 10.0,
        }
    )
    return evidence, verified, sample_fingerprint


def load_lock(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CopKokoroListeningQAError(f"paid_tts.lock is invalid JSON: {exc}") from exc
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise CopKokoroListeningQAError("paid_tts.lock is not safely available")
    if payload.get("allowed_next_holders") != []:
        raise CopKokoroListeningQAError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: Mapping[str, Any], budget: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "approved_scope": (
                f"{SCOPE} for {SLUG}; four exact private representative samples only; maximum estimated "
                "0.20 USD; no TTS, upload, publication, or release-gate mutation."
            ),
            "allowed_slugs": [SLUG],
            "budget_cap_usd": budget["total_budget_cap_usd"],
            "stop_conditions": [
                "Any explicit approval, slug, scope, API key, estimate, or cap is missing or mismatched",
                "Evidence, source, attempt, ASR config, audio hash, size, duration, or objective result changes",
                "The same listening sample fingerprint already reached the judge",
                "Estimated listening spend exceeds 0.20 USD",
                "Any generation, upload, publication, public Listen, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def prior_attempt_completed(output_path: Path, fingerprint: str) -> bool:
    if not output_path.is_file():
        return False
    try:
        prior = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return prior.get("sample_fingerprint") == fingerprint and prior.get("provider_calls_ran") is True


def evaluate_judgments(samples: list[dict[str, Any]]) -> dict[str, Any]:
    minimums = {
        field: round(min((safe_float((sample.get("scores") or {}).get(field), 0.0) for sample in samples), default=0.0), 4)
        for field in PLATFORM_THRESHOLDS
    }
    fatal = sorted(
        {
            field
            for sample in samples
            for field in BINARY_LISTENING_FLAGS
            if bool((sample.get("judge_flags") or {}).get(field))
        }
    )
    sample_blockers = [
        f"{sample.get('sample_label')}: {sample.get('blocker_reason')}"
        for sample in samples
        if str(sample.get("blocker_reason") or "").strip()
    ]
    sample_blockers.extend(
        f"{sample.get('sample_label')}: FRONTMATTER_PRESENT"
        for sample in samples
        if bool(sample.get("frontmatter_present"))
    )
    threshold_failures = {
        field: {"minimum": minimums[field], "required": threshold}
        for field, threshold in PLATFORM_THRESHOLDS.items()
        if minimums[field] < threshold
    }
    platform_pass = (
        len(samples) == EXPECTED_SAMPLE_COUNT
        and not fatal
        and not sample_blockers
        and not threshold_failures
    )
    owner_dimension_failures = {
        field: {"minimum": minimums[field], "required": 10.0}
        for field in QUALITY_DIMENSIONS
        if minimums[field] != 10.0
    }
    owner_exact_10 = platform_pass and not owner_dimension_failures
    return {
        "policy": "tiered_audiobook_acceptance_v1_english_premium",
        "platform_thresholds": PLATFORM_THRESHOLDS,
        "platform_screen_pass": platform_pass,
        "owner_exact_10_pass": owner_exact_10,
        "next_private_stage_authorized": owner_exact_10,
        "minimum_scores": minimums,
        "threshold_failures": threshold_failures,
        "owner_exact_10_dimension_failures": owner_dimension_failures,
        "fatal_flags": fatal,
        "sample_blockers": sample_blockers,
    }


def judge_exact_audio_sample(client: Any, args: Any, sample: dict[str, Any]) -> dict[str, Any]:
    """Call the same schema-3 audio judge while declaring the true WAV format."""
    audio_path = Path(sample["sample_audio_path"])
    if not audio_path.is_file():
        return {**sample, "scores": {}, "blocker_reason": "LISTENING_QA_SAMPLE_MISSING"}
    properties = {field: {"type": "number"} for field in LISTENING_THRESHOLDS}
    properties.update({field: {"type": "boolean"} for field in BINARY_LISTENING_FLAGS})
    properties.update(
        {
            "frontmatter_present": {"type": "boolean"},
            "notes": {"type": "string"},
            "blocker_reason": {"type": "string"},
        }
    )
    tool = {
        "type": "function",
        "function": {
            "name": "record_listening_quality",
            "description": "Record strict schema-3 audiobook listening QA for one exact private sample.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    prompt = (
        "Independently judge this exact private English literary-audiobook sample. Return only the function call. "
        "Quality scores are 0-10; confidence_score is 0-1. Score 10 only when the dimension is genuinely flawless. "
        "The active English premium screen requires quality dimensions >=9.0, overall >=9.3, confidence >=0.90, "
        "and no fatal flags; the separate owner target requires every quality dimension exactly 10.0. Penalize "
        "mispronunciation, weak emotion, unnatural pauses, pacing defects, mechanical or robotic cadence, choppy "
        f"joins, and listener fatigue. The work is {args.title} by {args.author}."
    )
    try:
        response = client.chat.completions.create(
            model=EXPECTED_ENV["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
                                "format": "wav",
                            },
                        },
                    ],
                }
            ],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": "record_listening_quality"}},
            temperature=0,
            max_completion_tokens=500,
        )
        message = response.choices[0].message
        arguments = message.tool_calls[0].function.arguments if message.tool_calls else ""
        judgment = json.loads(arguments or "{}")
    except Exception as exc:  # noqa: BLE001
        return {
            **sample,
            "scores": {},
            "judge_flags": {},
            "notes": f"OpenAI listening judge failed: {exc}",
            "blocker_reason": "LISTENING_QA_NOT_RUN",
        }
    if safe_float(judgment.get("confidence_score"), 0.0) > 1.0:
        judgment["confidence_score"] = round(safe_float(judgment.get("confidence_score")) / 10.0, 4)
    return {
        **sample,
        "scores": {field: safe_float(judgment.get(field), 0.0) for field in LISTENING_THRESHOLDS},
        "confidence": safe_float(judgment.get("confidence_score"), 0.0),
        "notes": str(judgment.get("notes") or ""),
        "blocker_reason": str(judgment.get("blocker_reason") or ""),
        "judge_flags": {field: bool(judgment.get(field)) for field in BINARY_LISTENING_FLAGS},
        "frontmatter_present": bool(judgment.get("frontmatter_present")),
        "raw_judgment": judgment,
    }


def execute(
    evidence_path: Path,
    output_path: Path,
    lock_path: Path,
    *,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    judge: Callable[[Any, Any, dict[str, Any]], dict[str, Any]] = judge_exact_audio_sample,
    client_factory: Callable[[], Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    assert_nonpublic_output(output_path)
    process_env = dict(os.environ if env is None else env)
    errors = runtime_gate_errors(process_env)
    if errors:
        result = {"status": "BLOCKED_RUNTIME_GATES", "blockers": errors, "provider_calls_ran": False}
        write_json(output_path, result)
        return 2, result
    evidence, samples, sample_fingerprint = load_evidence(evidence_path)
    budget = budget_guard(process_env)
    if budget["status"] != "PASS":
        result = {"status": "BLOCKED_BUDGET", "budget": budget, "provider_calls_ran": False}
        write_json(output_path, result)
        return 2, result
    if prior_attempt_completed(output_path, sample_fingerprint):
        return 4, {
            "status": "BLOCKED_REPEAT_ATTEMPT",
            "sample_fingerprint": sample_fingerprint,
            "provider_calls_ran": False,
        }

    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    preflight: dict[str, Any] = {
        "schema_version": 1,
        "status": "DRY_RUN_PASS" if dry_run else "READY",
        "scope": "PRIVATE_COP_REPRESENTATIVE_SCREEN_ONLY_NOT_RELEASE_EVIDENCE",
        "approved_scope": SCOPE,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "sample_fingerprint": sample_fingerprint,
        "evidence_path": str(evidence_path),
        "evidence_sha256": sha256_file(evidence_path),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
        "sample_count": len(samples),
        "sample_bindings": samples,
        "judge": "openai:gpt-audio",
        "rubric_version": LISTENING_QA_RUBRIC_VERSION,
        "hook_version": LISTENING_QA_HOOK_VERSION,
        "budget": budget,
        "provider_calls_ran": False,
        "full_title_generated": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_gate_mutated": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
        "objective_evidence_status": evidence["status"],
    }
    if dry_run:
        write_json(output_path, preflight)
        return 0, preflight

    if client_factory is None:
        from openai import OpenAI  # noqa: PLC0415

        client_factory = OpenAI
    args = SimpleNamespace(slug=SLUG, title=TITLE, author=AUTHOR, language=LANGUAGE)
    judged: list[dict[str, Any]] = []
    provider_calls_ran = False
    error = ""
    started_at = iso_now()
    try:
        # Recheck immediately before acquisition so a concurrent holder cannot be overwritten.
        if lock_path.read_bytes() != original_lock:
            raise CopKokoroListeningQAError("paid_tts.lock changed before acquisition")
        atomic_write(
            lock_path,
            json.dumps(acquired_lock_payload(lock, budget), ensure_ascii=False, indent=2).encode() + b"\n",
        )
        acquired = json.loads(lock_path.read_text(encoding="utf-8"))
        if acquired.get("current_holder") != HOLDER or acquired.get("allowed_slugs") != [SLUG]:
            raise CopKokoroListeningQAError("paid_tts.lock acquisition scope mismatch")
        client = client_factory()
        for sample in samples:
            provider_calls_ran = True
            judged.append(judge(client, args, sample))
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    lock_restored = lock_path.read_bytes() == original_lock
    gate = evaluate_judgments(judged)
    if not lock_restored:
        gate["next_private_stage_authorized"] = False
        error = error or "paid_tts.lock was not restored byte-for-byte"
    if error:
        status, code = "PRIVATE_COP_LISTENING_QA_ERROR", 3
    elif gate["owner_exact_10_pass"]:
        status, code = "PRIVATE_COP_REPRESENTATIVE_EXACT_10_PASS_NOT_RELEASE_EVIDENCE", 0
    elif gate["platform_screen_pass"]:
        status, code = "PRIVATE_COP_PLATFORM_PASS_OWNER_EXACT_10_NOT_MET", 5
    else:
        status, code = "PRIVATE_COP_LISTENING_QA_BLOCKED", 3
    result = {
        **preflight,
        "status": status,
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "actual_provider_billing": "NOT_REPORTED",
        "judged_samples": judged,
        "listening_gate": gate,
        "error": error or None,
        "lock_restored": lock_restored,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "release_blockers_preserved": [
            "FOUR_SAMPLE_SCREEN_IS_NOT_SIX_SAMPLE_FULL_TITLE_RELEASE_EVIDENCE",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "COP_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        ],
    }
    write_json(output_path, result)
    return code, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code, result = execute(
        args.evidence.expanduser().resolve(),
        args.output.expanduser().resolve(),
        args.paid_lock.expanduser().resolve(),
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output),
                "provider_calls_ran": result.get("provider_calls_ran", False),
                "listening_gate": result.get("listening_gate", {}),
                "blockers": result.get("blockers", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
