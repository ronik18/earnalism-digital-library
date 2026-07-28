#!/usr/bin/env python3
"""Judge the exact Gift VoxCPM2 v3.90 adversarial sample.

The single paid call is permitted only after exact local ASR/source,
coverage, order, first/last and word-timestamp evidence passes.  The runner
acquires and restores ``paid_tts.lock`` byte-for-byte.  It cannot synthesize,
upload, publish or mutate release truth.
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
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
SCOPE = "gift_voxcpm2_v390_section13_listening_qa"
HOLDER = "sprint1_gift_voxcpm2_v390_listening_qa"
MODEL = "gpt-audio"
EXPECTED_EVIDENCE_SHA256 = "eb9c078b8c7ed0ef2626ea4c74473982656adeea0c8f9a0829bbde3253c415a8"
EXPECTED_ATTEMPT_FINGERPRINT = "390655d6c5bbeb74a3670ef91bde612404374d1beffa89f80471d1806cb8bb91"
EXPECTED_ASR_FINGERPRINT = "e949c338e47ddf6e445a7ca050416f2a8852bc7364826f0169c84b787535758a"
EXPECTED_SOURCE_SHA256 = "be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e"
EXPECTED_SOURCE_TEXT_SHA256 = "f4d90dfa2ea8c93e8a1bd1d4cc72a52028ddcffff3020cf966fdc7a90a80d1b7"
EXPECTED_AUDIO_SHA256 = "785145a429cefb07ecef3239a9b602d4508dc27528dd28f4619a10900a1adb90"
EXPECTED_AUDIO_SIZE = 3_486_764
EXPECTED_DURATION = 36.32
POLICY = "sprint1_audiobook_acceptance_v3_90"
RUBRIC = "earnalism.literary_listening_schema3.v390"

LISTENING_THRESHOLDS = {
    "naturalness_score": 8.9,
    "pronunciation_score": 8.9,
    "emotional_expression_score": 8.9,
    "punctuation_pause_score": 8.9,
    "pacing_score": 8.9,
    "continuity_score": 8.9,
    "anti_robotic_texture_score": 9.2,
    "anti_choppy_join_score": 9.2,
    "listener_enjoyment_score": 8.9,
    "overall_listening_score": 9.0,
    "confidence_score": 0.9,
}
BINARY_FLAGS = (
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
    "EARNALISM_APPROVE_GIFT_VOXCPM2_V390_LISTENING_QA": "true",
    "EARNALISM_APPROVED_AUDIOBOOK_SLUG": SLUG,
    "EARNALISM_APPROVED_AUDIOBOOK_SCOPE": SCOPE,
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": MODEL,
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.05",
    "MAX_TTS_BUDGET_USD": "0.05",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
}
DEFAULT_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_voxcpm2_int8_v390_section13_20260727.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_voxcpm2_int8_v390_section13_listening_qa_20260727.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


class GiftVoxCPM2ListeningError(RuntimeError):
    """Raised when exact listening prerequisites do not match."""


def iso_now() -> str:
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
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GiftVoxCPM2ListeningError(f"Invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise GiftVoxCPM2ListeningError(f"JSON object required: {path}")
    return value


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
    temporary.replace(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    rendered = f"/{path.resolve().as_posix().lower().strip('/')}/"
    forbidden = ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/")
    if any(marker in rendered for marker in forbidden):
        raise GiftVoxCPM2ListeningError(f"public output is forbidden: {path}")
    atomic_write(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
    )


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise GiftVoxCPM2ListeningError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def runtime_errors(env: Mapping[str, str], *, require_key: bool = True) -> list[str]:
    errors = [
        f"{key} must equal {expected}"
        for key, expected in EXPECTED_ENV.items()
        if env.get(key) != expected
    ]
    if require_key and not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def budget_guard(env: Mapping[str, str]) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        estimate = float(env["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
        stage_cap = float(env["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"])
        total_cap = float(env["MAX_TTS_BUDGET_USD"])
    except (KeyError, TypeError, ValueError):
        estimate = stage_cap = total_cap = math.nan
        blockers.append("Listening estimate and caps must be numeric")
    if not all(math.isfinite(value) and value > 0 for value in (estimate, stage_cap, total_cap)):
        blockers.append("Listening estimate and caps must be positive finite values")
    if estimate != 0.05 or stage_cap != 0.05 or total_cap != 0.05:
        blockers.append("One-sample listening estimate and caps must each equal 0.05 USD")
    if math.isfinite(estimate) and (estimate > stage_cap or estimate > total_cap):
        blockers.append("Listening estimate exceeds an approved cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "sample_count": 1,
        "estimated_usd": estimate,
        "stage_cap_usd": stage_cap,
        "total_cap_usd": total_cap,
        "blockers": blockers,
    }


def load_evidence(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    require_equal(sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = read_json(path)
    require_equal(
        evidence.get("status"),
        "PRIVATE_ADVERSARIAL_SAMPLE_OBJECTIVE_PASS_LISTENING_PENDING",
        "evidence status",
    )
    scope = evidence.get("scope") or {}
    require_equal(scope.get("slug"), SLUG, "scope slug")
    require_equal(scope.get("section_indices"), [13], "scope sections")
    engine = evidence.get("engine") or {}
    require_equal(engine.get("attempt_fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    source = evidence.get("source") or {}
    require_equal(source.get("full_source_sha256"), EXPECTED_SOURCE_SHA256, "source SHA-256")
    samples = evidence.get("samples") or []
    require_equal(len(samples), 1, "sample count")
    sample = samples[0]
    for key, expected in {
        "passage_id": "section-013",
        "source_text_sha256": EXPECTED_SOURCE_TEXT_SHA256,
        "audio_sha256": EXPECTED_AUDIO_SHA256,
        "size_bytes": EXPECTED_AUDIO_SIZE,
        "duration_seconds": EXPECTED_DURATION,
        "sample_rate_hz": 48_000,
        "channels": 1,
        "sample_width_bytes": 2,
        "objective_format_pass": True,
    }.items():
        require_equal(sample.get(key), expected, f"sample {key}")
    audio = Path(str(sample.get("audio_path") or "")).resolve()
    private_root = Path(tempfile.gettempdir()).resolve()
    if not (audio == private_root or private_root in audio.parents):
        raise GiftVoxCPM2ListeningError(f"audio is outside OS private temp: {audio}")
    require_equal(audio.is_file(), True, "private audio exists")
    require_equal(sha256_file(audio), EXPECTED_AUDIO_SHA256, "measured audio SHA-256")
    require_equal(audio.stat().st_size, EXPECTED_AUDIO_SIZE, "measured audio size")
    objective = evidence.get("objective_qa") or {}
    require_equal(objective.get("status"), "PASS", "objective QA status")
    require_equal(objective.get("audio_derived"), True, "objective audio-derived")
    require_equal(objective.get("config_fingerprint"), EXPECTED_ASR_FINGERPRINT, "ASR fingerprint")
    aggregate = objective.get("full_title_aggregate") or {}
    for key, expected in {
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
        require_equal(aggregate.get(key), expected, f"objective aggregate {key}")
    reports = objective.get("reports") or []
    require_equal(len(reports), 1, "objective report count")
    require_equal(reports[0].get("word_timestamp_evidence_valid"), True, "word timestamps")
    require_equal(reports[0].get("pass"), True, "section objective pass")
    binding = {
        "sample_label": "section-013",
        "sample_audio_path": str(audio),
        "sample_audio_hash": EXPECTED_AUDIO_SHA256,
        "sample_audio_size_bytes": EXPECTED_AUDIO_SIZE,
        "sample_audio_duration_seconds": EXPECTED_DURATION,
        "source_text_sha256": EXPECTED_SOURCE_TEXT_SHA256,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "asr_config_fingerprint": EXPECTED_ASR_FINGERPRINT,
    }
    fingerprint = canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "binding": binding,
            "judge_model": MODEL,
            "rubric": RUBRIC,
            "thresholds": LISTENING_THRESHOLDS,
            "binary_flags": BINARY_FLAGS,
        }
    )
    return evidence, binding, fingerprint


def load_idle_lock(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GiftVoxCPM2ListeningError("paid_tts.lock is invalid") from exc
    require_equal(payload.get("status"), "active", "paid lock status")
    require_equal(payload.get("current_holder"), "none", "paid lock holder")
    require_equal(payload.get("allowed_next_holders"), [], "paid lock scheduled holders")
    require_equal(payload.get("allowed_slugs"), [SLUG], "paid lock slug scope")
    return payload


def acquired_lock(lock: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **lock,
        "current_holder": HOLDER,
        "allowed_next_holders": [],
        "holder_started_at": iso_now(),
        "approved_scope": (
            f"{SCOPE}; one exact private 36.32-second sample; estimated maximum "
            "USD 0.05; no synthesis, upload, publication, or release mutation."
        ),
        "allowed_slugs": [SLUG],
        "budget_cap_usd": 0.05,
        "updated_at": iso_now(),
    }


def evaluate(judgment: Mapping[str, Any]) -> dict[str, Any]:
    scores = {
        field: float(judgment.get(field) or 0.0)
        for field in LISTENING_THRESHOLDS
    }
    flags = {
        field: bool(judgment.get(field))
        for field in BINARY_FLAGS
    }
    threshold_failures = {
        field: {"observed": scores[field], "required": threshold}
        for field, threshold in LISTENING_THRESHOLDS.items()
        if scores[field] < threshold
    }
    fatal_flags = sorted(field for field, present in flags.items() if present)
    blocker_reason = str(judgment.get("blocker_reason") or "").strip()
    frontmatter = bool(judgment.get("frontmatter_present"))
    passed = not threshold_failures and not fatal_flags and not blocker_reason and not frontmatter
    return {
        "policy": POLICY,
        "thresholds": LISTENING_THRESHOLDS,
        "scores": scores,
        "judge_flags": flags,
        "threshold_failures": threshold_failures,
        "fatal_flags": fatal_flags,
        "blocker_reason": blocker_reason,
        "frontmatter_present": frontmatter,
        "confidence": scores["confidence_score"],
        "listening_pass": passed,
    }


def parse_judgment(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    required = (
        set(LISTENING_THRESHOLDS)
        | set(BINARY_FLAGS)
        | {"frontmatter_present", "notes", "blocker_reason"}
    )
    return value if isinstance(value, dict) and required.issubset(value) else {}


def judge_audio(client: Any, sample: Mapping[str, Any]) -> dict[str, Any]:
    properties = {
        field: {
            "type": "number",
            "description": (
                "Confidence from 0 to 1"
                if field == "confidence_score"
                else "Score from 0 to 10"
            ),
        }
        for field in LISTENING_THRESHOLDS
    }
    properties.update({field: {"type": "boolean"} for field in BINARY_FLAGS})
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
            "description": "Record all required listening scores and fatal flags.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    prompt = (
        f"Act as a strict literary-audiobook editor. Listen to this exact "
        f"private sample from {TITLE} by {AUTHOR}. Call record_listening_quality "
        "exactly once and populate every field. Judge natural English "
        "pronunciation, emotional truth, punctuation pauses, non-mechanical "
        "pacing, continuity, warmth, and listener enjoyment. A v3.90 pass "
        "requires overall >=9.0, ordinary dimensions >=8.9, anti-robotic and "
        "anti-choppy >=9.2, confidence >=0.90, and no fatal flags or concrete "
        "blocker. Be strict; do not reward source accuracy as performance "
        "quality. Flag robotic texture, mechanical cadence, list rhythm, "
        "choppy joins, fallback TTS, abrupt resets, repeated identical endings, "
        "or placeholder audio whenever audible."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(
                                Path(str(sample["sample_audio_path"])).read_bytes()
                            ).decode("ascii"),
                            "format": "wav",
                        },
                    },
                ],
            }
        ],
        modalities=["text"],
        tools=[tool],
        tool_choice={
            "type": "function",
            "function": {"name": "record_listening_quality"},
        },
        parallel_tool_calls=False,
        temperature=0,
        max_completion_tokens=900,
    )
    calls = response.choices[0].message.tool_calls or []
    raw = str(calls[0].function.arguments or "") if calls else ""
    judgment = parse_judgment(raw)
    if not judgment:
        raise GiftVoxCPM2ListeningError("listening judge returned an incomplete schema")
    return judgment


def prior_attempt_completed(path: Path, fingerprint: str) -> bool:
    if not path.is_file():
        return False
    try:
        prior = read_json(path)
    except GiftVoxCPM2ListeningError:
        return False
    return (
        prior.get("sample_fingerprint") == fingerprint
        and prior.get("provider_calls_ran") is True
    )


def execute(
    *,
    evidence_path: Path,
    output_path: Path,
    lock_path: Path,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    client_factory: Callable[[], Any] | None = None,
    judge: Callable[[Any, Mapping[str, Any]], dict[str, Any]] = judge_audio,
) -> tuple[int, dict[str, Any]]:
    process_env = dict(os.environ if env is None else env)
    errors = runtime_errors(process_env, require_key=not dry_run)
    if errors:
        result = {
            "status": "BLOCKED_RUNTIME_GATES",
            "blockers": errors,
            "provider_calls_ran": False,
        }
        write_json(output_path, result)
        return 2, result
    evidence, sample, fingerprint = load_evidence(evidence_path)
    budget = budget_guard(process_env)
    if budget["status"] != "PASS":
        result = {
            "status": "BLOCKED_BUDGET",
            "budget": budget,
            "provider_calls_ran": False,
        }
        write_json(output_path, result)
        return 2, result
    if prior_attempt_completed(output_path, fingerprint):
        return 4, {
            "status": "BLOCKED_REPEAT_ATTEMPT",
            "sample_fingerprint": fingerprint,
            "provider_calls_ran": False,
        }
    original_lock = lock_path.read_bytes()
    lock = load_idle_lock(original_lock)
    preflight = {
        "schema": "earnalism.gift_voxcpm2_v390_listening_qa.v1",
        "generated_at": iso_now(),
        "status": "DRY_RUN_PASS" if dry_run else "READY",
        "scope": SCOPE,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "sample_fingerprint": fingerprint,
        "evidence_path": str(evidence_path),
        "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
        "sample_binding": sample,
        "objective_status": evidence["status"],
        "judge": f"openai:{MODEL}",
        "rubric": RUBRIC,
        "budget": budget,
        "provider_calls_ran": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
        "safety": {
            "audio_generated": False,
            "uploaded": False,
            "published": False,
            "release_gate_mutated": False,
            "public_audio_status": "AUDIO_HIDDEN",
        },
    }
    if dry_run:
        write_json(output_path, preflight)
        return 0, preflight
    if client_factory is None:
        from openai import OpenAI  # noqa: PLC0415

        client_factory = OpenAI
    provider_calls_ran = False
    error = ""
    judgment: dict[str, Any] = {}
    try:
        if lock_path.read_bytes() != original_lock:
            raise GiftVoxCPM2ListeningError("paid_tts.lock changed before acquisition")
        atomic_write(
            lock_path,
            json.dumps(acquired_lock(lock), ensure_ascii=False, indent=2).encode("utf-8")
            + b"\n",
        )
        provider_calls_ran = True
        judgment = judge(client_factory(), sample)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)
    lock_restored = lock_path.read_bytes() == original_lock
    gate = evaluate(judgment)
    if not lock_restored:
        gate["listening_pass"] = False
        error = error or "paid_tts.lock was not restored byte-for-byte"
    if error:
        status, code = "PRIVATE_ADVERSARIAL_LISTENING_ERROR_AUDIO_HIDDEN", 3
    elif gate["listening_pass"]:
        status, code = (
            "PRIVATE_ADVERSARIAL_LISTENING_PASS_REPRESENTATIVE_EXPANSION_AUTHORIZED",
            0,
        )
    else:
        status, code = "PRIVATE_ADVERSARIAL_LISTENING_FAIL_AUDIO_HIDDEN", 3
    result = {
        **preflight,
        "generated_at": iso_now(),
        "status": status,
        "provider_calls_ran": provider_calls_ran,
        "actual_provider_billing": "NOT_REPORTED",
        "raw_judgment": judgment,
        "listening_gate": gate,
        "error": error or None,
        "lock_restored": lock_restored,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "release_eligible": False,
        "blockers_to_release": (
            [
                "REMAINING_REPRESENTATIVE_PASSAGES_NOT_RUN",
                "FULL_TITLE_NOT_AUTHORIZED",
                "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
            ]
            if gate["listening_pass"] and not error
            else [
                "ADVERSARIAL_LISTENING_QA_FAILED",
                "VOXCPM2_V390_EXPANSION_STOPPED",
                "FULL_TITLE_NOT_AUTHORIZED",
                "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
            ]
        ),
        "next_exact_command": (
            "EARNALISM_APPROVE_GIFT_VOXCPM2_V390_REPRESENTATIVE=true "
            "PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/"
            "sprint1_gift_voxcpm2_v390_representative.py --execute "
            "--section-indices 1,7,17,18,19"
            if gate["listening_pass"] and not error
            else "Select a materially different commercially permitted narration family."
        ),
    }
    write_json(output_path, result)
    return code, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, result = execute(
            evidence_path=args.evidence.resolve(),
            output_path=args.output.resolve(),
            lock_path=args.paid_lock.resolve(),
            dry_run=args.dry_run,
        )
    except (OSError, GiftVoxCPM2ListeningError) as exc:
        print(json.dumps({"status": "BLOCKED", "blocker": str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
