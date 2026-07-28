#!/usr/bin/env python3
"""Judge one private Google English audition with bounded schema-3 listening QA."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import BINARY_LISTENING_FLAGS, judge_audio_sample_with_openai  # noqa: E402

POLICY_MIN_LISTENING_SCORE = 9.0
POLICY_MIN_CONFIDENCE = 0.9
POLICY_MIN_DIMENSION_SCORE = 8.9
POLICY_MIN_ANTI_ROBOTIC_SCORE = 9.2
POLICY_MIN_ANTI_CHOPPY_SCORE = 9.2
LISTENING_DIMENSION_KEYS = (
    "naturalness_score",
    "pronunciation_score",
    "emotional_expression_score",
    "punctuation_pause_score",
    "pacing_score",
    "continuity_score",
    "listener_enjoyment_score",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def validate_paid_lock(path: Path, slug: str) -> tuple[bytes, dict[str, Any]]:
    original = path.expanduser().resolve().read_bytes()
    try:
        payload = json.loads(original)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("paid lock must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("status") != "active":
        raise ValueError("paid lock must remain active")
    if payload.get("current_holder") != "none":
        raise ValueError("paid lock already has a holder")
    if payload.get("allowed_next_holders", []) != []:
        raise ValueError("paid lock allowed_next_holders must be empty")
    allowed = payload.get("allowed_slugs")
    if not isinstance(allowed, list) or slug not in allowed:
        raise ValueError(f"paid lock does not allow slug {slug}")
    return original, payload


@contextmanager
def paid_lock_guard(
    path: Path, *, slug: str, audition_fingerprint: str, estimated_usd: float
):
    resolved = path.expanduser().resolve()
    original, payload = validate_paid_lock(resolved, slug)
    acquired = {
        **payload,
        "current_holder": f"sprint1_google_english_listening_qa:{slug}",
        "allowed_next_holders": [],
        "approved_scope": (
            "Private four-passage OpenAI listening QA only; "
            f"audition fingerprint {audition_fingerprint}; no synthesis, upload, "
            "publication, or release mutation."
        ),
        "estimated_cost_usd": estimated_usd,
    }
    write_bytes(
        resolved,
        json.dumps(acquired, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n",
    )
    try:
        yield {
            "paid_lock_touched": True,
            "paid_lock_sha256_before": sha256_bytes(original),
        }
    finally:
        write_bytes(resolved, original)
        if resolved.read_bytes() != original:
            raise RuntimeError("paid lock was not restored byte-for-byte")


def runtime_errors(env: dict[str, str], sample_count: int) -> tuple[list[str], dict[str, float]]:
    errors: list[str] = []
    if env.get("EARNALISM_ENABLE_OPENAI_LISTENING_QA", "").lower() not in {"1", "true", "yes"}:
        errors.append("EARNALISM_ENABLE_OPENAI_LISTENING_QA=true is required")
    if not env.get("EARNALISM_OPENAI_LISTENING_QA_MODEL"):
        errors.append("EARNALISM_OPENAI_LISTENING_QA_MODEL is required")
    if not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    try:
        unit = float(env["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"])
        cap = float(env["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"])
        if not math.isfinite(unit) or unit <= 0 or not math.isfinite(cap) or cap <= 0:
            raise ValueError
    except (KeyError, ValueError):
        errors.append("valid listening-QA estimate and cap environment variables are required")
        unit = 0.0
        cap = 0.0
    estimate = round(sample_count * unit, 4)
    if estimate > cap:
        errors.append(f"estimated listening QA cost ${estimate:.4f} exceeds cap ${cap:.4f}")
    return errors, {"sample_count": sample_count, "estimated_usd_per_sample": unit, "estimated_usd": estimate, "cap_usd": cap}


def load_evidence(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("status") != "PENDING_LISTENING_REVIEW":
        raise ValueError("audition evidence must be pending listening review")
    samples = evidence.get("samples")
    required = evidence.get("required_passages")
    if not isinstance(samples, list) or len(samples) != 4:
        raise ValueError("audition evidence must contain exactly four samples")
    if [item.get("passage_id") for item in samples] != required:
        raise ValueError("audition sample passage order does not match required_passages")
    manifest_path = Path(str(evidence.get("audition_manifest_path") or ""))
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if not manifest_path.is_file() or sha256_file(manifest_path) != evidence.get("audition_manifest_sha256"):
        raise ValueError("audition manifest is missing or hash-mismatched")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("slug") != evidence.get("slug") or manifest.get("source_sha256") != evidence.get("source_sha256"):
        raise ValueError("audition manifest slug/source binding mismatch")
    seen: set[str] = set()
    for sample in samples:
        audio = Path(str(sample.get("audio_path") or ""))
        if not audio.is_absolute():
            audio = ROOT / audio
        expected = str(sample.get("audio_sha256") or "")
        if not audio.is_file() or audio.stat().st_size <= 0 or sha256_file(audio) != expected:
            raise ValueError(f"audition sample is missing or hash-mismatched: {sample.get('passage_id')}")
        if expected in seen:
            raise ValueError("audition evidence contains duplicate audio")
        seen.add(expected)
        sample["audio_path"] = str(audio)
    return evidence, manifest


def evaluate(
    evidence_path: Path,
    output_path: Path,
    *,
    paid_lock_path: Path | None = None,
    env: dict[str, str] | None = None,
    judge: Callable[[Any, Any, dict[str, Any]], dict[str, Any]] = judge_audio_sample_with_openai,
    client: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    process_env = dict(os.environ if env is None else env)
    evidence, manifest = load_evidence(evidence_path)
    errors, budget = runtime_errors(process_env, len(evidence["samples"]))
    if paid_lock_path is None and client is None:
        errors.append("paid lock is required for live listening QA")
    lock_validation: tuple[bytes, dict[str, Any]] | None = None
    if paid_lock_path is not None:
        try:
            lock_validation = validate_paid_lock(paid_lock_path, evidence["slug"])
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if errors:
        result = {
            **evidence,
            "status": "BLOCKED_BEFORE_LISTENING_QA",
            "budget": budget,
            "blockers": errors,
            "provider_calls_ran": False,
            "paid_lock_touched": False,
        }
        write_json(output_path, result)
        return 2, result
    if client is None:
        from openai import OpenAI

        client = OpenAI()
    args = SimpleNamespace(
        slug=evidence["slug"],
        title=evidence["title"],
        author=manifest.get("author") or "",
        language="English",
    )
    judged_samples = []
    lock_result = {
        "paid_lock_touched": False,
        "paid_lock_restored_byte_for_byte": True,
    }

    def judge_samples() -> None:
        for sample in evidence["samples"]:
            judged = judge(
                client,
                args,
                {
                    "sample_label": sample["passage_id"],
                    "start_time": 0.0,
                    "duration": 0.0,
                    "sample_audio_path": sample["audio_path"],
                    "sample_audio_hash": sample["audio_sha256"],
                },
            )
            scores = (
                judged.get("scores")
                if isinstance(judged.get("scores"), dict)
                else {}
            )
            flags = (
                judged.get("judge_flags")
                if isinstance(judged.get("judge_flags"), dict)
                else {}
            )
            judged_samples.append(
                {
                    **sample,
                    "overall_listening_score": float(
                        scores.get("overall_listening_score") or 0
                    ),
                    "confidence_score": float(
                        scores.get("confidence_score")
                        or judged.get("confidence")
                        or 0
                    ),
                    "fatal_flags": sorted(
                        name for name in BINARY_LISTENING_FLAGS if flags.get(name)
                    ),
                    "judge_flags": flags,
                    "scores": scores,
                    "review_notes": judged.get("notes") or "",
                    "blocker_reason": judged.get("blocker_reason") or "",
                }
            )

    if paid_lock_path is not None:
        assert lock_validation is not None
        with paid_lock_guard(
            paid_lock_path,
            slug=evidence["slug"],
            audition_fingerprint=str(evidence.get("audition_fingerprint") or ""),
            estimated_usd=budget["estimated_usd"],
        ) as acquired:
            lock_result.update(acquired)
            judge_samples()
        lock_result["paid_lock_restored_byte_for_byte"] = (
            paid_lock_path.expanduser().resolve().read_bytes() == lock_validation[0]
        )
    else:
        judge_samples()
    minimum_score = min(item["overall_listening_score"] for item in judged_samples)
    minimum_confidence = min(item["confidence_score"] for item in judged_samples)
    fatal = sorted({flag for item in judged_samples for flag in item["fatal_flags"]})
    score_gate = float(
        evidence.get("minimum_listening_score") or POLICY_MIN_LISTENING_SCORE
    )
    confidence_gate = float(
        evidence.get("minimum_listening_confidence") or POLICY_MIN_CONFIDENCE
    )
    dimension_failures: list[str] = []
    for sample in judged_samples:
        passage_id = sample["passage_id"]
        scores = sample.get("scores") or {}
        for key in LISTENING_DIMENSION_KEYS:
            try:
                score = float(scores.get(key))
            except (TypeError, ValueError):
                dimension_failures.append(f"{passage_id}: {key} missing")
                continue
            if score < POLICY_MIN_DIMENSION_SCORE:
                dimension_failures.append(
                    f"{passage_id}: {key} {score} below {POLICY_MIN_DIMENSION_SCORE}"
                )
        for key, minimum in (
            ("anti_robotic_texture_score", POLICY_MIN_ANTI_ROBOTIC_SCORE),
            ("anti_choppy_join_score", POLICY_MIN_ANTI_CHOPPY_SCORE),
        ):
            try:
                score = float(scores.get(key))
            except (TypeError, ValueError):
                dimension_failures.append(f"{passage_id}: {key} missing")
                continue
            if score < minimum:
                dimension_failures.append(
                    f"{passage_id}: {key} {score} below {minimum}"
                )
    passed = (
        minimum_score >= score_gate
        and minimum_confidence >= confidence_gate
        and not fatal
        and not dimension_failures
    )
    result = {
        **evidence,
        "status": "PASS" if passed else "BLOCKED_LISTENING_QA",
        "samples": judged_samples,
        "minimum_overall_listening_score": minimum_score,
        "minimum_confidence_score": minimum_confidence,
        "fatal_flags": fatal,
        "dimension_failures": dimension_failures,
        "per_dimension_score_min": POLICY_MIN_DIMENSION_SCORE,
        "anti_robotic_texture_score_min": POLICY_MIN_ANTI_ROBOTIC_SCORE,
        "anti_choppy_join_score_min": POLICY_MIN_ANTI_CHOPPY_SCORE,
        "budget": budget,
        "provider_calls_ran": True,
        "actual_provider_billing": "NOT_REPORTED",
        **lock_result,
        "blockers": (
            []
            if passed
            else [
                "Every audition sample must meet overall, confidence, "
                "per-dimension, anti-robotic, anti-choppy, and fatal-flag gates."
            ]
        ),
    }
    write_json(output_path, result)
    return (0 if passed else 3), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paid-lock", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    returncode, result = evaluate(
        args.evidence, args.output, paid_lock_path=args.paid_lock
    )
    print(json.dumps({"status": result["status"], "output": str(args.output), "blockers": result.get("blockers", [])}, ensure_ascii=False))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
