#!/usr/bin/env python3
"""Run one bounded ASR-only repair over retained Masque bf_emma WAVs.

This title-specific contract reuses the established retained-WAV repair core.
Both unprompted local Whisper decoder arms run over every immutable private WAV,
and every raw candidate is retained.  Only exact-count colour/color,
revellers/revelers, and fire light/firelight equivalences are allowed.  Missing
``harken`` and trailing unexpected ``you`` remain substantive failures unless a
decoder arm resolves them from the audio.  No synthesis, audio edit, listening,
provider, upload, publication, or release-state mutation is possible here.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
CORE_SPEC = importlib.util.spec_from_file_location("retained_wav_asr_repair_core", CORE_PATH)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR repair core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name("sprint1_masque_kokoro_private_audition.py")
PROFILE_SPEC = importlib.util.spec_from_file_location("masque_kokoro_profile", PROFILE_PATH)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Masque Kokoro profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.masque_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.masque_private_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = "5380e1c4347e52be3857c3c17cc26ded88c88f9147a9fd0064dcce25f1d76c20"
EXPECTED_ATTEMPT_FINGERPRINT = (
    "dabff0b69632542f712b259fe039c9fa74092506141c71adb1d76b5afc21f33a"
)
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "bcac5ecbe5afdbc64e042a2158e55793cdb79c4c1ac181cb56313a6c5fd369dc"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_plague_and_prospero": (
        "b6f5ad101ba672d06c3c4010d874c255c7688b15c73281fc6ffd3529befc4e82"
    ),
    "black_room_blood_light": (
        "7c4db44ef6204b8f77cc274b8b712cc976e96c5ba2a14b8dc2aed65ce9a4960c"
    ),
    "ebony_clock_tension": (
        "4ee570b4c41b6ba5603100afb8cfec0751a7322809c3d468860e03fcfb97385f"
    ),
    "final_confrontation_and_dominion": (
        "ba650938404ad815449123920e26655893a175d6a8fe93d6d51d1cb46540f8ca"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_plague_and_prospero": {
        "source_text_sha256": (
            "16e78152465fec59b1a45da95cad7eb8f7dffd7f0e845a372e3ff12e33809e48"
        ),
        "audio_sha256": (
            "50ff80a37a6ec44a899a1d5e1c8485d711c01fa931903d465a9165df2c301d7d"
        ),
        "size_bytes": 1_476_044,
        "duration_seconds": 30.75,
    },
    "black_room_blood_light": {
        "source_text_sha256": (
            "4e908021ee2eb41c0897de247df3ec5b46f9f54206fef071ba7dc2dd00c19e0b"
        ),
        "audio_sha256": (
            "a1154d9771f17e88cb70ac874ca8e9a491d73ebc20c17f247689e43a2399e370"
        ),
        "size_bytes": 2_800_844,
        "duration_seconds": 58.35,
    },
    "ebony_clock_tension": {
        "source_text_sha256": (
            "b23e8a225f916e6c56b810058cdf70f819a08f3ab155b71afcb1075f8d971227"
        ),
        "audio_sha256": (
            "1a1451fbaa957ff5dfb7ead723d1107433c3266209ea64af787665946556a9bc"
        ),
        "size_bytes": 1_522_844,
        "duration_seconds": 31.725,
    },
    "final_confrontation_and_dominion": {
        "source_text_sha256": (
            "3156906cde350ac6a1964dd686fa7b92475390b0db3f5fd13d2fca277c3b2335"
        ),
        "audio_sha256": (
            "c383b4aaaa8978c7376cebe2816331cc479d5e62732975e0f96d2f53bfca4e37"
        ),
        "size_bytes": 2_637_644,
        "duration_seconds": 54.95,
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

# These rules map only acoustically identical ASR forms back to the exact
# manuscript spelling/tokenization.  A variant is accepted only at its bound
# passage-specific count.  No rule can invent ``harken`` or erase ``you``.
EQUIVALENCE_POLICY = {
    "opening_plague_and_prospero": (),
    "black_room_blood_light": (
        {
            "pattern": r"\bcolor\b",
            "replacement": "colour",
            "expected_count_when_observed": 2,
            "reason": "American ASR spelling for the source British colour",
        },
        {
            "pattern": r"\bfirelight\b",
            "replacement": "fire light",
            "expected_count_when_observed": 1,
            "reason": "compound ASR tokenization for the source fire light",
        },
    ),
    "ebony_clock_tension": (),
    "final_confrontation_and_dominion": (
        {
            "pattern": r"\brevelers\b",
            "replacement": "revellers",
            "expected_count_when_observed": 2,
            "reason": "American ASR spelling for the source British revellers",
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "missing harken",
    "trailing unexpected you",
    "unexpected speech deletion",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-masque-of-the-red-death_kokoro_bf_emma_representative_preflight_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-masque-of-the-red-death_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)

MasqueASRRepairError = CORE.GiftEmmaASRRepairError


def _configure_core() -> None:
    """Bind the reusable repair mechanics to this immutable Masque contract."""

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
        "missing_harken_normalized": False,
        "trailing_unexpected_you_deleted_or_normalized": False,
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


def _audio_hashes(samples: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    _configure_core()
    return CORE._audio_hashes(samples)


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
    repair["missing_harken_normalized"] = False
    repair["trailing_unexpected_you_deleted_or_normalized"] = False
    result["blockers_to_release"] = [
        (
            "MASQUE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
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
    except (MasqueASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
