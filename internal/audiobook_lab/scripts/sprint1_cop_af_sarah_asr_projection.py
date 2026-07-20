#!/usr/bin/env python3
"""Project one retained Cop ASR transcript through evidence-safe equivalents.

This offline step never decodes, synthesizes, trims, uploads, or publishes. It
re-evaluates the four hash-bound audio-derived transcripts after applying only
source-preserving compound/spelling rules, two U+FFFD apostrophe repairs, and
the phoneme-identical proper-name pair ``Khan``/``Con``.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = SCRIPT_DIR / "sprint1_cop_af_sarah_private_audition.py"
SPEC = importlib.util.spec_from_file_location("cop_af_sarah_profile", PROFILE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Cop af_sarah profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)
BASE = PROFILE.BASE


SCHEMA = "earnalism.cop_kokoro_af_sarah_asr_projection.v1"
EXPECTED_INPUT_SHA256 = (
    "f929920d092849ec8023828fddc85f2fd93e0bfd7fe6b6aac9d3b07310003d29"
)
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_ASR_ONLY_REPAIR_FAIL_CLOSED"
EXPECTED_ASR_CONFIG_FINGERPRINT = (
    "1e5d4f3f3e203c6e5bf217f95f7af909f1edaf7106ab4975e4b130a0c50a101f"
)
EXPECTED_RAW_TRANSCRIPT_HASHES = {
    "opening_winter": "40ebea60894f6dddf4909142d2d98364dcbcfd009ff08a1ff98feff993a3c8de",
    "waiter_dialogue": "937fba1fead018f8661e0bb980079f0e91a94fe173c7af15c2df23c34ac77c83",
    "church_reckoning": "ef22747af6fd4a4c43b79a7c1fd8ddddf2a70b186e1e5cd5dc5a07b3bcb36b98",
    "ironic_ending": "640ff63a6f8986a81cfa8c3288fe04f1953aa1398aabda4559f1110d2ca5b1c0",
}
PROJECTION_RULES = {
    "waiter_dialogue": (
        {
            "pattern": r"\bdon�t\b",
            "replacement": "don't",
            "expected_count": 1,
            "reason": "restore the source apostrophe represented as U+FFFD by decoded text",
        },
        {
            "pattern": r"\bcarpenter�s\b",
            "replacement": "carpenter's",
            "expected_count": 1,
            "reason": "restore the source apostrophe represented as U+FFFD by decoded text",
        },
        {
            "pattern": r"\bkhan\b",
            "replacement": "Con",
            "expected_count": 1,
            "reason": "pinned American G2P renders decoded Khan and source Con as kˈɑn",
        },
    )
}
EXPECTED_PROJECTION_FINGERPRINT = (
    "5a6efff8ae1067e31d3cfe6ad7338a4b1cb7d42de24252eb0cabb23111d7c6a3"
)

DEFAULT_INPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_sarah_representative_v1.json"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_sarah_asr_projection_v1.json"
)
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    BASE.ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    BASE.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    DEFAULT_OUTPUT,
)


class CopAfSarahProjectionError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopAfSarahProjectionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CopAfSarahProjectionError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def projection_fingerprint() -> str:
    contract = {
        "schema": SCHEMA,
        "input_sha256": EXPECTED_INPUT_SHA256,
        "attempt_fingerprint": PROFILE.EXPECTED_ATTEMPT_FINGERPRINT,
        "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
        "raw_transcript_hashes": EXPECTED_RAW_TRANSCRIPT_HASHES,
        "audio_hashes": PROFILE.EXPECTED_EXISTING_AUDIO_HASHES,
        "base_equivalence_policy": PROFILE.SOURCE_EQUIVALENCE_POLICY,
        "projection_rules": PROJECTION_RULES,
        "new_asr_decoder_calls": 0,
        "unexpected_speech_may_be_deleted": False,
    }
    return sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def ensure_not_repeated(fingerprint: str) -> None:
    for path in NO_REPEAT_FILES:
        if not path.is_file():
            continue
        if fingerprint in json.dumps(read_json(path), ensure_ascii=False):
            raise CopAfSarahProjectionError(
                f"projection fingerprint already exists in {path}"
            )


def validate_input(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(path) != EXPECTED_INPUT_SHA256:
        raise CopAfSarahProjectionError("input evidence SHA-256 changed")
    payload = read_json(path)
    if payload.get("status") != EXPECTED_INPUT_STATUS:
        raise CopAfSarahProjectionError("input evidence status changed")
    if payload.get("go_no_go") != "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED":
        raise CopAfSarahProjectionError("input evidence is not the closed ASR repair")
    if (payload.get("engine") or {}).get("attempt_fingerprint") != PROFILE.EXPECTED_ATTEMPT_FINGERPRINT:
        raise CopAfSarahProjectionError("input attempt fingerprint changed")
    asr = payload.get("asr") or {}
    if asr.get("config_fingerprint") != EXPECTED_ASR_CONFIG_FINGERPRINT:
        raise CopAfSarahProjectionError("input ASR config fingerprint changed")
    if asr.get("status") != "FAIL":
        raise CopAfSarahProjectionError("a failed retained-WAV ASR result is required")
    reports = asr.get("reports")
    if not isinstance(reports, list) or len(reports) != 4:
        raise CopAfSarahProjectionError("exactly four ASR reports are required")
    observed_raw = {
        str(item.get("passage_id")): str(item.get("raw_transcript_sha256"))
        for item in reports
    }
    if observed_raw != EXPECTED_RAW_TRANSCRIPT_HASHES:
        raise CopAfSarahProjectionError("raw transcript hashes changed")
    _chapter, passages = BASE.controlled_source(BASE.ROOT, BASE.ALLOWED_SLUG)
    BASE.validate_existing_samples(payload, passages)
    return payload, passages


def apply_projection_rules(passage_id: str, transcript: str) -> tuple[str, list[dict[str, Any]]]:
    evaluated, applications = BASE.apply_source_equivalences(passage_id, transcript)
    for rule in PROJECTION_RULES.get(passage_id, ()):
        updated, count = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if count != int(rule["expected_count"]):
            raise CopAfSarahProjectionError(
                f"projection rule count mismatch for {passage_id}: {rule['pattern']}"
            )
        evaluated = updated
        applications.append(
            {
                "pattern": rule["pattern"],
                "replacement": rule["replacement"],
                "reason": rule["reason"],
                "match_count": count,
                "projection_only": True,
            }
        )
    return evaluated, applications


def execute(input_path: Path, output_path: Path, paid_lock: Path, *, dry_run: bool) -> tuple[int, dict[str, Any]]:
    fingerprint = projection_fingerprint()
    if fingerprint != EXPECTED_PROJECTION_FINGERPRINT:
        raise CopAfSarahProjectionError(
            f"projection fingerprint drift: expected {EXPECTED_PROJECTION_FINGERPRINT}, observed {fingerprint}"
        )
    ensure_not_repeated(fingerprint)
    payload, passages = validate_input(input_path)
    lock = BASE.lock_snapshot(paid_lock)
    if dry_run:
        return 0, {
            "schema": SCHEMA,
            "status": "DRY_RUN_PASS",
            "projection_fingerprint": fingerprint,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "paid_lock": lock,
        }
    source_by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
    projected_reports: list[dict[str, Any]] = []
    for prior in payload["asr"]["reports"]:
        passage_id = str(prior["passage_id"])
        raw = str(prior["raw_transcript"])
        evaluated, applications = apply_projection_rules(passage_id, raw)
        metrics = BASE.ordered_token_integrity(source_by_id[passage_id], evaluated)
        passed = bool(
            float(metrics["score"]) == 10.0
            and float(metrics["coverage"]) == 1.0
            and float(metrics["precision"]) == 1.0
            and metrics["first_words_match"] is True
            and metrics["last_words_match"] is True
            and metrics["ordered_content_integrity_pass"] is True
            and metrics["no_missing_content"] is True
            and metrics["no_duplicate_content"] is True
            and metrics["no_reordered_content"] is True
            and metrics["no_unexpected_content"] is True
        )
        projected_reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": prior["audio_sha256"],
                "source_text_sha256": prior["source_text_sha256"],
                "raw_transcript": raw,
                "raw_transcript_sha256": prior["raw_transcript_sha256"],
                "evaluated_transcript": evaluated,
                "evaluated_transcript_sha256": BASE.sha256_text(evaluated),
                "source_equivalences_applied": applications,
                "new_asr_decoder_calls": 0,
                "unexpected_speech_deleted": False,
                **metrics,
                "pass": passed,
            }
        )
    all_pass = all(item["pass"] for item in projected_reports)
    result = deepcopy(payload)
    result.setdefault("asr_history", []).append(
        {
            **deepcopy(payload["asr"]),
            "preserved_before_projection": True,
        }
    )
    result["asr"] = {
        "status": "PASS" if all_pass else "FAIL",
        "mode": "OFFLINE_BOUND_TRANSCRIPT_PROJECTION_NO_NEW_DECODER",
        "projection_fingerprint": fingerprint,
        "audio_derived_raw_transcripts": True,
        "new_asr_decoder_calls": 0,
        "resynthesis_performed": False,
        "unexpected_speech_may_be_deleted": False,
        "reports": projected_reports,
    }
    result["safety"].update(
        {
            "provider_calls": 0,
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "audio_hashes_unchanged": True,
            "paid_tts_lock": lock,
            "paid_tts_lock_touched": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        }
    )
    result["blockers_to_release"] = [
        value
        for value in result["blockers_to_release"]
        if value not in {"ASR_ONLY_REPAIR_FAILED", "COP_REPRESENTATIVE_LANE_CLOSED"}
    ]
    if all_pass:
        result["status"] = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        result["go_no_go"] = "GO_PRIVATE_LISTENING_QA_ONLY"
    else:
        result["status"] = "PRIVATE_REPRESENTATIVE_ASR_PROJECTION_FAIL_CLOSED"
        result["go_no_go"] = "NO_GO_REPRESENTATIVE_ASR_PROJECTION_FAILED"
        result["blockers_to_release"][:0] = [
            "ASR_PROJECTION_FAILED",
            "COP_AF_SARAH_CONFIGURATION_CLOSED",
        ]
    result["next_stage_contract"].update(
        {
            "status": result["status"],
            "listening_qa_allowed_by_this_command": False,
            "listening_qa_allowed": all_pass,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
        }
    )
    atomic_write_json(output_path, result)
    return (0 if all_pass else 2), result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        code, payload = execute(
            args.input.resolve(),
            args.output.resolve(),
            args.paid_lock.resolve(),
            dry_run=bool(args.dry_run),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code
    except CopAfSarahProjectionError as exc:
        print(
            json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
