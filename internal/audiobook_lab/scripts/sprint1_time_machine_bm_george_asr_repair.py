#!/usr/bin/env python3
"""Run one bounded ASR-only bakeoff over retained Time Machine WAVs.

Three deterministic local Whisper arms inspect each immutable private WAV.
Only exact-count spelling and compound-token equivalences are permitted.
The module cannot synthesize, edit audio, listen, upload, publish, or mutate
controlled release truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
CORE_SPEC = importlib.util.spec_from_file_location(
    "time_machine_retained_wav_asr_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR repair core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name(
    "sprint1_time_machine_bm_george_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "time_machine_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Time Machine profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.time_machine_bm_george_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.time_machine_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "d160ff37eda1d1abc2d12d8bee99c1516d3874e0765fe509a1673292e66130a6"
)
EXPECTED_ATTEMPT_FINGERPRINT = PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "54744926c96997eeaaf9530369e1dc38b454c21ad72554af33abe6b1a6d06577"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
EXPECTED_REPAIR_FINGERPRINT = (
    "058de6aa9d7477d7d8eb95dcdf836641dd09a7c2287f2bf7184fb03da13dfa15"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_exposition": "f848ac024fc49b373e71f40c5472efbb14d58a9f62061d56c7d964cf384c7fd0",
    "eloi_first_contact": "f4cdd5c225e1fc328df9d59b00a97e39eb5dde7a556b00c529bfdc319927bae6",
    "morlock_darkness": "d7ae08debe1e46c0393e4d23e8dcd37a791d1950143b71802df30545a4f9fd5b",
    "epilogue_tenderness": "9bb6e4f9632f30f7482e0c69ee7dbb2e9450d12e71f38139824cfa06abfe66ad",
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_exposition": {
        "source_text_sha256": "22dc5f715d1f9ecf4a32b6a92c57d97cd6f86c39c70d7b997c453ec197eb82c2",
        "audio_sha256": "1a45c3b5ba1c06435ad66bbf00fb4c98fc46628357175990f03d2b9421c0e0e9",
        "size_bytes": 2_290_844,
        "duration_seconds": 47.725,
    },
    "eloi_first_contact": {
        "source_text_sha256": "6262bd33a6ab3f8e742c55372b2eb4421ca84ec75e123c12ec36528c36a62077",
        "audio_sha256": "f45ade35e35fe588e993a0ee60f62b7951c92d8fe9b2d3a3c976acc811860ce5",
        "size_bytes": 3_834_044,
        "duration_seconds": 79.875,
    },
    "morlock_darkness": {
        "source_text_sha256": "f1a209de898abbbaf96624ac4ca16d06f9f065bd2d6137a995586dc2610ee084",
        "audio_sha256": "ee0c32a3466ce3d30bc178cf9c70d23c012fc28452c742f4e5536213e12157cb",
        "size_bytes": 2_518_844,
        "duration_seconds": 52.475,
    },
    "epilogue_tenderness": {
        "source_text_sha256": "ef675e8a4077b5e93c07f9e71102cf66ff51711a28be1ab22fef05bc1f78782b",
        "audio_sha256": "6c920ab0557a16fd1fd5c5aaabd9e020a3120f32c1a176f8f7e858704fcd67a1",
        "size_bytes": 4_506_044,
        "duration_seconds": 93.875,
    },
}

VOCABULARY_PROMPT = (
    "Canonical spellings: Time Traveller; Weena; Morlocks; Cretaceous; "
    "Jurassic; plesiosaurus; Oolitic; Triassic; civilisation; shrivelled; "
    "ninepins. Preserve every spoken source word and British spelling."
)
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
    "opening_exposition": (),
    "eloi_first_contact": (
        {
            "pattern": r"\bnine pins\b",
            "replacement": "ninepins",
            "expected_count_when_observed": 1,
            "reason": "ASR token split for the acoustically identical source compound ninepins",
        },
    ),
    "morlock_darkness": (),
    "epilogue_tenderness": (
        {
            "pattern": r"\bcivilization\b",
            "replacement": "civilisation",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source British spelling civilisation",
        },
        {
            "pattern": r"\bshriveled\b",
            "replacement": "shrivelled",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source British spelling shrivelled",
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "I and / ironing",
    "missing plesiosaurus",
    "unexpected speech deletion",
    "substantive word substitution",
    "missing content insertion",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_kokoro_bm_george_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_kokoro_bm_george_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/"
    "sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_release_gate_evidence.json",
)

TimeMachineASRRepairError = CORE.GiftEmmaASRRepairError


def _configure_core() -> None:
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
    evaluated, applications = CORE.apply_equivalences(
        str(passage["passage_id"]), transcript
    )
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


def validate_input(path: Path):
    _configure_core()
    return CORE.validate_input(path)


def repair_fingerprint() -> str:
    _configure_core()
    observed = CORE.repair_fingerprint()
    if observed != EXPECTED_REPAIR_FINGERPRINT:
        raise TimeMachineASRRepairError(
            "Time Machine ASR repair contract changed without fingerprint rebind"
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
    _configure_core()
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
    passed = result["status"] == (
        "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
    )
    result["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if passed
        else "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
    )
    result["blockers_to_release"] = [
        (
            "TIME_MACHINE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
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
                        else (result.get("asr_repair") or {}).get(
                            "retained_audio_immutable"
                        )
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
    except (TimeMachineASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
