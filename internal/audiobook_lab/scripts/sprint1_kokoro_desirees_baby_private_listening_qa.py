#!/usr/bin/env python3
"""Fail-closed four-sample listening screen for the exact Désirée Kokoro pilot.

Dry-run performs all evidence, hash, budget, path, and lock checks without a
provider call. A later explicitly approved non-dry run is capped at $0.20 and
can only authorize further private work; it is never publication evidence.
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
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
import sys

sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]

from asr_sync_hook import BINARY_LISTENING_FLAGS, LISTENING_THRESHOLDS, safe_float  # noqa: E402
from common import ffprobe_duration, sha256_file  # noqa: E402


SLUG = "dsires-baby"
TITLE = "Désirée's Baby"
AUTHOR = "Kate Chopin"
LANGUAGE = "en"
SCOPE = "desirees_baby_kokoro_representative_listening_qa_v1"
HOLDER = "sprint1_desirees_baby_kokoro_private_listening_qa"
EXPECTED_SAMPLE_COUNT = 4
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = "05a3bf2e322c45b25819908e9260533bf3bca476a8700ee8a1c8a2379b6cbf37"
EXPECTED_SOURCE_SHA256 = "8bfaa9cc56c6e731cd0a5372f7fc4bf1c870ace2261ff7f0b6be44bfd013f8a5"
EXPECTED_ATTEMPT_FINGERPRINT = "b07e30881ec1c1a04944c8f2ba5ccc1b94bf24dc176a784ae12963b9e072f266"
EXPECTED_EXECUTION_FINGERPRINT = "66e0b11cca0c530679ffda849d1069dd4f3f5d6a76ed0b756f719f86256284d3"
EXPECTED_ASR_REPAIR_FINGERPRINT = "63c614ca791064d7bdcaaf8ad595c20198af55295a7d4b3a08d7fe4106ebac9e"
EXPECTED_SAMPLE_BINDINGS = {
    "opening_names": {
        "source_text_sha256": "70745d2ae03039744b0395d76b6de106f0f782c8718066db71d475641e3f521d",
        "audio_sha256": "fece6253f13c7655f195dd5a7ca27f13e33a82b713da6a02e2f3ff6b408b8abf",
        "size_bytes": 1_030_844,
        "duration_seconds": 21.475,
    },
    "maternal_dialogue": {
        "source_text_sha256": "8afc4db73ebe2e947fb6db89732ce84deec1999411b595086adec403dcb08f51",
        "audio_sha256": "b490ace6cac89b381146236b44d0ce8458ca906a3379ddcf0e46adf3e15381ae",
        "size_bytes": 1_218_044,
        "duration_seconds": 25.375,
    },
    "accusation_dialogue": {
        "source_text_sha256": "226f3fc6668a7ca68e472e79781a5917c30e50f8f5522b0e58826c64388d97be",
        "audio_sha256": "981beef0d13a017f7c4e2f43a69262bc3455bdb7f27f113b8478c4e11dfaf953",
        "size_bytes": 1_467_644,
        "duration_seconds": 30.575,
    },
    "final_revelation": {
        "source_text_sha256": "4718ed95408ff638bd2ab0cd75b91dcd85295c84262cb364d85354e93db6398c",
        "audio_sha256": "4cef4b68b3abec2fceaa068fa63b81c0e004061fac7a2fbc6e23c3c502627ced",
        "size_bytes": 1_742_444,
        "duration_seconds": 36.3,
    },
}

QUALITY_FIELDS = tuple(field for field in LISTENING_THRESHOLDS if field != "confidence_score")
PLATFORM_THRESHOLDS = {
    **{field: 9.2 for field in QUALITY_FIELDS},
    "confidence_score": 0.90,
}
EXPECTED_ENV = {
    "EARNALISM_APPROVE_DESIREE_KOKORO_LISTENING_QA": "true",
    "EARNALISM_APPROVED_AUDIOBOOK_SLUG": SLUG,
    "EARNALISM_APPROVED_AUDIOBOOK_SCOPE": SCOPE,
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.20",
    "MAX_TTS_BUDGET_USD": "0.20",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
}
DEFAULT_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "dsires-baby_kokoro_af_bella_listening_qa_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


class DesireeListeningQAError(RuntimeError):
    pass


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def assert_nonpublic(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    if any(marker in rendered for marker in ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/")):
        raise DesireeListeningQAError(f"public path is forbidden: {resolved}")
    return resolved


def assert_private_audio(path: Path) -> Path:
    resolved = assert_nonpublic(path)
    if "/internal/audiobook_lab/private_runs/" not in f"/{resolved.as_posix().lower().strip('/')}/":
        raise DesireeListeningQAError(f"audio is outside private_runs: {resolved}")
    return resolved


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    assert_nonpublic(path)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode() + b"\n")


def canonical_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise DesireeListeningQAError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


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
        per_sample = float(env["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
        stage_cap = float(env["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"])
        total_cap = float(env["MAX_TTS_BUDGET_USD"])
    except (KeyError, TypeError, ValueError):
        per_sample = stage_cap = total_cap = math.nan
        blockers.append("budget values must be numeric")
    estimate = round(per_sample * EXPECTED_SAMPLE_COUNT, 4) if math.isfinite(per_sample) else math.nan
    if per_sample != 0.05:
        blockers.append("estimated cost must be exactly 0.05 USD per sample")
    if stage_cap != 0.20 or total_cap != 0.20:
        blockers.append("stage and total caps must each be exactly 0.20 USD")
    if math.isfinite(estimate) and (estimate > stage_cap or estimate > total_cap):
        blockers.append("four-sample estimate exceeds cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "sample_count": 4,
        "estimated_usd_per_sample": per_sample,
        "estimated_listening_qa_usd": estimate,
        "stage_cap_usd": stage_cap,
        "total_cap_usd": total_cap,
        "blockers": blockers,
    }


def load_evidence(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if not path.is_file():
        raise DesireeListeningQAError(f"evidence missing: {path}")
    _require(sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    _require(evidence.get("status"), EXPECTED_STATUS, "evidence status")
    binding = evidence.get("catalog_binding") or {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "language": LANGUAGE,
        "reader_live": True,
        "audio_hidden": True,
        "normalized_source_sha256": EXPECTED_SOURCE_SHA256,
    }.items():
        _require(binding.get(key), expected, f"catalog_binding.{key}")
    _require((evidence.get("attempt") or {}).get("fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    execution = evidence.get("execution") or {}
    _require(execution.get("execution_fingerprint"), EXPECTED_EXECUTION_FINGERPRINT, "execution fingerprint")
    repair = execution.get("asr_repair") or {}
    _require(repair.get("status"), "PASS", "ASR repair status")
    _require(repair.get("audio_derived"), True, "ASR audio-derived")
    _require(repair.get("repair_fingerprint"), EXPECTED_ASR_REPAIR_FINGERPRINT, "ASR repair fingerprint")
    reports = repair.get("reports") if isinstance(repair.get("reports"), list) else []
    samples = execution.get("samples") if isinstance(execution.get("samples"), list) else []
    _require(len(reports), 4, "ASR report count")
    _require(len(samples), 4, "sample count")
    reports_by_id = {str(item.get("passage_id")): item for item in reports}
    samples_by_id = {str(item.get("passage_id")): item for item in samples}
    _require(set(reports_by_id), set(EXPECTED_SAMPLE_BINDINGS), "ASR passage IDs")
    _require(set(samples_by_id), set(EXPECTED_SAMPLE_BINDINGS), "sample passage IDs")
    verified: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = samples_by_id[passage_id]
        report = reports_by_id[passage_id]
        for key in ("source_text_sha256", "audio_sha256", "size_bytes", "duration_seconds"):
            _require(sample.get(key), expected[key], f"{passage_id} sample {key}")
        audio = assert_private_audio(Path(str(sample.get("audio_path") or "")))
        _require(audio.is_file(), True, f"{passage_id} private audio exists")
        _require(sha256_file(audio), expected["audio_sha256"], f"{passage_id} audio SHA-256")
        _require(audio.stat().st_size, expected["size_bytes"], f"{passage_id} audio size")
        measured_duration = ffprobe_duration(audio) or 0.0
        if abs(measured_duration - expected["duration_seconds"]) > 0.005:
            raise DesireeListeningQAError(f"{passage_id} duration changed")
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
            _require(report.get(key), required, f"{passage_id} ASR {key}")
        verified.append(
            {
                "passage_id": passage_id,
                "sample_label": passage_id,
                "sample_audio_path": str(audio),
                "sample_audio_hash": expected["audio_sha256"],
                "sample_audio_size_bytes": expected["size_bytes"],
                "sample_audio_duration_seconds": expected["duration_seconds"],
                "source_text_sha256": expected["source_text_sha256"],
            }
        )
    fingerprint = canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "execution_fingerprint": EXPECTED_EXECUTION_FINGERPRINT,
            "asr_repair_fingerprint": EXPECTED_ASR_REPAIR_FINGERPRINT,
            "sample_bindings": EXPECTED_SAMPLE_BINDINGS,
            "model": EXPECTED_ENV["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
            "thresholds": PLATFORM_THRESHOLDS,
            "fatal_flags": sorted(BINARY_LISTENING_FLAGS),
        }
    )
    return evidence, verified, fingerprint


def load_lock(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise DesireeListeningQAError("paid_tts.lock is not safely idle")
    if payload.get("allowed_next_holders") != []:
        raise DesireeListeningQAError("paid_tts.lock has a scheduled holder")
    return payload


def prior_attempt_completed(output: Path, fingerprint: str) -> bool:
    if not output.is_file():
        return False
    try:
        prior = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return prior.get("sample_fingerprint") == fingerprint and prior.get("provider_calls_ran") is True


def evaluate_judgments(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    transport_invalid_samples = [
        str(sample.get("sample_label") or sample.get("passage_id") or "unknown")
        for sample in samples
        if any(
            marker in str(sample.get("blocker_reason") or "").lower()
            for marker in ("no audio provided", "listening_qa_not_run")
        )
    ]
    quality_evaluable_samples = [
        sample
        for sample in samples
        if str(sample.get("sample_label") or sample.get("passage_id") or "unknown")
        not in transport_invalid_samples
    ]
    minimums = {
        field: round(
            min(
                (
                    safe_float((sample.get("scores") or {}).get(field), 0.0)
                    for sample in quality_evaluable_samples
                ),
                default=0.0,
            ),
            4,
        )
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
    blockers = [
        f"{sample.get('sample_label')}: {sample.get('blocker_reason')}"
        for sample in samples
        if str(sample.get("blocker_reason") or "").strip()
    ]
    blockers += [
        f"{sample.get('sample_label')}: FRONTMATTER_PRESENT"
        for sample in samples
        if sample.get("frontmatter_present") is True
    ]
    failures = {
        field: {"minimum": minimums[field], "required": threshold}
        for field, threshold in PLATFORM_THRESHOLDS.items()
        if minimums[field] < threshold
    }
    platform_pass = (
        len(samples) == 4
        and not transport_invalid_samples
        and not fatal
        and not blockers
        and not failures
    )
    exact_10 = platform_pass and all(minimums[field] == 10.0 for field in QUALITY_FIELDS)
    return {
        "platform_thresholds": PLATFORM_THRESHOLDS,
        "platform_screen_pass": platform_pass,
        "owner_exact_10_observed": exact_10,
        "next_private_stage_authorized": platform_pass,
        "transport_valid_sample_count": len(quality_evaluable_samples),
        "transport_invalid_sample_count": len(transport_invalid_samples),
        "transport_invalid_samples": transport_invalid_samples,
        "transport_invalid_zeroes_are_quality_scores": False,
        "minimum_scores": minimums,
        "threshold_failures": failures,
        "fatal_flags": fatal,
        "sample_blockers": blockers,
    }


def judge_audio(client: Any, args: Any, sample: dict[str, Any]) -> dict[str, Any]:
    audio = Path(sample["sample_audio_path"])
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
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    prompt = (
        f"Judge this exact private literary-audiobook sample from {args.title} by {args.author}. "
        "Return only the function call. Quality scores are 0-10 and confidence is 0-1. "
        "Fail robotic texture, mechanical cadence, list-reading rhythm, choppy joins, fallback TTS, "
        "mispronunciation, poor emotion, bad pauses, or uneven pacing."
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
                                "data": base64.b64encode(audio.read_bytes()).decode(),
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
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        judgment = json.loads(arguments or "{}")
    except Exception as exc:  # noqa: BLE001
        return {**sample, "scores": {}, "judge_flags": {}, "blocker_reason": "LISTENING_QA_NOT_RUN", "notes": str(exc)}
    if safe_float(judgment.get("confidence_score"), 0.0) > 1.0:
        judgment["confidence_score"] = safe_float(judgment.get("confidence_score")) / 10.0
    return {
        **sample,
        "scores": {field: safe_float(judgment.get(field), 0.0) for field in LISTENING_THRESHOLDS},
        "judge_flags": {field: bool(judgment.get(field)) for field in BINARY_LISTENING_FLAGS},
        "frontmatter_present": bool(judgment.get("frontmatter_present")),
        "notes": str(judgment.get("notes") or ""),
        "blocker_reason": str(judgment.get("blocker_reason") or ""),
    }


def execute(
    evidence_path: Path,
    output_path: Path,
    lock_path: Path,
    *,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    judge: Callable[[Any, Any, dict[str, Any]], dict[str, Any]] = judge_audio,
    client_factory: Callable[[], Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    assert_nonpublic(output_path)
    process_env = dict(os.environ if env is None else env)
    errors = runtime_gate_errors(process_env)
    if errors:
        result = {"status": "BLOCKED_RUNTIME_GATES", "blockers": errors, "provider_calls_ran": False}
        write_json(output_path, result)
        return 2, result
    evidence, samples, fingerprint = load_evidence(evidence_path)
    budget = budget_guard(process_env)
    if budget["status"] != "PASS":
        result = {"status": "BLOCKED_BUDGET", "budget": budget, "provider_calls_ran": False}
        write_json(output_path, result)
        return 2, result
    if prior_attempt_completed(output_path, fingerprint):
        return 4, {"status": "BLOCKED_REPEAT_ATTEMPT", "sample_fingerprint": fingerprint, "provider_calls_ran": False}
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    preflight = {
        "schema_version": 1,
        "status": "DRY_RUN_PASS" if dry_run else "READY",
        "scope": "PRIVATE_DESIREE_REPRESENTATIVE_SCREEN_ONLY_NOT_RELEASE_EVIDENCE",
        "approved_scope": SCOPE,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "sample_fingerprint": fingerprint,
        "evidence_path": str(evidence_path),
        "evidence_sha256": sha256_file(evidence_path),
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "execution_fingerprint": EXPECTED_EXECUTION_FINGERPRINT,
        "asr_repair_fingerprint": EXPECTED_ASR_REPAIR_FINGERPRINT,
        "sample_count": 4,
        "sample_bindings": samples,
        "judge": "openai:gpt-audio",
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
    acquired = dict(lock)
    acquired.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "approved_scope": f"{SCOPE}; four exact samples; maximum estimated 0.20 USD",
            "allowed_slugs": [SLUG],
            "budget_cap_usd": 0.20,
            "holder_started_at": iso_now(),
        }
    )
    judged: list[dict[str, Any]] = []
    provider_calls_ran = False
    error = ""
    try:
        if lock_path.read_bytes() != original_lock:
            raise DesireeListeningQAError("paid_tts.lock changed before acquisition")
        atomic_write(lock_path, json.dumps(acquired, ensure_ascii=False, indent=2).encode() + b"\n")
        client = client_factory()
        args = SimpleNamespace(slug=SLUG, title=TITLE, author=AUTHOR, language=LANGUAGE)
        for sample in samples:
            provider_calls_ran = True
            judged.append(judge(client, args, sample))
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)
    lock_restored = lock_path.read_bytes() == original_lock
    gate = evaluate_judgments(judged)
    if error or not lock_restored:
        status, code = "PRIVATE_DESIREE_LISTENING_QA_ERROR", 3
    elif gate["platform_screen_pass"]:
        status, code = "PRIVATE_DESIREE_REPRESENTATIVE_LISTENING_PASS_NOT_RELEASE_EVIDENCE", 0
    elif gate["transport_invalid_sample_count"] and gate["fatal_flags"]:
        status, code = "PRIVATE_DESIREE_LISTENING_TRANSPORT_INVALID_WITH_AUDIBLE_FATAL", 3
    elif gate["transport_invalid_sample_count"]:
        status, code = "PRIVATE_DESIREE_LISTENING_QA_TRANSPORT_INVALID", 3
    else:
        status, code = "PRIVATE_DESIREE_LISTENING_QA_BLOCKED", 3
    result = {
        **preflight,
        "status": status,
        "provider_calls_ran": provider_calls_ran,
        "actual_provider_billing": "NOT_REPORTED",
        "judged_samples": judged,
        "listening_gate": gate,
        "error": error or None,
        "lock_restored": lock_restored,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "release_blockers_preserved": [
            "FOUR_SAMPLE_SCREEN_IS_NOT_FULL_TITLE_RELEASE_EVIDENCE",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        ],
    }
    write_json(output_path, result)
    return code, result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    code, result = execute(
        args.evidence.resolve(), args.output.resolve(), args.paid_lock.resolve(), dry_run=args.dry_run
    )
    print(json.dumps({"status": result["status"], "output": str(args.output), "provider_calls_ran": result.get("provider_calls_ran", False)}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
