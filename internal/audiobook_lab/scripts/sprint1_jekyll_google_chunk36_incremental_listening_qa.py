#!/usr/bin/env python3
"""Judge only repaired Jekyll chunk_0036 and rebuild six-sample listening QA.

Five unchanged judgments are reused only after exact source/audio hash binding
to the retained independent report.  The changed chunk is always judged again
under ``paid_tts.lock``.  The rebuilt report uses the active English
``platform_audiobook_acceptance_v4_89`` policy and remains private.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
import sys

sys.path[:0] = [str(SCRIPT_DIR), str(HOOK_DIR)]

import sprint1_google_english_full_audio_derived_qa as audio_derived_qa  # noqa: E402
import sprint1_google_english_full_candidate_qa as candidate_qa  # noqa: E402
import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402
import sprint1_jekyll_google_chunk36_bounded_repair as repair  # noqa: E402
from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    UNIVERSAL_LISTENING_POLICY,
)


SCHEMA = "earnalism.jekyll_google_chunk36_incremental_listening_qa.v1"
ACTIVE_POLICY = UNIVERSAL_LISTENING_POLICY
if ACTIVE_POLICY != "platform_audiobook_acceptance_v4_89":
    raise RuntimeError("the active English listening policy changed unexpectedly")
APPROVAL_ENV = "EARNALISM_APPROVE_JEKYLL_CHUNK36_LISTENING_QA"
EXPECTED_PRIOR_LISTENING_SHA256 = repair.EXPECTED_FAILED_LISTENING_SHA256
EXPECTED_PRIOR_UNIT_IDS = (
    "chunk_0000",
    "chunk_0018",
    repair.TARGET_UNIT_ID,
    "chunk_0041",
    "chunk_0045",
    "chunk_0091",
)


class IncrementalListeningError(RuntimeError):
    """Fail-closed incremental listening evidence error."""

    def __init__(
        self,
        status: str,
        message: str,
        *,
        exit_code: int = 2,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "error": str(self), **self.details}


def require(condition: bool, status: str, message: str) -> None:
    if not condition:
        raise IncrementalListeningError(status, message)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IncrementalListeningError(
            "BLOCKED_INVALID_EVIDENCE",
            f"{label} is not readable UTF-8 JSON: {path}",
        ) from exc
    require(
        isinstance(value, dict),
        "BLOCKED_INVALID_EVIDENCE",
        f"{label} must contain one JSON object",
    )
    return value


def validate_output(output: Path, run_dir: Path) -> Path:
    resolved = output.expanduser().resolve()
    resolved_run_dir = run_dir.expanduser().resolve()
    require(
        candidate_qa.is_within(resolved, resolved_run_dir),
        "BLOCKED_OUTPUT_PATH",
        "incremental listening output must remain inside the repaired full run",
    )
    require(
        not resolved.exists(),
        "BLOCKED_REPEAT_LISTENING_QA",
        "incremental listening output is immutable; this candidate already has a result",
    )
    try:
        google_pipeline.validate_private_output_dir(resolved.parent)
    except google_pipeline.PipelineError as exc:
        raise IncrementalListeningError(exc.status, str(exc)) from exc
    return resolved


def validate_objective_report(
    path: Path,
    evidence: candidate_qa.CandidateEvidence,
) -> dict[str, Any]:
    objective_path = path.expanduser().resolve()
    require(
        candidate_qa.is_within(
            objective_path,
            evidence.manifest_path.parent.resolve(),
        ),
        "BLOCKED_OBJECTIVE_QA_BINDING",
        "audio-derived QA must remain inside the repaired full run",
    )
    payload = read_json(objective_path, "audio-derived QA")
    for field, expected in {
        "schema_version": audio_derived_qa.SCHEMA,
        "status": "FULL_AUDIO_DERIVED_ASR_SYNC_PASS_PRIVATE_ONLY",
        "slug": repair.SLUG,
        "full_manifest_sha256": evidence.manifest_sha256,
        "source_sha256": evidence.source_sha256,
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "candidate_audio_sequence_sha256": (
            evidence.candidate_audio_sequence_sha256
        ),
        "candidate_binding_sha256": evidence.candidate_binding_sha256,
        "objective_pass": True,
        "next_stage": "FULL_TITLE_LISTENING_QA_PRIVATE_ONLY",
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
    }.items():
        require(
            payload.get(field) == expected,
            "BLOCKED_OBJECTIVE_QA_BINDING",
            f"audio-derived QA changed at {field}",
        )
    require(
        not payload.get("blockers"),
        "BLOCKED_OBJECTIVE_QA_BINDING",
        "audio-derived QA still contains blockers",
    )
    return payload


def prior_samples(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    prior_path = path.expanduser().resolve()
    require(
        repair.sha256_file(prior_path) == EXPECTED_PRIOR_LISTENING_SHA256,
        "BLOCKED_PRIOR_LISTENING_HASH",
        "prior listening report does not match the independent retained report",
    )
    prior = read_json(prior_path, "prior listening report")
    require(
        prior.get("status") == "BLOCKED_LISTENING_QA"
        and prior.get("slug") == repair.SLUG
        and prior.get("full_manifest_sha256")
        == repair.EXPECTED_FULL_MANIFEST_SHA256
        and prior.get("candidate_binding_sha256")
        == repair.EXPECTED_BASE_CANDIDATE_BINDING_SHA256,
        "BLOCKED_PRIOR_LISTENING_BINDING",
        "prior listening report is not the exact rejected Jekyll candidate",
    )
    samples = (
        ((prior.get("listening_quality_report") or {}).get("listening_quality") or {})
        .get("samples")
    )
    require(
        isinstance(samples, list) and len(samples) == 6,
        "BLOCKED_PRIOR_LISTENING_BINDING",
        "prior report must contain exactly six judgments",
    )
    by_unit = {
        str(sample.get("unit_id") or ""): sample
        for sample in samples
        if isinstance(sample, dict)
    }
    require(
        tuple(by_unit) == EXPECTED_PRIOR_UNIT_IDS,
        "BLOCKED_PRIOR_LISTENING_BINDING",
        "prior deterministic six-sample order changed",
    )
    return prior, by_unit


def bind_reused_samples(
    evidence: candidate_qa.CandidateEvidence,
    prior_path: Path,
    prior: Mapping[str, Any],
    prior_by_unit: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = candidate_qa.select_listening_samples(evidence)
    require(
        tuple(sample["unit_id"] for sample in selected)
        == EXPECTED_PRIOR_UNIT_IDS,
        "BLOCKED_SAMPLE_SELECTION_DRIFT",
        "repaired candidate no longer selects the exact six review units",
    )
    repaired: dict[str, Any] | None = None
    bound: list[dict[str, Any]] = []
    for sample in selected:
        unit_id = sample["unit_id"]
        old = prior_by_unit[unit_id]
        require(
            old.get("source_text_sha256") == sample["source_text_sha256"],
            "BLOCKED_REUSED_JUDGMENT_BINDING",
            f"{unit_id} source hash changed",
        )
        if unit_id == repair.TARGET_UNIT_ID:
            require(
                old.get("sample_audio_hash")
                == repair.TARGET_PRIOR_AUDIO_SHA256
                and sample["sample_audio_hash"]
                != old.get("sample_audio_hash"),
                "BLOCKED_REPAIR_AUDIO_NOT_CHANGED",
                "chunk_0036 replacement does not differ from rejected audio",
            )
            repaired = dict(sample)
            continue
        require(
            old.get("sample_audio_hash") == sample["sample_audio_hash"],
            "BLOCKED_REUSED_JUDGMENT_BINDING",
            f"{unit_id} audio hash changed; prior judgment cannot be reused",
        )
        scores = old.get("scores")
        flags = old.get("judge_flags")
        require(
            isinstance(scores, dict)
            and all(field in scores for field in candidate_qa.LISTENING_THRESHOLDS)
            and isinstance(flags, dict)
            and all(field in flags for field in BINARY_LISTENING_FLAGS)
            and old.get("frontmatter_present") is False,
            "BLOCKED_REUSED_JUDGMENT_SCHEMA",
            f"{unit_id} prior judgment lacks passing schema-3 fields",
        )
        bound.append(
            {
                **sample,
                "scores": dict(scores),
                "confidence": float(scores["confidence_score"]),
                "judge_flags": dict(flags),
                "frontmatter_present": old.get("frontmatter_present"),
                "notes": str(old.get("notes") or ""),
                "blocker_reason": str(old.get("blocker_reason") or ""),
                "judgment_reused": True,
                "judgment_reuse_reason": "SOURCE_AND_AUDIO_HASH_UNCHANGED",
                "prior_listening_report_path": str(prior_path.resolve()),
                "prior_listening_report_sha256": EXPECTED_PRIOR_LISTENING_SHA256,
                "prior_candidate_binding_sha256": prior.get(
                    "candidate_binding_sha256"
                ),
            }
        )
    require(
        repaired is not None and len(bound) == 5,
        "BLOCKED_SAMPLE_SELECTION_DRIFT",
        "incremental QA requires five reusable judgments and one repaired chunk",
    )
    return bound, repaired


def runtime_errors(env: Mapping[str, str]) -> list[str]:
    errors = candidate_qa.listening_runtime_errors(dict(env))
    if env.get("EARNALISM_LISTENING_POLICY_VERSION") != ACTIVE_POLICY:
        errors.append(
            f"EARNALISM_LISTENING_POLICY_VERSION={ACTIVE_POLICY} is required"
        )
    if env.get(APPROVAL_ENV, "").strip().lower() != "true":
        errors.append(f"{APPROVAL_ENV}=true is required")
    return list(dict.fromkeys(errors))


def acquired_lock(
    original: Mapping[str, Any],
    *,
    evidence: candidate_qa.CandidateEvidence,
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    repair_block = evidence.manifest["bounded_chunk_repair"]
    payload = dict(original)
    payload.update(
        {
            "current_holder": (
                "sprint1_jekyll_google_chunk36_incremental_listening_qa:"
                f"{repair.SLUG}:{repair.TARGET_UNIT_ID}"
            ),
            "allowed_next_holders": [],
            "holder_started_at": repair.iso_now(),
            "allowed_slugs": [repair.SLUG],
            "budget_cap_usd": budget.get("listening_qa_cap_usd"),
            "estimated_cost_usd": budget.get("estimated_qa_cost_usd"),
            "approved_scope": (
                "One OpenAI listening judgment for the repaired private "
                f"chunk_0036 only; candidate binding {evidence.candidate_binding_sha256}; "
                f"repair fingerprint {repair_block['repair_attempt_fingerprint']}; "
                "five unchanged judgments may be hash-reused; no synthesis, upload, "
                "publication, or release mutation."
            ),
            "stop_conditions": [
                "Objective audio-derived QA is not an exact pass",
                "Any prior reusable source or audio hash changed",
                "The repaired chunk was not replaced",
                "Any runtime approval, policy, budget, or lock gate fails",
                "Any upload, publication, or release mutation is attempted",
            ],
            "updated_at": repair.iso_now(),
        }
    )
    return payload


def evaluate(
    manifest_path: Path,
    objective_path: Path,
    prior_path: Path,
    paid_lock: Path,
    output_path: Path,
    *,
    env: Mapping[str, str] | None = None,
    judge: Callable[[Any, Any, dict[str, Any]], dict[str, Any]] = (
        candidate_qa.judge_audio_sample_with_openai
    ),
    client: Any | None = None,
    duration_probe: Callable[[Path], float] = candidate_qa.ffprobe_duration,
) -> tuple[int, dict[str, Any]]:
    try:
        evidence = audio_derived_qa.validate_contract(
            manifest_path,
            duration_getter=duration_probe,
        )
        manifest = evidence.manifest
        repair_block = manifest.get("bounded_chunk_repair")
        require(
            isinstance(repair_block, dict)
            and repair_block.get("slug") == repair.SLUG
            and repair_block.get("chunk_index") == repair.TARGET_INDEX
            and repair_block.get("unit_id") == repair.TARGET_UNIT_ID
            and repair_block.get("failed_listening_evidence_sha256")
            == EXPECTED_PRIOR_LISTENING_SHA256,
            "BLOCKED_REPAIR_BINDING",
            "replacement manifest is not the exact bounded Jekyll repair",
        )
        output = validate_output(output_path, evidence.manifest_path.parent)
        objective = validate_objective_report(objective_path, evidence)
        prior, prior_by_unit = prior_samples(prior_path)
        reused, target_sample = bind_reused_samples(
            evidence,
            prior_path,
            prior,
            prior_by_unit,
        )
    except (
        audio_derived_qa.FullAudioDerivedQAError,
        candidate_qa.CandidateQAError,
    ) as exc:
        result = {
            "schema_version": SCHEMA,
            "status": "BLOCKED_BEFORE_INCREMENTAL_LISTENING_QA",
            "provider_calls_ran": False,
            "provider_call_count": 0,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": [f"{getattr(exc, 'code', 'OBJECTIVE_QA_FAILED')}: {exc}"],
        }
        return 2, result
    except IncrementalListeningError as exc:
        return 2, {
            "schema_version": SCHEMA,
            "status": exc.status,
            "provider_calls_ran": False,
            "provider_call_count": 0,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": [str(exc)],
        }

    process_env = dict(os.environ if env is None else env)
    errors = runtime_errors(process_env)
    if errors:
        result = {
            "schema_version": SCHEMA,
            "status": "BLOCKED_RUNTIME_GATES",
            "candidate_binding_sha256": evidence.candidate_binding_sha256,
            "provider_calls_ran": False,
            "provider_call_count": 0,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": errors,
        }
        candidate_qa.atomic_write_json(output, result)
        return 2, result
    budget = candidate_qa.listening_budget_guard(process_env, 1)
    if not budget.get("ok"):
        result = {
            "schema_version": SCHEMA,
            "status": "BLOCKED_BUDGET",
            "candidate_binding_sha256": evidence.candidate_binding_sha256,
            "listening_qa_budget_guard": budget,
            "provider_calls_ran": False,
            "provider_call_count": 0,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": [str(budget.get("blocker") or "budget blocked")],
        }
        candidate_qa.atomic_write_json(output, result)
        return 2, result

    if client is None:
        try:
            from openai import OpenAI

            client = OpenAI()
        except Exception as exc:  # noqa: BLE001
            result = {
                "schema_version": SCHEMA,
                "status": "BLOCKED_OPENAI_CLIENT",
                "candidate_binding_sha256": evidence.candidate_binding_sha256,
                "provider_calls_ran": False,
                "provider_call_count": 0,
                "private_output_only": True,
                "public_release_approved": False,
                "upload_performed": False,
                "publication_performed": False,
                "release_mutation_performed": False,
                "blockers": [f"LISTENING_QA_NOT_RUN: {exc}"],
            }
            candidate_qa.atomic_write_json(output, result)
            return 2, result

    lock_path = paid_lock.expanduser().resolve()
    lock_before = lock_path.read_bytes()
    try:
        parsed_lock = google_pipeline.validate_paid_lock(lock_before)
    except google_pipeline.PipelineError as exc:
        result = {
            "schema_version": SCHEMA,
            "status": exc.status,
            "candidate_binding_sha256": evidence.candidate_binding_sha256,
            "provider_calls_ran": False,
            "provider_call_count": 0,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": [str(exc)],
        }
        candidate_qa.atomic_write_json(output, result)
        return 2, result

    provider_call_count = 0
    judgment_error: Exception | None = None
    judged: dict[str, Any] = {}
    try:
        repair.atomic_write_json(
            lock_path,
            acquired_lock(parsed_lock, evidence=evidence, budget=budget),
        )
        args = SimpleNamespace(
            slug=repair.SLUG,
            title=repair.TITLE,
            author=repair.AUTHOR,
            language="English",
        )
        provider_call_count = 1
        raw = judge(client, args, dict(target_sample))
        if not isinstance(raw, dict):
            raise TypeError("listening judge returned a non-object result")
        judged, judgment_blockers = candidate_qa.normalize_judgment(
            target_sample,
            raw,
        )
        if judgment_blockers:
            judged["normalization_blockers"] = judgment_blockers
    except Exception as exc:  # noqa: BLE001
        judgment_error = exc
    finally:
        try:
            repair.atomic_write_bytes(lock_path, lock_before)
        except Exception as restore_exc:  # noqa: BLE001
            judgment_error = IncrementalListeningError(
                "PAID_LOCK_RESTORE_FAILED",
                f"paid lock restoration failed: {restore_exc}",
                exit_code=7,
            )
    lock_after = lock_path.read_bytes()
    lock_restored = lock_after == lock_before
    if not lock_restored:
        judgment_error = IncrementalListeningError(
            "PAID_LOCK_RESTORE_FAILED",
            "paid lock was not restored byte-for-byte",
            exit_code=7,
        )

    if judgment_error is not None:
        result = {
            "schema_version": SCHEMA,
            "status": "BLOCKED_INCREMENTAL_LISTENING_QA",
            "candidate_binding_sha256": evidence.candidate_binding_sha256,
            "provider_calls_ran": provider_call_count > 0,
            "provider_call_count": provider_call_count,
            "paid_lock_touched": True,
            "paid_lock_restored_byte_for_byte": lock_restored,
            "paid_lock_sha256_before": repair.sha256_bytes(lock_before),
            "paid_lock_sha256_after": repair.sha256_bytes(lock_after),
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "blockers": [f"LISTENING_QA_NOT_RUN: {judgment_error}"],
        }
        candidate_qa.atomic_write_json(output, result)
        return (7 if not lock_restored else 3), result

    judged.update(
        {
            "judgment_reused": False,
            "new_judgment_reason": "REPLACEMENT_AUDIO_HASH_CHANGED",
            "active_release_policy": ACTIVE_POLICY,
        }
    )
    all_samples = sorted(
        [*reused, judged],
        key=lambda sample: int(sample["section_index"]),
    )
    normalization_blockers = list(judged.get("normalization_blockers") or [])
    listening_report, blockers = candidate_qa.build_listening_report(
        evidence,
        all_samples,
        policy_name=ACTIVE_POLICY,
        model=process_env["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
        blockers=normalization_blockers,
    )
    passed = not blockers
    result = {
        **candidate_qa.base_result(evidence),
        "schema_version": SCHEMA,
        "status": (
            "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY"
            if passed
            else "BLOCKED_LISTENING_QA"
        ),
        "active_release_policy": ACTIVE_POLICY,
        "audio_derived_objective_qa_path": str(objective_path.resolve()),
        "audio_derived_objective_qa_sha256": repair.sha256_file(
            objective_path.resolve()
        ),
        "audio_derived_objective_qa_binding_sha256": objective.get(
            "qa_binding_sha256"
        ),
        "objective_qa": {
            "status": "PASS",
            "evidence_kind": "FULL_AUDIO_DERIVED_ASR_SYNC",
            "audio_derived_qa_path": str(objective_path.resolve()),
            "audio_derived_qa_sha256": repair.sha256_file(
                objective_path.resolve()
            ),
            "audio_derived_qa_binding_sha256": objective.get(
                "qa_binding_sha256"
            ),
            "audio_derived_asr": objective.get("audio_derived_asr"),
            "measured_sync": objective.get("measured_sync"),
        },
        "prior_listening_report_path": str(prior_path.resolve()),
        "prior_listening_report_sha256": EXPECTED_PRIOR_LISTENING_SHA256,
        "reused_judgment_count": 5,
        "new_judgment_count": 1,
        "reused_judgment_unit_ids": [
            sample["unit_id"] for sample in all_samples if sample["judgment_reused"]
        ],
        "new_judgment_unit_ids": [
            sample["unit_id"]
            for sample in all_samples
            if not sample["judgment_reused"]
        ],
        "all_sample_judgments_hash_bound": True,
        "listening_qa_budget_guard": budget,
        "listening_quality_report": listening_report,
        "provider_calls_ran": True,
        "provider_call_count": 1,
        "paid_lock_read_or_written": True,
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": True,
        "paid_lock_sha256_before": repair.sha256_bytes(lock_before),
        "paid_lock_sha256_after": repair.sha256_bytes(lock_after),
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "blockers": blockers,
    }
    candidate_qa.atomic_write_json(output, result)
    return (0 if passed else 3), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replacement-full-manifest", required=True, type=Path)
    parser.add_argument("--audio-derived-qa", required=True, type=Path)
    parser.add_argument("--prior-listening-evidence", required=True, type=Path)
    parser.add_argument("--paid-lock", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, result = evaluate(
            args.replacement_full_manifest,
            args.audio_derived_qa,
            args.prior_listening_evidence,
            args.paid_lock,
            args.output,
        )
    except IncrementalListeningError as exc:
        print(json.dumps(exc.as_dict(), indent=2, sort_keys=True))
        return exc.exit_code
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output.expanduser().resolve()),
                "provider_calls_ran": result.get("provider_calls_ran", False),
                "provider_call_count": result.get("provider_call_count", 0),
                "blockers": result.get("blockers", []),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
