#!/usr/bin/env python3
"""Run one strict, private listening review for the Pride Chatterbox pilot.

The wrapper accepts only a caller-hash-bound objective-pass pilot report and
its exact private WAV. It reads ``paid_tts.lock`` without ever writing it and
permits at most one listening-judge call inside the existing Pride-only
USD 0.20 listening scope. It contains no synthesis, upload, publication,
catalog mutation, release mutation, or public-asset code path.
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
import tempfile
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[3]
SLUG = "pride-and-prejudice"
TITLE = "Pride and Prejudice"
AUTHOR = "Jane Austen"
SCOPE = "pride_chatterbox_v3_one_sample_listening_qa"
MODEL = "gpt-audio"
RUBRIC = "earnalism.literary_listening_schema3.pride_strict_92"
PILOT_SCHEMA = "earnalism.pride_chatterbox_v3_private_pilot.v1"
PILOT_STATUS = "REPRESENTATIVE_OBJECTIVE_PASS_LISTENING_REVIEW_REQUIRED"
PILOT_POLICY_SHA256 = (
    "f1cb28a41004bc49e9796bc91cbc584f94fb361837afbd9d74b277ab73e38540"
)
EXPECTED_SOURCE_SHA256 = (
    "fcf234e0476cc6af8b3f604399bf3d7c4b72931bdf2af276ab4cc78caf938d5c"
)
EXPECTED_PASSAGE_SHA256 = (
    "e51782a522b817e8c1e116fdbffd2841a3327e44ad7c16dd655e5ae2b235680b"
)
PASSAGE_ID = "chapter-001-dialogue-01"
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
MAX_LISTENING_SCOPE_USD = 0.20
LOCK_SCOPE = (
    "Pride and Prejudice four-sample independent listening QA only; "
    "maximum estimated 0.20 USD; no paid TTS, upload, publication, "
    "or release mutation"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
DEFAULT_PRIVATE_ROOT = (
    Path(tempfile.gettempdir()) / "earnalism-pride-chatterbox-v3-private"
)

ORDINARY_SCORE_FIELDS = (
    "naturalness_score",
    "pronunciation_score",
    "emotional_expression_score",
    "punctuation_pause_score",
    "pacing_score",
    "continuity_score",
    "listener_enjoyment_score",
)
ANTI_SCORE_FIELDS = (
    "anti_robotic_texture_score",
    "anti_choppy_join_score",
)
LISTENING_THRESHOLDS = {
    **{field: 9.2 for field in ORDINARY_SCORE_FIELDS},
    **{field: 9.2 for field in ANTI_SCORE_FIELDS},
    "overall_listening_score": 9.2,
    "confidence_score": 0.90,
}
FATAL_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "repeated_identical_sentence_endings_detected",
    "abrupt_tts_resets_detected",
    "placeholder_audio_detected",
)
EXPECTED_ENV = {
    "EARNALISM_APPROVE_PRIDE_CHATTERBOX_V3_LISTENING_QA": "true",
    "EARNALISM_APPROVED_AUDIOBOOK_SLUG": SLUG,
    "EARNALISM_APPROVED_AUDIOBOOK_SCOPE": SCOPE,
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": MODEL,
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
}


class PrideChatterboxListeningError(RuntimeError):
    """Raised when the exact listening-only contract is not satisfied."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrideChatterboxListeningError(message)


