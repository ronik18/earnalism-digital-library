#!/usr/bin/env python3
"""Run one distinct British-voice private pilot for The Monkey's Paw.

This profile reuses the hash-bound Monkey's Paw source and four risk passages,
but replaces the closed ``af_bella`` lane with the checksum-distinct British
``bf_emma`` voice and British fallback-free G2P.  It is representative-only:
there is no listening, full-title generation, upload, publication, release
mutation, browser speech, or public media path in this command.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = SCRIPT_DIR / "sprint1_monkeys_paw_kokoro_private_audition.py"
SPEC = importlib.util.spec_from_file_location(
    "earnalism_monkeys_paw_af_profile", PROFILE_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load Monkey's Paw profile: {PROFILE_PATH}")
PROFILE_BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE_BASE)


PROFILE = "monkeys-paw-bf-emma-gothic-v1"
VOICE = "bf_emma"
VOICE_SHA256 = "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
PREVIOUS_VOICE = "af_bella"
PREVIOUS_VOICE_SHA256 = (
    "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
)
KOKORO_LANG_CODE = "b"
G2P_BRITISH = True
SPEED = 0.94
RANDOM_SEED = 2026072003
PRONUNCIATION_OVERRIDES = {
    "Herbert": "hˈɜːbət",
    "Meggins": "mˈɛɡɪnz",
    "jarred": "ʤˈɑːd",
    "tapped": "tˈæpt",
}
PHONEME_HASHES = {
    "opening_domestic_tension": (
        "a88b072d35edc4809432f0dee996ab30cfdf561a4320c8b2cff4582cff759fdc"
    ),
    "paw_warning_and_fate": (
        "11cfd6261a4d7ffc1a1179e0b392b7f915302a4dda9344d044ddc29d128a4dae"
    ),
    "factory_news_and_grief": (
        "4c0282da33f4c6eec6e0e3c15313f36599921ffc75dde3dcc95bd11a6e197aef"
    ),
    "final_knocking_and_third_wish": (
        "8aa37539eec3924e4010893cff8e2a57a85bc5b8bb169087315cfe8c186f1b1e"
    ),
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "e62afa333e08cb3c4df2d11e529c95dc661465f337537f02dbd7e054c1e405a4"
)

DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-monkeys-paw/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_representative_v1.json"
)
AF_BELLA_EVIDENCE = PROFILE_BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_af_bella_representative_v1.json"
)
AF_BELLA_REPAIR_EVIDENCE = PROFILE_BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_af_bella_asr_repair_v1.json"
)

_BASE_PREFLIGHT = PROFILE_BASE.preflight


def exact_execute_command(asset_root: Path) -> str:
    """Return the sole command allowed to synthesize this exact profile."""

    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/"
        "sprint1_monkeys_paw_bf_emma_private_audition.py "
        f"--execute --slug {PROFILE_BASE.SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} "
        f"--artifact-dir {PROFILE_BASE.DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {PROFILE_BASE.DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE}"
    )


def bf_emma_preflight(**kwargs: Any):
    """Decorate the common contract with the distinct British voice evidence."""

    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    payload.update(
        {
            "schema": "earnalism.kokoro.monkeys_paw_bf_emma_private_audition.v1",
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "previous_voice": PREVIOUS_VOICE,
                "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
                "voice_tensor_is_materially_different": (
                    VOICE_SHA256 != PREVIOUS_VOICE_SHA256
                ),
                "locale": "British English",
                "kokoro_lang_code": KOKORO_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "selection_reason": (
                    "The restrained British timbre is title-suitable for period Gothic "
                    "suspense and is a checksum-distinct, previously untested voice for "
                    "this title."
                ),
            },
            "go_no_go": "GO_ONE_PRIVATE_REPRESENTATIVE_EXECUTION_ONLY",
        }
    )
    payload["engine"].update(
        {
            "voice_language": "British English",
            "kokoro_lang_code": KOKORO_LANG_CODE,
            "g2p_british": G2P_BRITISH,
            "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
        }
    )
    payload["g2p_audit"].update(
        {
            "lang_code": KOKORO_LANG_CODE,
            "british": G2P_BRITISH,
            "fallback": None,
        }
    )
    payload["next_stage_contract"].update(
        {
            "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
            "exact_execute_command": exact_execute_command(Path(kwargs["asset_root"])),
            "scope": "these four exact source-bound passages with bf_emma only",
            "asr_must_pass_before_listening_qa": True,
            "listening_qa_allowed_by_this_command": False,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
        }
    )
    return payload, passages, artifacts


def configure_profile() -> None:
    """Bind every mutable base constant to this immutable new fingerprint."""

    PROFILE_BASE.PROFILE = PROFILE
    PROFILE_BASE.VOICE = VOICE
    PROFILE_BASE.VOICE_SHA256 = VOICE_SHA256
    PROFILE_BASE.SPEED = SPEED
    PROFILE_BASE.RANDOM_SEED = RANDOM_SEED
    PROFILE_BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    PROFILE_BASE.AMERICAN_LANG_CODE = KOKORO_LANG_CODE
    PROFILE_BASE.AMERICAN_G2P = G2P_BRITISH
    PROFILE_BASE.PHONEME_HASHES = PHONEME_HASHES
    PROFILE_BASE.EXPECTED_ATTEMPT_FINGERPRINT = EXPECTED_ATTEMPT_FINGERPRINT
    PROFILE_BASE.DEFAULT_PRIVATE_OUTPUT = DEFAULT_PRIVATE_OUTPUT
    PROFILE_BASE.DEFAULT_EVIDENCE = DEFAULT_EVIDENCE
    PROFILE_BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (
                *PROFILE_BASE.NO_REPEAT_FILES,
                AF_BELLA_EVIDENCE,
                AF_BELLA_REPAIR_EVIDENCE,
            )
        )
    )
    PROFILE_BASE.configure_base()
    PROFILE_BASE.BASE.KOKORO_LANG_CODE = KOKORO_LANG_CODE
    PROFILE_BASE.BASE.G2P_BRITISH = G2P_BRITISH
    PROFILE_BASE.preflight = bf_emma_preflight


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults = (
        ("--asset-root", PROFILE_BASE.ROOT),
        ("--artifact-dir", PROFILE_BASE.DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", PROFILE_BASE.DEFAULT_WHISPER_CACHE),
        ("--private-output-dir", DEFAULT_PRIVATE_OUTPUT),
        ("--output", DEFAULT_EVIDENCE),
    )
    for option, value in defaults:
        if option not in options:
            args.extend((option, str(value)))
    if "--slug" not in options:
        args.extend(("--slug", PROFILE_BASE.SLUG))
    if "--profile" not in options:
        args.extend(("--profile", PROFILE))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_profile()
    return int(PROFILE_BASE.main(expand_defaults(argv)))


configure_profile()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
