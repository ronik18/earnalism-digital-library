#!/usr/bin/env python3
"""Run one ASR-only decoder bakeoff over retained Secret Garden bf_emma WAVs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPAIR_BASE = _load(
    "secret_garden_af_repair_base",
    SCRIPT_DIR / "sprint1_secret_garden_kokoro_asr_repair.py",
)
BF_PROFILE = _load(
    "secret_garden_bf_profile",
    SCRIPT_DIR / "sprint1_secret_garden_bf_emma_private_audition.py",
)
PROFILE = BF_PROFILE.PROFILE_BASE
CORE = REPAIR_BASE.CORE
ROOT = PROFILE.BASE.ROOT

SCHEMA = "earnalism.kokoro.secret_garden_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.secret_garden_bf_emma_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "30dd7e579cbbeb935490257e8d8697708f3da65a4bfe05b03ba390b922c6b035"
)
EXPECTED_ATTEMPT_FINGERPRINT = BF_PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "e0259b7636a31717714e0302c34c43fc385548f0695ff5f53688b3bcd1522bcc"
)
EXPECTED_PAID_LOCK_SHA256 = REPAIR_BASE.EXPECTED_PAID_LOCK_SHA256
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_india": "747e4094fe4e8da3f3cb78e02ecf9634da75ee4d78009c6f1cb2d759a6683d9a",
    "yorkshire_dialogue": "00c783a1667f730995abba9960b146ae583d2f7111539f49a795d1ac7459035a",
    "mary_colin_emotion": "9438007d2799b53b040b69680eff0ec1710f31f6aeccd71d918fb34bc81c9479",
    "ending_return": "1bbdb263aefad1473fc3f44698fbc70a668f7b25af455894220a093e071b6d6b",
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_india": {
        "source_text_sha256": "9921329ed99b36731d1ca45e6f209dd44e3fc22376009f75d3e4246d94daf341",
        "audio_sha256": "6dacd2b2a750066f62ec7e5b522799e04436d338f3fdcc2afaa5be9dba7c61fa",
        "size_bytes": 2_144_444,
        "duration_seconds": 44.675,
    },
    "yorkshire_dialogue": {
        "source_text_sha256": "be1275f2818dab21ed28678a84a6a4029a41166bc74fe7b2caedbc58290285ad",
        "audio_sha256": "856a8877249d04541fd26f522f68d414982f0aed144405465574eb7a771bd3e3",
        "size_bytes": 2_223_644,
        "duration_seconds": 46.325,
    },
    "mary_colin_emotion": {
        "source_text_sha256": "ff3b5af98b532ad81f19df606c456aea0580519c9683d5a81b48de755a4023dd",
        "audio_sha256": "9922686e1a8f551c449ed103ed7f9a8e78a431681c24ee00fc526ebbef9dcdb7",
        "size_bytes": 2_365_244,
        "duration_seconds": 49.275,
    },
    "ending_return": {
        "source_text_sha256": "bdd08b81e13c0ec9c4e74854e1c8eb939963ba13c76187c258b39488193cb6cc",
        "audio_sha256": "4e16d8bcaf79e9d2edcd839a74d262fd485e987627d91cc1fdc2c56c62879d51",
        "size_bytes": 1_238_444,
        "duration_seconds": 25.8,
    },
}
DECODING_ARMS = REPAIR_BASE.DECODING_ARMS
EQUIVALENCE_POLICY = REPAIR_BASE.EQUIVALENCE_POLICY
FORBIDDEN_NORMALIZATIONS = REPAIR_BASE.FORBIDDEN_NORMALIZATIONS
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
EXPECTED_REPAIR_FINGERPRINT = (
    "a3e8fc338d235164ceea0c703856a09de42655e28611dd72acac96e53d2ecc1e"
)

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
    ROOT
    / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_release_gate_evidence.json",
    REPAIR_BASE.DEFAULT_OUTPUT,
)

SecretGardenBfASRRepairError = CORE.GiftEmmaASRRepairError


def _configure_core() -> None:
    bindings = {
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
        "EXPECTED_REPAIR_FINGERPRINT": EXPECTED_REPAIR_FINGERPRINT,
    }
    for name, value in bindings.items():
        setattr(REPAIR_BASE, name, value)
    REPAIR_BASE._configure_core()


def repair_fingerprint() -> str:
    _configure_core()
    observed = CORE.repair_fingerprint()
    if (
        EXPECTED_REPAIR_FINGERPRINT != "PENDING_REBIND"
        and observed != EXPECTED_REPAIR_FINGERPRINT
    ):
        raise SecretGardenBfASRRepairError(
            "Secret Garden bf_emma ASR repair contract changed without rebind"
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
    return REPAIR_BASE.execute(
        input_path,
        output_path,
        whisper_cache,
        paid_lock,
        dry_run=dry_run,
        model_loader=model_loader,
        decoder=decoder,
    )


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
    except (SecretGardenBfASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