def require_equal(observed: Any, expected: Any, label: str) -> None:
    require(
        observed == expected,
        f"{label} changed: expected {expected!r}, observed {observed!r}",
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrideChatterboxListeningError(f"invalid JSON: {path}") from exc
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def private_path(path: Path, *, must_exist: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    require(
        resolved == temporary_root or temporary_root in resolved.parents,
        f"private path must stay under OS temporary storage: {temporary_root}",
    )
    repository = ROOT.resolve()
    require(
        not (resolved == repository or repository in resolved.parents),
        "private path may not be inside the repository",
    )
    lowered = f"/{resolved.as_posix().lower().strip('/')}/"
    for marker in ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/"):
        require(marker not in lowered, f"public path is forbidden: {resolved}")
    if must_exist:
        require(resolved.is_file(), f"private file is missing: {resolved}")
    return resolved


def write_private_json(path: Path, payload: Mapping[str, Any]) -> None:
    target = private_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    os.chmod(target, 0o600)


def objective_report_errors(report: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    def score_passes(value: Any) -> bool:
        observed = float(value)
        return math.isfinite(observed) and ASR_SCORE_MIN <= observed <= 10.0

    def coverage_passes(value: Any) -> bool:
        observed = float(value)
        return math.isfinite(observed) and ASR_COVERAGE_MIN <= observed <= 1.0

    checks = {
        "score": score_passes,
        "coverage": coverage_passes,
        "first_words_match": lambda value: value is True,
        "last_words_match": lambda value: value is True,
        "ordered_content_integrity_pass": lambda value: value is True,
        "no_missing_content": lambda value: value is True,
        "no_duplicate_content": lambda value: value is True,
        "no_reordered_content": lambda value: value is True,
        "no_unexpected_content": lambda value: value is True,
        "word_timestamp_evidence_valid": lambda value: value is True,
        "pass": lambda value: value is True,
    }
    for field, predicate in checks.items():
        try:
            passed = predicate(report.get(field))
        except (TypeError, ValueError):
            passed = False
        if not passed:
            errors.append(f"objective report {field} did not pass")
    if report.get("word_timestamp_anomalies") not in (None, []):
        errors.append("objective report contains timestamp anomalies")
    if not report.get("audio_derived_word_timestamps"):
        errors.append("objective report has no audio-derived word timestamps")
    return errors


def load_objective_pass(
    pilot_report_path: Path,
    *,
    expected_pilot_report_sha256: str,
    expected_audio_sha256: str,
) -> Tuple[dict[str, Any], dict[str, Any], str]:
    require(is_sha256(expected_pilot_report_sha256), "pilot report SHA-256 is invalid")
    require(is_sha256(expected_audio_sha256), "audio SHA-256 is invalid")
    report_path = private_path(pilot_report_path, must_exist=True)
    require_equal(
        sha256_file(report_path),
        expected_pilot_report_sha256,
        "measured pilot report SHA-256",
    )
    report = read_json(report_path)
    require_equal(report.get("schema_version"), PILOT_SCHEMA, "pilot schema")
    require_equal(report.get("status"), PILOT_STATUS, "pilot status")
    require_equal(report.get("slug"), SLUG, "pilot slug")
    require_equal(report.get("title"), TITLE, "pilot title")
    require_equal(report.get("author"), AUTHOR, "pilot author")
    require_equal(report.get("policy_sha256"), PILOT_POLICY_SHA256, "pilot policy")
    require_equal(
        (report.get("source") or {}).get("source_sha256"),
        EXPECTED_SOURCE_SHA256,
        "pilot source SHA-256",
    )
    require_equal(
        (report.get("source") or {}).get("passage_text_sha256"),
        EXPECTED_PASSAGE_SHA256,
        "pilot passage SHA-256",
    )
    require_equal(
        (report.get("source") or {}).get("passage_id"),
        PASSAGE_ID,
        "pilot passage ID",
    )
    scope = report.get("scope") or {}
    require_equal(scope.get("sample_count"), 1, "pilot sample count")
    for field in (
        "upload_allowed",
        "publication_allowed",
        "release_gate_mutation_allowed",
        "full_title_generation_allowed",
    ):
        require_equal(scope.get(field), False, f"pilot scope {field}")
    require_equal(report.get("release_ready"), False, "pilot release readiness")
    require_equal(
        report.get("public_audio_status"),
        "AUDIO_HIDDEN_NOT_APPROVED",
        "pilot public audio state",
    )
    require_equal(
        report.get("next_transition"),
        "BOUNDED_LISTENING_REVIEW_ONLY",
        "pilot transition",
    )
    lock = report.get("paid_tts_lock") or {}
    require_equal(lock.get("access"), "READ_ONLY", "pilot lock access")
    require_equal(lock.get("touched"), False, "pilot lock touched")
    require_equal(lock.get("unchanged"), True, "pilot lock unchanged")
    require_equal(
        lock.get("sha256_after"),
        lock.get("sha256_before"),
        "pilot lock before/after hash",
    )
    attempt_fingerprint = str(report.get("attempt_fingerprint") or "")
    require(is_sha256(attempt_fingerprint), "pilot attempt fingerprint is invalid")

    audio = report.get("audio") or {}
    require_equal(audio.get("audio_sha256"), expected_audio_sha256, "pilot audio hash")
    audio_path = private_path(
        Path(str(audio.get("audio_path") or "")),
        must_exist=True,
    )
    require_equal(sha256_file(audio_path), expected_audio_sha256, "measured audio hash")
    require_equal(
        audio_path.stat().st_size,
        int(audio.get("audio_size_bytes") or 0),
        "measured audio size",
    )
    require_equal(audio.get("objective_format_pass"), True, "audio format gate")
    require_equal(audio.get("channels"), 1, "audio channels")
    duration = float(audio.get("duration_seconds") or 0.0)
    require(
        math.isfinite(duration) and duration > 0.0,
        "audio duration is invalid",
    )
    require(int(audio.get("sample_rate_hz") or 0) > 0, "audio sample rate is invalid")

    objective = report.get("objective_asr") or {}
    require_equal(objective.get("status"), "PASS", "objective ASR status")
    require_equal(objective.get("audio_derived"), True, "objective ASR derivation")
    require_equal(
        float(objective.get("required_score") or 0.0),
        ASR_SCORE_MIN,
        "objective score floor",
    )
    require_equal(
        float(objective.get("required_coverage") or 0.0),
        ASR_COVERAGE_MIN,
        "objective coverage floor",
    )
    objective_report = objective.get("report") or {}
    errors = objective_report_errors(objective_report)
    require(not errors, "; ".join(errors))

    binding = {
        "pilot_report_path": str(report_path),
        "pilot_report_sha256": expected_pilot_report_sha256,
        "pilot_attempt_fingerprint": attempt_fingerprint,
        "audio_path": str(audio_path),
        "audio_sha256": expected_audio_sha256,
        "audio_size_bytes": audio_path.stat().st_size,
        "duration_seconds": float(audio["duration_seconds"]),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "passage_id": PASSAGE_ID,
        "passage_text_sha256": EXPECTED_PASSAGE_SHA256,
        "objective_asr_score": float(objective_report["score"]),
        "objective_coverage": float(objective_report["coverage"]),
    }
    fingerprint = canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "binding": binding,
            "model": MODEL,
            "rubric": RUBRIC,
            "thresholds": LISTENING_THRESHOLDS,
            "fatal_flags": FATAL_FLAGS,
        }
    )
    return report, binding, fingerprint


def read_pride_listening_lock(path: Path) -> Tuple[bytes, dict[str, Any]]:
    require(path.is_file(), f"paid_tts.lock is missing: {path}")
    raw = path.read_bytes()
    try:
        lock = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrideChatterboxListeningError("paid_tts.lock is invalid") from exc
    require_equal(lock.get("status"), "active", "paid lock status")
    require_equal(lock.get("current_holder"), "none", "paid lock holder")
    require_equal(lock.get("allowed_next_holders"), [], "paid lock next holders")
    require_equal(lock.get("allowed_slugs"), [SLUG], "paid lock allowed slugs")
    require_equal(lock.get("requested_slug"), SLUG, "paid lock requested slug")
    require_equal(lock.get("approved_scope"), LOCK_SCOPE, "paid lock approved scope")
    return raw, lock


def assert_lock_unchanged(path: Path, before: bytes) -> None:
    require(path.read_bytes() == before, "paid_tts.lock changed during listening QA")


def budget_guard(env: Mapping[str, str]) -> dict[str, Any]:
    names = (
        "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD",
        "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
        "MAX_TTS_BUDGET_USD",
    )
    blockers: list[str] = []
    values: dict[str, float] = {}
    for name in names:
        try:
            value = float(env[name])
        except (KeyError, TypeError, ValueError):
            value = math.nan
        values[name] = value
        if not math.isfinite(value) or value <= 0:
            blockers.append(f"{name} must be a positive finite number")
        elif value > MAX_LISTENING_SCOPE_USD:
            blockers.append(
                f"{name} exceeds the Pride listening-only USD "
                f"{MAX_LISTENING_SCOPE_USD:.2f} scope"
            )
    estimate = values[names[0]]
    stage_cap = values[names[1]]
    total_cap = values[names[2]]
    if all(math.isfinite(value) for value in (estimate, stage_cap, total_cap)):
        if estimate > stage_cap or estimate > total_cap:
            blockers.append("listening estimate exceeds an approved cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "sample_count": 1,
        "estimated_usd": estimate,
        "stage_cap_usd": stage_cap,
        "total_cap_usd": total_cap,
        "scope_cap_usd": MAX_LISTENING_SCOPE_USD,
        "blockers": blockers,
    }


def runtime_errors(env: Mapping[str, str], *, require_key: bool) -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if env.get(name) != expected
    ]
    if require_key and not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def parse_judgment(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    required = (
        set(LISTENING_THRESHOLDS)
        | set(FATAL_FLAGS)
        | {"frontmatter_present", "notes", "blocker_reason"}
    )
    return value if isinstance(value, dict) and required.issubset(value) else {}


def evaluate(judgment: Mapping[str, Any]) -> dict[str, Any]:
    scores: dict[str, float] = {}
    invalid_fields: list[str] = []
    for field in LISTENING_THRESHOLDS:
        try:
            value = float(judgment[field])
        except (KeyError, TypeError, ValueError):
            value = 0.0
            invalid_fields.append(field)
        maximum = 1.0 if field == "confidence_score" else 10.0
        if not math.isfinite(value) or value < 0.0 or value > maximum:
            invalid_fields.append(field)
        scores[field] = value
    flags = {field: bool(judgment.get(field)) for field in FATAL_FLAGS}
    threshold_failures = {
        field: {"observed": scores[field], "required": threshold}
        for field, threshold in LISTENING_THRESHOLDS.items()
        if scores[field] < threshold
    }
    fatal_flags = sorted(field for field, present in flags.items() if present)
    blocker_reason = str(judgment.get("blocker_reason") or "").strip()
    frontmatter = bool(judgment.get("frontmatter_present"))
    passed = not (
        invalid_fields
        or threshold_failures
        or fatal_flags
        or blocker_reason
        or frontmatter
    )
    return {
        "rubric": RUBRIC,
        "thresholds": LISTENING_THRESHOLDS,
        "scores": scores,
        "invalid_fields": sorted(invalid_fields),
        "threshold_failures": threshold_failures,
        "judge_flags": flags,
        "fatal_flags": fatal_flags,
        "blocker_reason": blocker_reason,
        "frontmatter_present": frontmatter,
        "confidence": scores["confidence_score"],
        "listening_pass": passed,
    }


def judge_audio(client: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
    properties = {
        field: {
            "type": "number",
            "description": (
                "Confidence from 0 to 1"
                if field == "confidence_score"
                else "Strict score from 0 to 10"
            ),
        }
        for field in LISTENING_THRESHOLDS
    }
    properties.update({field: {"type": "boolean"} for field in FATAL_FLAGS})
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
            "name": "record_pride_listening_quality",
            "description": "Record every strict listening dimension and fatal flag.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    prompt = (
        f"Act as a strict premium literary-audiobook editor. Listen to this one "
        f"private Chatterbox V3 passage from {TITLE} by {AUTHOR}. Call "
        "record_pride_listening_quality exactly once and populate every field. "
        "Judge performance independently from source accuracy. A pass requires "
        "overall and every ordinary dimension >=9.2, anti-robotic and "
        "anti-choppy >=9.2, confidence >=0.90, and no fatal flag, frontmatter, "
        "or concrete blocker. Flag robotic texture, mechanical cadence, list "
        "rhythm, choppy joins, fallback TTS, repeated identical endings, abrupt "
        "resets, or placeholder audio whenever audible."
    )
    encoded_audio = base64.b64encode(
        Path(str(binding["audio_path"])).read_bytes()
    ).decode("ascii")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": encoded_audio, "format": "wav"},
                    },
                ],
            }
        ],
        modalities=["text"],
        tools=[tool],
        tool_choice={
            "type": "function",
            "function": {"name": "record_pride_listening_quality"},
        },
        parallel_tool_calls=False,
        temperature=0,
        max_completion_tokens=900,
    )
    calls = response.choices[0].message.tool_calls or []
    raw = str(calls[0].function.arguments or "") if calls else ""
    judgment = parse_judgment(raw)
    if not judgment:
        raise PrideChatterboxListeningError(
            "listening judge returned an incomplete schema"
        )
    return judgment


