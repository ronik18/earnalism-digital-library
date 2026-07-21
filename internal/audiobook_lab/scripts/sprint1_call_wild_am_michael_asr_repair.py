#!/usr/bin/env python3
"""Run one bounded ASR-only bakeoff over retained Call of the Wild WAVs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
CORE_SPEC = importlib.util.spec_from_file_location("call_wild_retained_wav_asr_core", CORE_PATH)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name("sprint1_call_wild_am_michael_private_audition.py")
PROFILE_SPEC = importlib.util.spec_from_file_location("call_wild_kokoro_profile", PROFILE_PATH)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Call of the Wild profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.call_wild_am_michael_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.call_wild_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = "07cc70506e5d322e0de0407d9d28109b8f58e9dbadbfb1ed91685c35b7eeb1d7"
EXPECTED_ATTEMPT_FINGERPRINT = PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = "38d0227d93cde260025085bd9f7b5203cc80a64e5fceda66a3bff91795cd4fb2"
EXPECTED_PAID_LOCK_SHA256 = "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
EXPECTED_REPAIR_FINGERPRINT = "0b990e5c8efbc8fd8eebbe347a95d36922bc00c16f814911136e4a047888b36c"
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_exposition": "361126381d422714145cb3f09b0910ce629e5ccba42db85bcee55be3bcfa06a0",
    "spitz_final_conflict": "5e26f0b5b3664748181b997c20bc763eff3c117c6ac68a1a4c55ab384ff18c4f",
    "thornton_bond": "6454dd9eb0c3c50aa542bc5f65b28d7e606ec061ca55a7d667a6a75ef4061ba7",
    "closing_call": "2e1303a672760a3aa8d4f556e5f902ec42a5748b1106bee8690837235a8fd138",
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_exposition": {
        "source_text_sha256": "1791560e493d4ea492e40cca2a7ebb9722b70c1bd282a9853cb12877c5172216",
        "audio_sha256": "142dc34d80695597a51f0d3d7199392c5fedbcd5f865c4e40dc687140717bb87",
        "size_bytes": 1_827_644,
        "duration_seconds": 38.075,
    },
    "spitz_final_conflict": {
        "source_text_sha256": "11ea4acd69bd769dcbb1ac522aa27f90f47bd900a94fffaab4890279a3af5d6f",
        "audio_sha256": "ff10825d490813fd40bc2595df610216e5dd773c36196be2041c02f046d54506",
        "size_bytes": 4_891_244,
        "duration_seconds": 101.9,
    },
    "thornton_bond": {
        "source_text_sha256": "a0f70373151c13d69f99afbec80f83fb548e4b473eb19ad2ab05497c43927567",
        "audio_sha256": "41d63dba01fa4370bf87a63892da0281411540ae12ac422e83e419e900bbaae1",
        "size_bytes": 3_561_644,
        "duration_seconds": 74.2,
    },
    "closing_call": {
        "source_text_sha256": "01835614d16f85410731e48e6a4b11b6fb8f2c75a8cdaa68ba34ab849d09134b",
        "audio_sha256": "61af540b5a7586a245aab7ef8b56394aa359902b249fe8986cf89ff388524942",
        "size_bytes": 3_577_244,
        "duration_seconds": 74.525,
    },
}
VOCABULARY_PROMPT = PROFILE.ASR_VOCABULARY_PROMPT
DECODING_ARMS = (
    {
        "id": "unprompted_beam_2",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 2,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
    {
        "id": "unprompted_greedy",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": None,
        "patience": None,
        "hallucination_silence_threshold": 0.5,
    },
    {
        "id": "canonical_vocabulary_beam_2",
        "initial_prompt": VOCABULARY_PROMPT,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 2,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
)
EQUIVALENCE_POLICY = {
    "opening_exposition": (
        {
            "pattern": r"\btidewater\b",
            "replacement": "tide-water",
            "expected_count_when_observed": 1,
            "reason": "ASR compound token for source tide-water",
        },
    ),
    "spitz_final_conflict": (
        {
            "pattern": r"\bforeleg\b",
            "replacement": "fore-leg",
            "expected_count_when_observed": 2,
            "reason": "ASR compound token for two source fore-leg occurrences",
        },
        {
            "pattern": r"\bmaneuvered\b",
            "replacement": "manœuvred",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source manœuvred",
        },
        {
            "pattern": r"\bspits\b",
            "replacement": "Spitz",
            "expected_count_when_observed": 2,
            "reason": "ASR homophone spelling for the source-bound dog name Spitz",
        },
        {
            "pattern": r"\bclimbs\b",
            "replacement": "climes",
            "expected_count_when_observed": 1,
            "reason": "ASR homophone spelling for source climes",
        },
    ),
    "thornton_bond": (),
    "closing_call": (
        {
            "pattern": r"\bmoosehide\b",
            "replacement": "moose-hide",
            "expected_count_when_observed": 1,
            "reason": "ASR compound token for source moose-hide",
        },
        {
            "pattern": r"\bmold\b",
            "replacement": "mould",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source mould",
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "metal / medal",
    "missing opening But",
    "feigned / feign",
    "missing source article a",
    "coated / coded",
    "unexpected speech deletion",
    "substantive word substitution",
    "missing content insertion",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/the-call-of-the-wild_release_gate_evidence.json",
)

CallWildASRRepairError = CORE.GiftEmmaASRRepairError


def configure_core() -> None:
    bindings = {
        "ROOT": ROOT,
        "PROFILE": PROFILE,
        "SCHEMA": SCHEMA,
        "EXPECTED_INPUT_SCHEMA": EXPECTED_INPUT_SCHEMA,
        "EXPECTED_INPUT_STATUS": EXPECTED_INPUT_STATUS,
        "EXPECTED_INPUT_SHA256": EXPECTED_INPUT_SHA256,
        "EXPECTED_ATTEMPT_FINGERPRINT": EXPECTED_ATTEMPT_FINGERPRINT,
        "EXPECTED_PRIOR_ASR_FINGERPRINT": EXPECTED_PRIOR_ASR_FINGERPRINT,
        "EXPECTED_PAID_LOCK_SHA256": EXPECTED_PAID_LOCK_SHA256,
        "EXPECTED_PRIOR_TRANSCRIPT_HASHES": EXPECTED_PRIOR_TRANSCRIPT_HASHES,
        "EXPECTED_SAMPLE_BINDINGS": EXPECTED_SAMPLE_BINDINGS,
        "DECODING_ARMS": DECODING_ARMS,
        "EQUIVALENCE_POLICY": EQUIVALENCE_POLICY,
        "FORBIDDEN_NORMALIZATIONS": FORBIDDEN_NORMALIZATIONS,
        "ASR_SCORE_MIN": ASR_SCORE_MIN,
        "ASR_COVERAGE_MIN": ASR_COVERAGE_MIN,
        "DEFAULT_INPUT": DEFAULT_INPUT,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_WHISPER_CACHE": DEFAULT_WHISPER_CACHE,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "NO_REPEAT_FILES": NO_REPEAT_FILES,
    }
    for name, value in bindings.items():
        setattr(CORE, name, value)
    CORE.evaluate_transcript = evaluate_transcript


def evaluate_transcript(
    passage: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm_id: str,
) -> dict[str, Any]:
    evaluated, applications = CORE.apply_equivalences(str(passage["passage_id"]), transcript)
    metrics = PROFILE.BASE.ordered_token_integrity(str(passage["text"]), evaluated)
    passed = bool(
        float(metrics["score"]) >= ASR_SCORE_MIN
        and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
        and metrics["first_words_match"] is True
        and metrics["last_words_match"] is True
        and metrics["ordered_content_integrity_pass"] is True
        and metrics["no_missing_content"] is True
        and metrics["no_duplicate_content"] is True
        and metrics["no_reordered_content"] is True
        and metrics["no_unexpected_content"] is True
    )
    return {
        "passage_id": passage["passage_id"],
        "decoder_arm": arm_id,
        "audio_sha256": sample["audio_sha256"],
        "source_text_sha256": passage["text_sha256"],
        "raw_transcript": transcript,
        "raw_transcript_sha256": PROFILE.BASE.sha256_text(transcript),
        "evaluated_transcript": evaluated,
        "evaluated_transcript_sha256": PROFILE.BASE.sha256_text(evaluated),
        "source_equivalences_applied": applications,
        "substantive_normalization_performed": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def repair_fingerprint() -> str:
    configure_core()
    observed = CORE.repair_fingerprint()
    if observed != EXPECTED_REPAIR_FINGERPRINT:
        raise CallWildASRRepairError(
            f"Call of the Wild ASR repair contract changed: observed {observed}"
        )
    return observed


def execute(
    input_path: Path,
    output_path: Path,
    whisper_cache: Path,
    paid_lock: Path,
    *,
    dry_run: bool = False,
    model_loader: Callable[[Path], Any] = CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = CORE.run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    configure_core()
    repair_fingerprint()
    code, result = CORE.execute(
        input_path,
        output_path,
        whisper_cache,
        paid_lock,
        dry_run=dry_run,
        model_loader=model_loader,
        decoder=decoder,
    )
    if dry_run:
        return code, result
    repair = result["asr_repair"]
    repair.pop("substantive_were_are_normalized", None)
    repair["substantive_normalization_performed"] = False
    passed = result["status"] == "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
    result["go_no_go"] = "GO_PRIVATE_LISTENING_QA_ONLY" if passed else "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
    result["blockers_to_release"] = [
        (
            "CALL_WILD_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            if blocker == "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            else blocker
        )
        for blocker in result["blockers_to_release"]
    ]
    CORE.write_json(output_path, result)
    return code, result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        code, result = execute(
            args.input.resolve(),
            args.output.resolve(),
            args.whisper_cache.resolve(),
            args.paid_lock.resolve(),
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "repair_fingerprint": result.get("repair_fingerprint")
                    or (result.get("asr_repair") or {}).get("repair_fingerprint"),
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "retained_audio_immutable": (
                        result.get("retained_audio_immutable")
                        if args.dry_run
                        else (result.get("asr_repair") or {}).get("retained_audio_immutable")
                    ),
                    "decoder_arms": len(DECODING_ARMS),
                    "resynthesis_performed": False,
                    "audio_edit_or_trim_performed": False,
                    "listening_provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (CallWildASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
