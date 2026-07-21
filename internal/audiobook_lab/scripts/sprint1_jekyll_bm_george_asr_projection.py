#!/usr/bin/env python3
"""Project retained Jekyll bm_george transcripts through exact evidence.

This offline step never decodes, synthesizes, edits, trims, listens, uploads,
or publishes.  It re-evaluates the four hash-bound selected transcripts using
only source-preserving compound, spelling, homophone, and interjection forms.
Unexpected speech and substantive words are never removed or rewritten.
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
PROFILE_PATH = SCRIPT_DIR / "sprint1_jekyll_kokoro_private_bakeoff.py"
SPEC = importlib.util.spec_from_file_location("jekyll_projection_profile", PROFILE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Jekyll profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)
PROFILE.configure_base("bm_george")
BASE = PROFILE.BASE
ROOT = BASE.ROOT

SCHEMA = "earnalism.kokoro.jekyll_bm_george_asr_projection.v1"
EXPECTED_INPUT_SHA256 = (
    "0d68a5fbd5576cfbbdb915cc22d8491bd072aeea32f84d38f435d72f6563ea03"
)
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED"
EXPECTED_REPAIR_FINGERPRINT = (
    "f769f885ffadc9f3553b76d90ecb32550b58a81fb85bab91c3e5da33fda78109"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "e10223569eb619615f05c83cc824eca7a247ede7788eba5d78e0fb17fea3ec2f"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES = {
    "opening_character": "2d96d28402af3ac4efaee1c69cdce5cecac6005ccc6f6aca9dbd09009cbf0c19",
    "carew_murder": "d5b97390881de5543b1b16b2837a614f4a74d6af88a4cc80a0c4ec546af0d3b0",
    "lanyon_transformation": "12992631e8db85c1b42786997e2ce5fda21c4d64be0f9316e15107d17c737748",
    "final_confession": "3720c094c94489a9d373f6af6fba3af314bb7a1247ddde5d5ce9a90f945b7c73",
}
EXPECTED_AUDIO_BINDINGS = {
    passage_id: {
        "source_text_sha256": values["source_text_sha256"],
        "audio_sha256": values["audio_sha256"],
        "size_bytes": values["size_bytes"],
        "duration_seconds": values["duration_seconds"],
    }
    for passage_id, values in {
        "opening_character": {
            "source_text_sha256": "b491afef3119554f32c9250f5a81446b55bd81a63bf2fecf3b4940da8e4f1994",
            "audio_sha256": "0c39a3fa2fe66131f9c57cfbac3e5b270f5b43d75aa215158d9d298a508381a6",
            "size_bytes": 2_715_644,
            "duration_seconds": 56.575,
        },
        "carew_murder": {
            "source_text_sha256": "b45aebd6abcc2e730d156ad71d2964eeff8a1f472cc7146ade53575ec386bd8f",
            "audio_sha256": "dad290dcd691f60904a855373a1487ab3cd6ce393cb8bbf5776f931938b8145e",
            "size_bytes": 2_510_444,
            "duration_seconds": 52.3,
        },
        "lanyon_transformation": {
            "source_text_sha256": "3bd9b43260be8299d10f73995dd4c5706e39eba3e0844bf88c619bc7373d47ff",
            "audio_sha256": "3fe90dbfdceab82ab91bd28e58406cf145d107c141e2747aee98caa27966f0bb",
            "size_bytes": 1_993_244,
            "duration_seconds": 41.525,
        },
        "final_confession": {
            "source_text_sha256": "fee77d935c85880bed743ddd65949450c5bb5f5528e8a40101d34cf3e2d11e93",
            "audio_sha256": "e4fbad3f91538722187afd82dede7e4e4691977f652e091933fb1a53d11d3112",
            "size_bytes": 4_344_044,
            "duration_seconds": 90.5,
        },
    }.items()
}
PROJECTION_RULES = {
    "opening_character": (
        {
            "pattern": r"\bbeakened\b",
            "replacement": "beaconed",
            "expected_count": 1,
            "reason": "non-word ASR spelling for source-generated beaconed phonemes",
        },
    ),
    "carew_murder": (
        {
            "pattern": r"\bunderfoot\b",
            "replacement": "under foot",
            "expected_count": 1,
            "reason": "ASR compound for the exact source words under foot",
        },
        {
            "pattern": r"\brecognize\b",
            "replacement": "recognise",
            "expected_count": 1,
            "reason": "American ASR spelling for source British spelling recognise",
        },
    ),
    "lanyon_transformation": (
        {
            "pattern": r"\boh\b",
            "replacement": "O",
            "expected_count": 1,
            "reason": "ASR interjection spelling for one source O exclamation",
        },
    ),
    "final_confession": (
        {
            "pattern": r"\bfear[- ]struck\b",
            "replacement": "fearstruck",
            "expected_count": 1,
            "reason": "ASR tokenization of the source compound fearstruck",
        },
    ),
}
FORBIDDEN_PROJECTIONS = (
    "wondering/wandering",
    "unexpected speech deletion",
    "missing content insertion",
    "substantive word substitution",
)
EXPECTED_PROJECTION_FINGERPRINT = (
    "d8f01045423aaa6d4b0a0773db62759325f5360c8b822753ff0fa3e46d4f224a"
)

DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_kokoro_bm_george_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_kokoro_bm_george_asr_projection_v1.json"
)
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_release_gate_evidence.json",
    DEFAULT_OUTPUT,
)


class JekyllProjectionError(RuntimeError):
    """Raised when retained projection evidence no longer matches its contract."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise JekyllProjectionError(f"expected JSON object: {path}")
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
        "repair_fingerprint": EXPECTED_REPAIR_FINGERPRINT,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "selected_raw_transcript_hashes": EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES,
        "audio_bindings": EXPECTED_AUDIO_BINDINGS,
        "projection_rules": PROJECTION_RULES,
        "forbidden_projections": FORBIDDEN_PROJECTIONS,
        "new_asr_decoder_calls": 0,
        "resynthesis_performed": False,
        "unexpected_speech_may_be_deleted": False,
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(fingerprint: str) -> None:
    for path in NO_REPEAT_FILES:
        if not path.is_file():
            continue
        if fingerprint in path.read_text(encoding="utf-8", errors="strict"):
            raise JekyllProjectionError(
                f"projection fingerprint already exists in {path}"
            )


