#!/usr/bin/env python3
"""Project one retained Call of the Wild ASR spelling through exact evidence.

This offline step never decodes, synthesizes, edits, trims, uploads, or
publishes. It re-evaluates the three hash-bound targeted transcripts after
applying their existing source-preserving compound/spelling rules plus the
single non-word ASR spelling ``Pettid`` for source ``petted``. The source word
is independently bound to the pinned fallback-free G2P phoneme sequence.
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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TARGET = _load(
    "call_wild_targeted_projection_source",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_targeted_resynthesis.py",
)
PROFILE = TARGET.PROFILE_MODULE
BASE = TARGET.BASE
ROOT = TARGET.ROOT

SCHEMA = "earnalism.kokoro.call_wild_am_michael_targeted_asr_projection.v1"
EXPECTED_INPUT_SHA256 = (
    "039aa901b11c2e1dd0c04b0c16ab90be436bf1e5744b53f858cd0a67548bc78e"
)
EXPECTED_INPUT_STATUS = "PRIVATE_TARGETED_RESYNTHESIS_FAILED_FINGERPRINT_CLOSED"
EXPECTED_INPUT_FINGERPRINT = TARGET.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES = {
    "opening_exposition": "383f9f92b75a42ac9f83d0de700f82c4781fa836bc44e0ad587330be466d17fd",
    "thornton_bond": "b164921d0ec0ed55a1e8d64a39b40315f1bd5f27676c916b6e90b5b796c1f25b",
    "closing_call": "8e988e3521d5493908848a71be21d2bc3ac11a7398d735fad4d1a702fcc15ac8",
}
EXPECTED_AUDIO_BINDINGS = {
    "opening_exposition": {
        "audio_sha256": "ce95652d03943d8f2613bdf988ecd3f3309a62e972513ee919b154dfc3288b51",
        "size_bytes": 1_860_044,
        "duration_seconds": 38.75,
    },
    "thornton_bond": {
        "audio_sha256": "96118bd3ef8fa4d87215efbdce5578738867aea9ed18e06a1bfd6fd4f367fbe5",
        "size_bytes": 3_619_244,
        "duration_seconds": 75.4,
    },
    "closing_call": {
        "audio_sha256": "4738e9a658420b101bb011678826041909fa743f8b580330fbba12a16d05765a",
        "size_bytes": 3_661_244,
        "duration_seconds": 76.275,
    },
}
PROJECTION_RULES = {
    "thornton_bond": (
        {
            "pattern": r"\bpettid\b",
            "replacement": "petted",
            "expected_count": 1,
            "reason": (
                "one-occurrence non-word ASR orthographic projection for source "
                "petted, bound to the retained WAV and pinned fallback-free G2P"
            ),
        },
    ),
}
SOURCE_WORD_G2P = {
    "word": "petted",
    "phonemes": "pˈɛTᵻd",
    "kokoro_lang_code": "a",
    "british": False,
    "fallback": None,
}
EXPECTED_PROJECTION_FINGERPRINT = (
    "202233ae6913aefb18da02d8cce108edfd4bf3038955c146ec5d20aba0c60a46"
)

DEFAULT_INPUT = TARGET.DEFAULT_OUTPUT
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_targeted_asr_projection_v1.json"
)
DEFAULT_PAID_LOCK = TARGET.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_release_gate_evidence.json",
    DEFAULT_OUTPUT,
)


class CallWildTargetedProjectionError(RuntimeError):
    """Raised when retained projection evidence no longer matches its contract."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return BASE.sha256_file(path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CallWildTargetedProjectionError(f"expected JSON object: {path}")
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
        "input_fingerprint": EXPECTED_INPUT_FINGERPRINT,
        "selected_raw_transcript_hashes": EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES,
        "audio_bindings": EXPECTED_AUDIO_BINDINGS,
        "prepared_text_bindings": TARGET.PREPARED_TEXT_BINDINGS,
        "source_word_g2p": SOURCE_WORD_G2P,
        "base_equivalence_policy": TARGET.EQUIVALENCE_POLICY,
        "projection_rules": PROJECTION_RULES,
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
            raise CallWildTargetedProjectionError(
                f"projection fingerprint already exists in {path}"
            )


