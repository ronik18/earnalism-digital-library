#!/usr/bin/env python3
"""Reverify retained Secret Garden bf_emma WAVs without resynthesis.

Two unprompted local Whisper decoder arms run against every immutable private
WAV. Only passage-scoped, exact-count British/American spelling and Yorkshire
dialect tokenization equivalents are allowed. Unexpected speech cannot be
deleted. This command cannot synthesize, edit audio, listen, upload, publish,
or mutate release truth.
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
    "sprint1_secret_garden_kokoro_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "secret_garden_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Secret Garden profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.secret_garden_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.secret_garden_private_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "d326bfde0b2b8ef584ae8428a92f98793d0b16537bedac81cfc2f437cf7e6d0f"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "f849e64889b7a614bce6eb2ad3c0b5630424cf5d338e6a1b9d216318842aceff"
)
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "9d7a37a70d777d3e6db539ef498ed38afa0e680f1c7425e293ce4c862ae9d450"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "9361db87eee060cfceac6e4594c8d94cb02f02481d88d1e7f5055684c4081ac2"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_india_character": (
        "57d477c1cbe4df5f5bac89cc7d231cda8bd3d675b18154e994c0a124d1dae04e"
    ),
    "garden_key_discovery": (
        "be2d244ccbfe6e4e4a6c469947e76353d29b6c7a3f2b71d7c79a0eaf24275075"
    ),
    "colin_midnight_dialogue": (
        "4790117d7ac855d2b620afa1688dbc005cb726b2aef9bd4332d6b7d04aea8214"
    ),
    "healing_finale": (
        "e5f7d133f3ef842c5fcf59b8a51fd2d4f8c0ec94cdf4b22480d53b57268f1928"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
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
)

# These rules preserve the acoustically spoken source and only recover exact
# manuscript spelling/tokenization. They cannot remove the opening's trailing
# unexpected "the" if an unprompted decoder still hears it.
EQUIVALENCE_POLICY = {
    "opening_india_character": (),
    "garden_key_discovery": (),
    "colin_midnight_dialogue": (
        {
            "pattern": r"\bgrey\b",
            "replacement": "gray",
            "expected_count_when_observed": 1,
            "reason": "British ASR spelling for the source American gray",
        },
    ),
    "healing_finale": (
        {
            "pattern": r"\bifs\b",
            "replacement": "if tha's",
            "expected_count_when_observed": 1,
            "reason": (
                "ASR contraction of the acoustically spoken Yorkshire source "
                "if tha's"
            ),
        },
        {
            "pattern": r"\bacross the grass\b",
            "replacement": "across th grass",
            "expected_count_when_observed": 1,
            "reason": (
                "standard ASR expansion of the source Yorkshire elision "
                "across th' grass"
            ),
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "unexpected trailing the",
    "unexpected speech deletion",
    "missing source word invention",
    "audio edit or trim",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)

SecretGardenASRRepairError = CORE.GiftEmmaASRRepairError


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
    CORE.assert_private_audio = PROFILE.BASE.assert_private_audio_path


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
        "unexpected_speech_deleted_or_normalized": False,
        "audio_edit_or_trim_performed": False,
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
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = (
        CORE.run_decoding_arm
    ),
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
    repair["unexpected_speech_deleted_or_normalized"] = False
    repair["audio_edit_or_trim_performed"] = False
    result["blockers_to_release"] = [
        blocker
        for blocker in result["blockers_to_release"]
        if blocker
        not in {
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "OWNER_10_TARGET_NOT_VERIFIED",
        }
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
                    or (result.get("asr_repair") or {}).get(
                        "repair_fingerprint"
                    ),
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "retained_audio_immutable": (
                        result.get("retained_audio_immutable")
                        if args.dry_run
                        else (result.get("asr_repair") or {}).get(
                            "retained_audio_immutable"
                        )
                    ),
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
    except (
        SecretGardenASRRepairError,
        PROFILE.BASE.KokoroTitlePilotError,
    ) as exc:
        print(
            json.dumps(
                {"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2
            )
        )
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