def prior_attempt_completed(path: Path, fingerprint: str) -> bool:
    if not path.is_file():
        return False
    try:
        prior = read_json(path)
    except PrideChatterboxListeningError:
        return False
    return (
        prior.get("sample_fingerprint") == fingerprint
        and prior.get("provider_calls_ran") is True
    )


def execute(
    *,
    pilot_report_path: Path,
    expected_pilot_report_sha256: str,
    expected_audio_sha256: str,
    output_path: Path,
    lock_path: Path,
    dry_run: bool = False,
    env: Optional[Mapping[str, str]] = None,
    client_factory: Optional[Callable[[], Any]] = None,
    judge: Callable[[Any, Mapping[str, Any]], dict[str, Any]] = judge_audio,
) -> Tuple[int, dict[str, Any]]:
    output_path = private_path(output_path)
    process_env = dict(os.environ if env is None else env)
    errors = runtime_errors(process_env, require_key=not dry_run)
    if errors:
        result = {
            "status": "BLOCKED_RUNTIME_GATES",
            "blockers": errors,
            "provider_calls_ran": False,
        }
        write_private_json(output_path, result)
        return 2, result
    pilot, binding, fingerprint = load_objective_pass(
        pilot_report_path,
        expected_pilot_report_sha256=expected_pilot_report_sha256,
        expected_audio_sha256=expected_audio_sha256,
    )
    budget = budget_guard(process_env)
    if budget["status"] != "PASS":
        result = {
            "status": "BLOCKED_BUDGET",
            "budget": budget,
            "provider_calls_ran": False,
        }
        write_private_json(output_path, result)
        return 2, result
    if prior_attempt_completed(output_path, fingerprint):
        return 4, {
            "status": "BLOCKED_REPEAT_ATTEMPT",
            "sample_fingerprint": fingerprint,
            "provider_calls_ran": False,
        }
    original_lock, lock = read_pride_listening_lock(lock_path)
    preflight = {
        "schema_version": "earnalism.pride_chatterbox_v3_one_sample_listening_qa.v1",
        "generated_at": utc_now(),
        "status": "DRY_RUN_PASS" if dry_run else "READY",
        "scope": SCOPE,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "sample_count": 1,
        "sample_fingerprint": fingerprint,
        "pilot_status": pilot["status"],
        "sample_binding": binding,
        "judge": f"openai:{MODEL}",
        "rubric": RUBRIC,
        "budget": budget,
        "provider_calls_ran": False,
        "lock": {
            "path": str(lock_path),
            "access": "READ_ONLY",
            "approved_scope": lock["approved_scope"],
            "sha256_before": hashlib.sha256(original_lock).hexdigest(),
            "touched": False,
        },
        "safety": {
            "audio_generated": False,
            "uploaded": False,
            "published": False,
            "catalog_mutated": False,
            "release_gate_mutated": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
        },
        "release_eligible": False,
    }
    assert_lock_unchanged(lock_path, original_lock)
    if dry_run:
        preflight["lock"]["sha256_after"] = hashlib.sha256(
            lock_path.read_bytes()
        ).hexdigest()
        preflight["lock"]["unchanged"] = True
        write_private_json(output_path, preflight)
        return 0, preflight
    if client_factory is None:
        from openai import OpenAI  # noqa: PLC0415

        client_factory = OpenAI
    provider_calls_ran = False
    judgment: dict[str, Any] = {}
    error = ""
    try:
        assert_lock_unchanged(lock_path, original_lock)
        provider_calls_ran = True
        judgment = judge(client_factory(), binding)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    lock_unchanged = lock_path.read_bytes() == original_lock
    gate = evaluate(judgment)
    if not lock_unchanged:
        gate["listening_pass"] = False
        error = error or "paid_tts.lock changed during listening QA"
    if error:
        status, code = "PRIVATE_ONE_SAMPLE_LISTENING_ERROR_AUDIO_HIDDEN", 3
    elif gate["listening_pass"]:
        status, code = (
            "PRIVATE_ONE_SAMPLE_LISTENING_PASS_ADDITIONAL_SAMPLES_REQUIRED",
            0,
        )
    else:
        status, code = "PRIVATE_ONE_SAMPLE_LISTENING_FAIL_AUDIO_HIDDEN", 3
    result = {
        **preflight,
        "generated_at": utc_now(),
        "status": status,
        "provider_calls_ran": provider_calls_ran,
        "actual_provider_billing": "NOT_REPORTED",
        "raw_judgment": judgment,
        "listening_gate": gate,
        "error": error or None,
        "lock": {
            **preflight["lock"],
            "sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            "unchanged": lock_unchanged,
        },
        "release_eligible": False,
        "blockers_to_release": (
            [
                "THREE_ADDITIONAL_INDEPENDENT_SAMPLES_NOT_RUN",
                "FULL_TITLE_NOT_AUTHORIZED",
                "FULL_RELEASE_GATES_NOT_RUN",
            ]
            if gate["listening_pass"] and not error
            else [
                "STRICT_ONE_SAMPLE_LISTENING_QA_FAILED",
                "FULL_TITLE_NOT_AUTHORIZED",
                "FULL_RELEASE_GATES_NOT_RUN",
            ]
        ),
        "next_transition": (
            "PREPARE_THREE_ADDITIONAL_OBJECTIVE_PASS_SAMPLES"
            if gate["listening_pass"] and not error
            else "SOURCE_BOUND_DELIVERY_REQUIRED"
        ),
    }
    write_private_json(output_path, result)
    return code, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pilot-report", type=Path, required=True)
    parser.add_argument("--expected-pilot-report-sha256", required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PRIVATE_ROOT / "one_sample_listening_qa.json",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, result = execute(
            pilot_report_path=args.pilot_report,
            expected_pilot_report_sha256=args.expected_pilot_report_sha256,
            expected_audio_sha256=args.expected_audio_sha256,
            output_path=args.output,
            lock_path=args.paid_lock,
            dry_run=args.dry_run,
        )
    except (OSError, PrideChatterboxListeningError) as exc:
        print(json.dumps({"status": "BLOCKED", "blocker": str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