def validate_input(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if BASE.sha256_file(path) != EXPECTED_INPUT_SHA256:
        raise JekyllProjectionError("input evidence SHA-256 changed")
    payload = read_json(path)
    if payload.get("status") != EXPECTED_INPUT_STATUS:
        raise JekyllProjectionError("input status changed")
    if payload.get("go_no_go") != "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED":
        raise JekyllProjectionError("input is not a closed Jekyll repair")
    if (payload.get("asr_repair") or {}).get("repair_fingerprint") != EXPECTED_REPAIR_FINGERPRINT:
        raise JekyllProjectionError("repair fingerprint changed")
    if (payload.get("engine") or {}).get("attempt_fingerprint") != EXPECTED_ATTEMPT_FINGERPRINT:
        raise JekyllProjectionError("attempt fingerprint changed")
    reports = (payload.get("asr") or {}).get("reports")
    if not isinstance(reports, list) or len(reports) != 4:
        raise JekyllProjectionError("exactly four selected reports are required")
    observed_raw = {
        str(item.get("passage_id")): str(item.get("raw_transcript_sha256"))
        for item in reports
    }
    if observed_raw != EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES:
        raise JekyllProjectionError("selected raw transcript hashes changed")

    samples = payload.get("samples")
    if not isinstance(samples, list) or len(samples) != 4:
        raise JekyllProjectionError("exactly four private samples are required")
    sample_by_id: dict[str, dict[str, Any]] = {}
    for sample in samples:
        passage_id = str(sample.get("passage_id") or "")
        binding = EXPECTED_AUDIO_BINDINGS.get(passage_id)
        if binding is None:
            raise JekyllProjectionError(f"unexpected sample: {passage_id}")
        for key, expected in binding.items():
            if sample.get(key) != expected:
                raise JekyllProjectionError(f"{passage_id} {key} changed")
        audio = BASE.assert_private_audio_path(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise JekyllProjectionError(f"private WAV missing: {audio}")
        if BASE.sha256_file(audio) != binding["audio_sha256"]:
            raise JekyllProjectionError(f"private WAV hash changed: {passage_id}")
        if audio.stat().st_size != binding["size_bytes"]:
            raise JekyllProjectionError(f"private WAV size changed: {passage_id}")
        sample_by_id[passage_id] = dict(sample)
    _chapters, passages = PROFILE.controlled_source(ROOT, PROFILE.SLUG)
    return payload, passages, sample_by_id


def apply_projection_rules(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in PROJECTION_RULES[passage_id]:
        evaluated, count = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if count != int(rule["expected_count"]):
            raise JekyllProjectionError(
                f"projection rule count mismatch for {passage_id}: {rule['pattern']}"
            )
        applications.append(
            {
                "pattern": rule["pattern"],
                "replacement": rule["replacement"],
                "reason": rule["reason"],
                "match_count": count,
                "projection_only": True,
                "substantive_normalization": False,
            }
        )
    return evaluated, applications


def execute(
    input_path: Path, output_path: Path, paid_lock: Path, *, dry_run: bool
) -> tuple[int, dict[str, Any]]:
    fingerprint = projection_fingerprint()
    if fingerprint != EXPECTED_PROJECTION_FINGERPRINT:
        raise JekyllProjectionError(
            "projection fingerprint drift: "
            f"expected {EXPECTED_PROJECTION_FINGERPRINT}, observed {fingerprint}"
        )
    ensure_not_repeated(fingerprint)
    payload, passages, sample_by_id = validate_input(input_path)
    lock = BASE.lock_snapshot(paid_lock)
    if lock["sha256"] != EXPECTED_PAID_LOCK_SHA256:
        raise JekyllProjectionError("paid_tts.lock hash changed")
    if dry_run:
        return 0, {
            "schema": SCHEMA,
            "status": "DRY_RUN_PASS",
            "projection_fingerprint": fingerprint,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "paid_tts_lock": lock,
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
                "decoder_arm": prior["decoder_arm"],
                "audio_sha256": sample_by_id[passage_id]["audio_sha256"],
                "source_text_sha256": sample_by_id[passage_id]["source_text_sha256"],
                "raw_transcript": raw,
                "raw_transcript_sha256": prior["raw_transcript_sha256"],
                "evaluated_transcript": evaluated,
                "evaluated_transcript_sha256": sha256_text(evaluated),
                "source_equivalences_applied": applications,
                "new_asr_decoder_calls": 0,
                "resynthesis_performed": False,
                "unexpected_speech_deleted": False,
                "substantive_normalization_performed": False,
                **metrics,
                "pass": passed,
            }
        )
    passed_ids = [str(item["passage_id"]) for item in projected_reports if item["pass"]]
    failed_ids = [str(item["passage_id"]) for item in projected_reports if not item["pass"]]
    all_pass = len(passed_ids) == 4
    targeted_opening_allowed = failed_ids == ["opening_character"]

    result = deepcopy(payload)
    result["schema"] = SCHEMA
    result["projection_fingerprint"] = fingerprint
    result["input_evidence"] = {
        "path": str(input_path),
        "sha256": EXPECTED_INPUT_SHA256,
        "repair_fingerprint": EXPECTED_REPAIR_FINGERPRINT,
        "preserved_before_projection": True,
    }
    result["asr_repair_history"] = deepcopy(payload["asr"])
    result["asr"] = {
        "status": "PASS" if all_pass else "FAIL",
        "mode": "OFFLINE_BOUND_TRANSCRIPT_PROJECTION_NO_NEW_DECODER",
        "projection_fingerprint": fingerprint,
        "audio_derived_raw_transcripts": True,
        "new_asr_decoder_calls": 0,
        "reports": projected_reports,
    }
    result["status"] = (
        "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        if all_pass
        else "PRIVATE_REPRESENTATIVE_OBJECTIVE_PARTIAL_3_OF_4"
        if targeted_opening_allowed
        else "PRIVATE_REPRESENTATIVE_ASR_PROJECTION_FAIL_CLOSED"
    )
    result["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if all_pass
        else "NO_GO_OPENING_TARGETED_RESYNTHESIS_ALLOWED"
        if targeted_opening_allowed
        else "NO_GO_ASR_PROJECTION_FAILED"
    )
    result["projection_summary"] = {
        "passage_count": 4,
        "exact_pass_count": len(passed_ids),
        "passed_passage_ids": passed_ids,
        "failed_passage_ids": failed_ids,
        "new_asr_decoder_calls": 0,
        "resynthesis_performed": False,
        "substantive_normalization_performed": False,
    }
    result["next_stage_contract"] = {
        "status": result["status"],
        "targeted_resynthesis_allowed": targeted_opening_allowed,
        "target_passage_ids": failed_ids if targeted_opening_allowed else [],
        "listening_qa_allowed": all_pass,
        "full_title_generation_allowed": False,
        "upload_allowed": False,
        "publication_allowed": False,
        "release_gate_mutation_allowed": False,
    }
    blockers = [
        blocker
        for blocker in payload["blockers_to_release"]
        if blocker != "REPRESENTATIVE_ASR_REPAIR_FAILED"
    ]
    if not all_pass:
        blockers.insert(0, "REPRESENTATIVE_OPENING_ASR_CONTENT_MISMATCH")
    result["blockers_to_release"] = blockers
    result["safety"].update(
        {
            "provider_calls": 0,
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "retained_audio_hashes_unchanged": True,
            "paid_tts_lock": lock,
            "paid_tts_lock_touched": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        }
    )
    atomic_write_json(output_path, result)
    return (0 if all_pass else 3 if targeted_opening_allowed else 4), result


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
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "projection_fingerprint": payload["projection_fingerprint"],
                    "exact_pass_count": (payload.get("projection_summary") or {}).get(
                        "exact_pass_count"
                    ),
                    "failed_passage_ids": (payload.get("projection_summary") or {}).get(
                        "failed_passage_ids"
                    ),
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "new_asr_decoder_calls": 0,
                    "resynthesis_performed": False,
                    "listening_qa_performed": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return int(code)
    except (JekyllProjectionError, BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