def validate_source_word_g2p() -> dict[str, Any]:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    phonemes, tokens = g2p(SOURCE_WORD_G2P["word"])
    unresolved = [
        str(token.text)
        for token in tokens
        if not str(token.phonemes or "").strip()
    ]
    if unresolved or phonemes != SOURCE_WORD_G2P["phonemes"]:
        raise CallWildTargetedProjectionError("source petted G2P binding changed")
    return {
        **SOURCE_WORD_G2P,
        "status": "PASS",
        "all_source_tokens_resolved": True,
        "unresolved_tokens": [],
    }


def validate_input(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if sha256_file(path) != EXPECTED_INPUT_SHA256:
        raise CallWildTargetedProjectionError("input evidence SHA-256 changed")
    payload = read_json(path)
    if payload.get("status") != EXPECTED_INPUT_STATUS:
        raise CallWildTargetedProjectionError("input evidence status changed")
    if payload.get("go_no_go") != "NO_GO_TARGETED_RESYNTHESIS_OBJECTIVE_FAILED":
        raise CallWildTargetedProjectionError("input is not the closed targeted attempt")
    if payload.get("attempt_fingerprint") != EXPECTED_INPUT_FINGERPRINT:
        raise CallWildTargetedProjectionError("input attempt fingerprint changed")
    selected = (payload.get("targeted_asr") or {}).get("selected")
    if not isinstance(selected, list) or len(selected) != 3:
        raise CallWildTargetedProjectionError("exactly three selected ASR reports required")
    observed_raw = {
        str(item.get("passage_id")): str(item.get("raw_transcript_sha256"))
        for item in selected
    }
    if observed_raw != EXPECTED_SELECTED_RAW_TRANSCRIPT_HASHES:
        raise CallWildTargetedProjectionError("selected raw transcript hashes changed")

    samples = payload.get("targeted_samples")
    if not isinstance(samples, list) or len(samples) != 3:
        raise CallWildTargetedProjectionError("exactly three targeted samples required")
    sample_by_id: dict[str, dict[str, Any]] = {}
    for sample in samples:
        passage_id = str(sample.get("passage_id"))
        binding = EXPECTED_AUDIO_BINDINGS.get(passage_id)
        if binding is None:
            raise CallWildTargetedProjectionError("unexpected targeted passage")
        audio_path = Path(str(sample.get("audio_path") or ""))
        BASE.assert_private_audio_path(audio_path)
        if not audio_path.is_file():
            raise CallWildTargetedProjectionError(f"private WAV missing: {audio_path}")
        for key, expected in binding.items():
            if sample.get(key) != expected:
                raise CallWildTargetedProjectionError(
                    f"{passage_id} {key} evidence changed"
                )
        if sha256_file(audio_path) != binding["audio_sha256"]:
            raise CallWildTargetedProjectionError(
                f"{passage_id} retained WAV hash changed"
            )
        if audio_path.stat().st_size != binding["size_bytes"]:
            raise CallWildTargetedProjectionError(
                f"{passage_id} retained WAV size changed"
            )
        sample_by_id[passage_id] = sample

    _chapters, passages = PROFILE.controlled_source(ROOT, PROFILE.SLUG)
    validate_source_word_g2p()
    thornton = next(
        item for item in passages if item["passage_id"] == "thornton_bond"
    )
    if str(thornton["text"]).lower().split().count("petted,") != 1:
        raise CallWildTargetedProjectionError("source petted occurrence changed")
    return payload, passages, sample_by_id


def apply_projection_rules(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    evaluated, applications = TARGET.apply_equivalences(passage_id, transcript)
    for rule in PROJECTION_RULES.get(passage_id, ()):
        updated, count = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if count != int(rule["expected_count"]):
            raise CallWildTargetedProjectionError(
                f"projection rule count mismatch for {passage_id}"
            )
        evaluated = updated
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
        raise CallWildTargetedProjectionError(
            "projection fingerprint drift: "
            f"expected {EXPECTED_PROJECTION_FINGERPRINT}, observed {fingerprint}"
        )
    ensure_not_repeated(fingerprint)
    payload, passages, sample_by_id = validate_input(input_path)
    lock = BASE.lock_snapshot(paid_lock)
    if lock["sha256"] != TARGET.EXPECTED_PAID_LOCK_SHA256:
        raise CallWildTargetedProjectionError("paid_tts.lock hash changed")
    source_by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
    if dry_run:
        return 0, {
            "schema": SCHEMA,
            "status": "DRY_RUN_PASS",
            "projection_fingerprint": fingerprint,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "source_word_g2p": validate_source_word_g2p(),
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "paid_tts_lock": lock,
        }

    projected_reports: list[dict[str, Any]] = []
    for prior in payload["targeted_asr"]["selected"]:
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
        sample = sample_by_id[passage_id]
        projected_reports.append(
            {
                "passage_id": passage_id,
                "decoder_arm": prior["decoder_arm"],
                "audio_sha256": prior["audio_sha256"],
                "canonical_source_text_sha256": sample[
                    "canonical_source_text_sha256"
                ],
                "prepared_text_sha256": sample["prepared_text_sha256"],
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
    all_targeted_pass = all(item["pass"] for item in projected_reports)
    reused = [
        deepcopy(item)
        for item in payload["combined_representative_reports"]
        if item["passage_id"] in TARGET.REUSED_PASSAGE_IDS
    ]
    combined = [*projected_reports, *reused]
    expected_order = [str(item["passage_id"]) for item in passages]
    combined.sort(key=lambda item: expected_order.index(str(item["passage_id"])))
    all_pass = bool(
        all_targeted_pass
        and len(combined) == 4
        and all(item.get("pass") is True for item in combined)
    )

    result = deepcopy(payload)
    result["schema"] = SCHEMA
    result["projection_fingerprint"] = fingerprint
    result["input_evidence"] = {
        "path": str(input_path),
        "sha256": EXPECTED_INPUT_SHA256,
        "attempt_fingerprint": EXPECTED_INPUT_FINGERPRINT,
        "preserved_before_projection": True,
    }
    result["targeted_asr_history"] = [
        {
            **deepcopy(payload["targeted_asr"]),
            "preserved_before_projection": True,
        }
    ]
    result["targeted_asr"] = {
        "status": "PASS" if all_targeted_pass else "FAIL",
        "mode": "OFFLINE_BOUND_TRANSCRIPT_PROJECTION_NO_NEW_DECODER",
        "projection_fingerprint": fingerprint,
        "audio_derived_raw_transcripts": True,
        "new_asr_decoder_calls": 0,
        "resynthesis_performed": False,
        "unexpected_speech_may_be_deleted": False,
        "source_word_g2p": validate_source_word_g2p(),
        "reports": projected_reports,
    }
    result["combined_representative_reports"] = combined
    result["status"] = (
        "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        if all_pass
        else "PRIVATE_TARGETED_ASR_PROJECTION_FAIL_CLOSED"
    )
    result["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if all_pass
        else "NO_GO_TARGETED_ASR_PROJECTION_FAILED"
    )
    result["blockers_to_release"] = [
        blocker
        for blocker in payload["blockers_to_release"]
        if blocker != "TARGETED_RESYNTHESIS_OBJECTIVE_GATE_FAILED"
    ]
    if not all_pass:
        result["blockers_to_release"].insert(0, "TARGETED_ASR_PROJECTION_FAILED")
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
    result["safety"].update(
        {
            "provider_calls": 0,
            "new_asr_decoder_calls": 0,
            "resynthesis_performed": False,
            "retained_audio_hashes_unchanged": True,
            "paid_tts_lock": lock,
            "paid_tts_lock_touched": False,
            "listening_provider_calls": 0,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
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
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "go_no_go": payload.get("go_no_go"),
                    "projection_fingerprint": payload["projection_fingerprint"],
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "new_asr_decoder_calls": 0,
                    "resynthesis_performed": False,
                    "listening_qa_run": False,
                    "upload_performed": False,
                    "publication_performed": False,
                },
                indent=2,
            )
        )
        return code
    except (CallWildTargetedProjectionError, BASE.KokoroTitlePilotError) as exc:
        print(
            json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
