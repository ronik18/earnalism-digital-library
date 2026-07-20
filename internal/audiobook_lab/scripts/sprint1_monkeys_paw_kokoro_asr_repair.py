#!/usr/bin/env python3
"""Run one bounded ASR-only repair over retained Monkey's Paw WAVs.

Three deterministic local Whisper arms inspect every immutable private WAV:
unprompted beam, unprompted greedy, and a vocabulary-only prompted beam.  All
raw candidates are retained.  Only the acoustically identical ``to-night`` /
``tonight`` tokenization is normalized.  Proper names, missing words,
pronunciation substitutions, and unexpected speech may not be rewritten.
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
    "retained_wav_asr_repair_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR repair core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name(
    "sprint1_monkeys_paw_kokoro_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "monkeys_paw_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Monkey's Paw profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.monkeys_paw_af_bella_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.monkeys_paw_private_audition.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "3801f927ed3f37e1892392e017f3db29b648fd0ebab57c086c339c75ccd5b539"
)
EXPECTED_ATTEMPT_FINGERPRINT = PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "7a65147b1c38c2ff4164a425e99c074eb930b2b0e42c1a6e257fdf03efac5671"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_domestic_tension": (
        "4461b6b881d1d20f41ba86f8821dc3c6166488a4eac9f4be8550498897e853a8"
    ),
    "paw_warning_and_fate": (
        "6d701decdd44cbcebe5444cce0eeb11c76fd7f1c7b49ee63fdfbf627e6930204"
    ),
    "factory_news_and_grief": (
        "be269616d12c39c13f25a1fd4bdbc99caaf4f06822bf1e80518c5bf0bc10ae67"
    ),
    "final_knocking_and_third_wish": (
        "47eb5c98c82ca08f8728a16fdcc069a6e5b34089fcd1f53a3010adc46b770ce8"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_domestic_tension": {
        "source_text_sha256": (
            "1505ffdc29416106677ad7c3ef7ea0a3db602c1069e1d72b81327721c1fe5765"
        ),
        "audio_sha256": (
            "f05904b0e4a8172dfb6409390d0e696fd5fb14dd8b7a4599738b7ecad65f1f7e"
        ),
        "size_bytes": 1_113_644,
        "duration_seconds": 23.2,
    },
    "paw_warning_and_fate": {
        "source_text_sha256": (
            "a3ec2e40908f432cca118c418e743329bccc9f411908bc16da2f725e8e43007d"
        ),
        "audio_sha256": (
            "92db4c64575a3198fee24d94ac882d1cef32e49c6b43cee49f1b3f4c1c8924cd"
        ),
        "size_bytes": 2_802_044,
        "duration_seconds": 58.375,
    },
    "factory_news_and_grief": {
        "source_text_sha256": (
            "6877bbcbea4fdfd7729b41ff27dc422b18dd6d44b7b0e4893555ba5e109cf0aa"
        ),
        "audio_sha256": (
            "9c15cc86759e7258be239fdc4166c768b8acf4cb98a3268006df7137950a070f"
        ),
        "size_bytes": 2_673_644,
        "duration_seconds": 55.7,
    },
    "final_knocking_and_third_wish": {
        "source_text_sha256": (
            "9198f815c21620148cfab038af5bdaadedd7397567c9a9010c1d1bc340148fb4"
        ),
        "audio_sha256": (
            "0d5fd578ba36d0826ac63ebf5bbdebb9eadf3e22186855a41a16d42206b75081"
        ),
        "size_bytes": 3_481_244,
        "duration_seconds": 72.525,
    },
}

VOCABULARY_PROMPT = (
    "Canonical spellings: to-night; age is wont; Maw and Meggins; "
    "Oh, thank God; slower-witted; fusillade. Preserve every spoken word."
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
    "opening_domestic_tension": (
        {
            "pattern": r"\btonight\b",
            "replacement": "to night",
            "expected_count_when_observed": 1,
            "reason": "single-token ASR rendering of the acoustically identical source to-night",
        },
    ),
    "paw_warning_and_fate": (),
    "factory_news_and_grief": (),
    "final_knocking_and_third_wish": (),
}
FORBIDDEN_NORMALIZATIONS = (
    "age is wont / ages want",
    "Maw / Ma",
    "Meggins / Meghan's",
    "missing Oh",
    "missing witted",
    "fusillade / fuselage",
    "unexpected speech deletion",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_af_bella_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_af_bella_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)

MonkeysPawASRRepairError = CORE.GiftEmmaASRRepairError


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
    return CORE.repair_fingerprint()


def apply_equivalences(passage_id: str, transcript: str):
    _configure_core()
    return CORE.apply_equivalences(passage_id, transcript)


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
            "MONKEYS_PAW_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
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
    except (MonkeysPawASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
