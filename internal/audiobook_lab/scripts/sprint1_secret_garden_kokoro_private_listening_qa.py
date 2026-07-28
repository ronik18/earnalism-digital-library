#!/usr/bin/env python3
"""Judge the exact Secret Garden Kokoro representative candidate.

The four hash-bound private WAVs may authorize one private full-title stage
only when the active Sprint 1 v3.89 listening policy passes. The adapter cannot
generate, upload, publish, or mutate audiobook release truth.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name(
    "sprint1_cop_kokoro_private_listening_qa.py"
)
CORE_SPEC = importlib.util.spec_from_file_location(
    "representative_listening_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load listening QA core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name(
    "sprint1_secret_garden_kokoro_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "secret_garden_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Secret Garden profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)

import asr_sync_hook as POLICY


SLUG = "the-secret-garden"
TITLE = "The Secret Garden"
AUTHOR = "Frances Hodgson Burnett"
LANGUAGE = "eng"
SCOPE = "secret_garden_kokoro_representative_listening_qa_v1"
HOLDER = "sprint1_secret_garden_kokoro_private_listening_qa"
EXPECTED_SAMPLE_COUNT = 4
EXPECTED_SCHEMA = "earnalism.kokoro.secret_garden_bf_emma_asr_repair.v1"
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = (
    "41da29ba7dfdae707d4d9def4905bfee9b5d38797a00787c00fbc5a83ff59bcb"
)
EXPECTED_SOURCE_SHA256 = (
    "4aac34ad4bda3586f1a062b24b3ca271a96edef7e4938d13042d0595f692f3a3"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "f849e64889b7a614bce6eb2ad3c0b5630424cf5d338e6a1b9d216318842aceff"
)
EXPECTED_ASR_CONFIG_FINGERPRINT = (
    "d73039f782de602ae41da7eda483a58c256a8b1be177d3b5aac5e848d89e707f"
)
EXPECTED_MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
EXPECTED_VOICE_SHA256 = (
    "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "231e27768bd89c86df8931b85823ebe9cd475ff082b631b99e430dd1ea1604d2"
)
EXPECTED_SAMPLE_BINDINGS: dict[str, dict[str, Any]] = {
    "opening_india_character": {
        "source_text_sha256": (
            "76fb57182f59bc7b3a9848bcc5f60489f297e208444e3089103d971f36cde893"
        ),
        "audio_sha256": (
            "9ada8c89feb554fc7ac26ecc291c546281613c79200a5b33d7846da7e81dadcc"
        ),
        "size_bytes": 1_000_844,
        "duration_seconds": 20.85,
    },
    "garden_key_discovery": {
        "source_text_sha256": (
            "444b42c0536f8c3c7ed8f2a3127ad023a88a0ffd864288e5bb61bb15dea60d7e"
        ),
        "audio_sha256": (
            "854ae30230cd83177fb602f68224f2f27c2c382d951b60462dd3a4e0c1e8f980"
        ),
        "size_bytes": 1_473_644,
        "duration_seconds": 30.7,
    },
    "colin_midnight_dialogue": {
        "source_text_sha256": (
            "d47aeb874088b45ba4032bbf886a5964b3b5071066f2619acb4c2e86666c969f"
        ),
        "audio_sha256": (
            "abb26f117b0bf850befa57ba05661f0604a2117dfb51d5ad2a1a361ef315044d"
        ),
        "size_bytes": 1_486_844,
        "duration_seconds": 30.975,
    },
    "healing_finale": {
        "source_text_sha256": (
            "8410db6f6340acce12a6c1b35686c093141d4672bd7a9713f7c7f4b2af14f7c3"
        ),
        "audio_sha256": (
            "a99dff8963e80bb8e9d7437d71db90e9bd3569b6078f56f0fa573bc8059c8570"
        ),
        "size_bytes": 1_479_644,
        "duration_seconds": 30.825,
    },
}

PLATFORM_THRESHOLDS = dict(POLICY.SPRINT1_AUDIOBOOK_89_THRESHOLDS)
QUALITY_DIMENSIONS = tuple(
    field for field in POLICY.LISTENING_THRESHOLDS if field != "confidence_score"
)
EXPECTED_ENV = {
    "EARNALISM_APPROVE_SECRET_GARDEN_KOKORO_LISTENING_QA": "true",
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
    "the-secret-garden_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_listening_qa_v1.json"
)
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK

SecretGardenListeningQAError = CORE.CopKokoroListeningQAError


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise SecretGardenListeningQAError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def load_evidence(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if not path.is_file():
        raise SecretGardenListeningQAError(f"evidence is missing: {path}")
    _require(CORE.sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    _require(evidence.get("schema"), EXPECTED_SCHEMA, "evidence schema")
    _require(evidence.get("status"), EXPECTED_STATUS, "evidence status")

    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "passage_count": EXPECTED_SAMPLE_COUNT,
        "representative_only": True,
        "full_title_generated": False,
    }.items():
        _require(scope.get(key), expected, f"scope.{key}")

    source = (
        evidence.get("source") if isinstance(evidence.get("source"), dict) else {}
    )
    _require(source.get("source_sha256"), EXPECTED_SOURCE_SHA256, "source SHA-256")
    engine = (
        evidence.get("engine") if isinstance(evidence.get("engine"), dict) else {}
    )
    for key, expected in {
        "package": "kokoro",
        "model_revision": EXPECTED_MODEL_REVISION,
        "voice": "bf_emma",
        "voice_sha256": EXPECTED_VOICE_SHA256,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "g2p_fallback_enabled": False,
        "pipeline_lang_code": "b",
        "g2p_british": True,
    }.items():
        _require(engine.get(key), expected, f"engine.{key}")

    asr = evidence.get("asr") if isinstance(evidence.get("asr"), dict) else {}
    _require(asr.get("status"), "PASS", "ASR status")
    _require(asr.get("audio_derived"), True, "ASR audio-derived flag")
    _require(
        asr.get("repair_fingerprint"),
        EXPECTED_ASR_CONFIG_FINGERPRINT,
        "ASR repair fingerprint",
    )
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    report_by_id = {str(item.get("passage_id") or ""): item for item in reports}
    _require(set(report_by_id), set(EXPECTED_SAMPLE_BINDINGS), "ASR passage IDs")

    samples = (
        evidence.get("samples") if isinstance(evidence.get("samples"), list) else []
    )
    sample_by_id = {str(item.get("passage_id") or ""): item for item in samples}
    _require(set(sample_by_id), set(EXPECTED_SAMPLE_BINDINGS), "sample passage IDs")
    verified: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = sample_by_id[passage_id]
        report = report_by_id[passage_id]
        for key, value in expected.items():
            _require(sample.get(key), value, f"{passage_id} sample {key}")
        audio = PROFILE.BASE.assert_private_audio_path(
            Path(str(sample.get("audio_path") or ""))
        )
        if not audio.is_file():
            raise SecretGardenListeningQAError(
                f"private audio is missing: {passage_id}"
            )
        _require(
            CORE.sha256_file(audio),
            expected["audio_sha256"],
            f"{passage_id} measured audio SHA-256",
        )
        _require(
            audio.stat().st_size,
            expected["size_bytes"],
            f"{passage_id} measured audio size",
        )
        measured_duration = CORE.ffprobe_duration(audio) or 0.0
        if abs(measured_duration - float(expected["duration_seconds"])) > 0.005:
            raise SecretGardenListeningQAError(
                f"{passage_id} measured duration changed"
            )
        for key, value in {
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
            _require(report.get(key), value, f"{passage_id} ASR {key}")
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

    sample_fingerprint = CORE.canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
            "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
            "sample_bindings": EXPECTED_SAMPLE_BINDINGS,
            "judge_model": EXPECTED_ENV["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
            "rubric_version": POLICY.LISTENING_QA_RUBRIC_VERSION,
            "hook_version": POLICY.LISTENING_QA_HOOK_VERSION,
            "policy": POLICY.SPRINT1_AUDIOBOOK_89_POLICY,
            "platform_thresholds": PLATFORM_THRESHOLDS,
        }
    )
    return evidence, verified, sample_fingerprint


def load_lock(raw: bytes) -> dict[str, Any]:
    _require(
        hashlib.sha256(raw).hexdigest(),
        EXPECTED_PAID_LOCK_SHA256,
        "paid lock SHA-256",
    )
    payload = json.loads(raw)
    _require(payload.get("status"), "active", "paid lock status")
    _require(payload.get("current_holder"), "none", "paid lock holder")
    _require(payload.get("allowed_next_holders"), [], "paid lock next holders")
    _require(payload.get("allowed_slugs"), [SLUG], "paid lock slug scope")
    return payload


def prior_attempt_completed(output_path: Path, fingerprint: str) -> bool:
    """Close a fingerprint only after four transport-valid judgments exist."""

    if not output_path.is_file():
        return False
    try:
        prior = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if prior.get("sample_fingerprint") != fingerprint:
        return False
    judged = (
        prior.get("judged_samples")
        if isinstance(prior.get("judged_samples"), list)
        else []
    )
    return bool(
        len(judged) == EXPECTED_SAMPLE_COUNT
        and all(
            isinstance(sample.get("raw_judgment"), dict)
            and not str(sample.get("blocker_reason") or "").strip()
            for sample in judged
        )
    )


def evaluate_judgments(samples: list[dict[str, Any]]) -> dict[str, Any]:
    minimums = {
        field: round(
            min(
                (
                    POLICY.safe_float((sample.get("scores") or {}).get(field), 0.0)
                    for sample in samples
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
            for field in POLICY.BINARY_LISTENING_FLAGS
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
    return {
        "policy": POLICY.SPRINT1_AUDIOBOOK_89_POLICY,
        "platform_thresholds": PLATFORM_THRESHOLDS,
        "platform_screen_pass": platform_pass,
        "owner_exact_10_pass": all(
            minimums[field] == 10.0 for field in QUALITY_DIMENSIONS
        ),
        "next_private_stage_authorized": platform_pass,
        "minimum_scores": minimums,
        "threshold_failures": threshold_failures,
        "fatal_flags": fatal,
        "sample_blockers": sample_blockers,
    }


def judge_exact_audio_sample(
    client: Any, args: Any, sample: dict[str, Any]
) -> dict[str, Any]:
    audio_path = Path(sample["sample_audio_path"])
    properties = {
        field: {"type": "number"} for field in POLICY.LISTENING_THRESHOLDS
    }
    properties.update(
        {field: {"type": "boolean"} for field in POLICY.BINARY_LISTENING_FLAGS}
    )
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
            "description": (
                "Record strict schema-3 audiobook listening QA for one exact "
                "private sample."
            ),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    prompt = (
        "Independently judge this exact private English literary-audiobook "
        "sample. Return only the function call. Quality scores are 0-10 and "
        "confidence_score is 0-1. Apply Sprint 1 v3.89: overall, naturalness, "
        "pronunciation, emotional expression, punctuation/pause, pacing, "
        "continuity and listener enjoyment must each be at least 8.9; "
        "anti-robotic texture and anti-choppy joins must each be at least 9.2; "
        "confidence must be at least 0.90; any fatal flag fails. Penalize "
        "mispronunciation, unnatural pauses, weak emotion, mechanical cadence, "
        "robotic texture, choppy joins and listener fatigue. The work is "
        f"{args.title} by {args.author}."
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
                                "data": base64.b64encode(
                                    audio_path.read_bytes()
                                ).decode("ascii"),
                                "format": "wav",
                            },
                        },
                    ],
                }
            ],
            tools=[tool],
            tool_choice={
                "type": "function",
                "function": {"name": "record_listening_quality"},
            },
            temperature=0,
            max_completion_tokens=500,
        )
        message = response.choices[0].message
        arguments = (
            message.tool_calls[0].function.arguments if message.tool_calls else ""
        )
        judgment = json.loads(arguments or "{}")
    except Exception as exc:  # noqa: BLE001
        return {
            **sample,
            "scores": {},
            "judge_flags": {},
            "notes": f"OpenAI listening judge failed: {exc}",
            "blocker_reason": "LISTENING_QA_NOT_RUN",
        }
    if POLICY.safe_float(judgment.get("confidence_score"), 0.0) > 1.0:
        judgment["confidence_score"] = round(
            POLICY.safe_float(judgment.get("confidence_score")) / 10.0, 4
        )
    return {
        **sample,
        "scores": {
            field: POLICY.safe_float(judgment.get(field), 0.0)
            for field in POLICY.LISTENING_THRESHOLDS
        },
        "confidence": POLICY.safe_float(judgment.get("confidence_score"), 0.0),
        "notes": str(judgment.get("notes") or ""),
        "blocker_reason": str(judgment.get("blocker_reason") or ""),
        "judge_flags": {
            field: bool(judgment.get(field))
            for field in POLICY.BINARY_LISTENING_FLAGS
        },
        "frontmatter_present": bool(judgment.get("frontmatter_present")),
        "raw_judgment": judgment,
    }


def _configure_core() -> None:
    bindings = {
        "SLUG": SLUG,
        "TITLE": TITLE,
        "AUTHOR": AUTHOR,
        "LANGUAGE": LANGUAGE,
        "SCOPE": SCOPE,
        "HOLDER": HOLDER,
        "EXPECTED_SAMPLE_COUNT": EXPECTED_SAMPLE_COUNT,
        "EXPECTED_SCHEMA": EXPECTED_SCHEMA,
        "EXPECTED_STATUS": EXPECTED_STATUS,
        "EXPECTED_EVIDENCE_SHA256": EXPECTED_EVIDENCE_SHA256,
        "EXPECTED_SOURCE_SHA256": EXPECTED_SOURCE_SHA256,
        "EXPECTED_ATTEMPT_FINGERPRINT": EXPECTED_ATTEMPT_FINGERPRINT,
        "EXPECTED_ASR_CONFIG_FINGERPRINT": EXPECTED_ASR_CONFIG_FINGERPRINT,
        "EXPECTED_MODEL_REVISION": EXPECTED_MODEL_REVISION,
        "EXPECTED_VOICE_SHA256": EXPECTED_VOICE_SHA256,
        "EXPECTED_SAMPLE_BINDINGS": EXPECTED_SAMPLE_BINDINGS,
        "PLATFORM_THRESHOLDS": PLATFORM_THRESHOLDS,
        "QUALITY_DIMENSIONS": QUALITY_DIMENSIONS,
        "EXPECTED_ENV": EXPECTED_ENV,
        "DEFAULT_EVIDENCE": DEFAULT_EVIDENCE,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "load_evidence": load_evidence,
        "load_lock": load_lock,
        "prior_attempt_completed": prior_attempt_completed,
        "evaluate_judgments": evaluate_judgments,
        "assert_private_audio": PROFILE.BASE.assert_private_audio_path,
    }
    for name, value in bindings.items():
        setattr(CORE, name, value)


def execute(
    evidence_path: Path,
    output_path: Path,
    lock_path: Path,
    *,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    client_factory: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    _configure_core()
    code, result = CORE.execute(
        evidence_path,
        output_path,
        lock_path,
        dry_run=dry_run,
        env=env,
        judge=judge_exact_audio_sample,
        client_factory=client_factory,
    )
    result["scope"] = (
        "PRIVATE_SECRET_GARDEN_REPRESENTATIVE_SCREEN_ONLY_NOT_RELEASE_EVIDENCE"
    )
    result["policy"] = POLICY.SPRINT1_AUDIOBOOK_89_POLICY
    if not dry_run:
        gate = result.get("listening_gate") or {}
        if gate.get("platform_screen_pass") is True and not result.get("error"):
            result["status"] = (
                "PRIVATE_SECRET_GARDEN_REPRESENTATIVE_V3_89_PASS_"
                "NOT_RELEASE_EVIDENCE"
            )
            code = 0
        elif result.get("error"):
            result["status"] = "PRIVATE_SECRET_GARDEN_LISTENING_QA_ERROR"
        else:
            result["status"] = "PRIVATE_SECRET_GARDEN_LISTENING_QA_BLOCKED"
        result["release_blockers_preserved"] = [
            "FOUR_SAMPLE_SCREEN_IS_NOT_SIX_SAMPLE_FULL_TITLE_RELEASE_EVIDENCE",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_DELIVERY_MANIFEST_NOT_COMPLETE",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        ]
    CORE.write_json(output_path, result)
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


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
