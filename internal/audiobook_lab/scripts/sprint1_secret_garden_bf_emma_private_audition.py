#!/usr/bin/env python3
"""Run one distinct British-voice private pilot for The Secret Garden.

This wrapper reuses the exact 27-chapter source and four immutable passages
from the closed af_bella lane, while selecting the checksum-distinct bf_emma
voice, British fallback-free G2P, and slower literary pacing.  It cannot
listen, upload, publish, mutate release truth, or write public media.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = SCRIPT_DIR / "sprint1_secret_garden_af_bella_private_audition.py"
SPEC = importlib.util.spec_from_file_location(
    "secret_garden_af_bella_profile", PROFILE_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Secret Garden source profile: {PROFILE_PATH}")
PROFILE_BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE_BASE)


PROFILE = "secret-garden-bf-emma-yorkshire-v1"
VOICE = "bf_emma"
VOICE_FILENAME = "voices/bf_emma.pt"
VOICE_SHA256 = "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
PREVIOUS_VOICE = "af_bella"
PREVIOUS_VOICE_SHA256 = (
    "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
)
AF_BELLA_ATTEMPT_FINGERPRINT = (
    "85ea18462a896ab42f61cca055a8d6a24190077884c24fef9a80701e955d3a67"
)
KOKORO_LANG_CODE = "b"
G2P_BRITISH = True
SPEED = 0.94
RANDOM_SEED = 2026072004
PRONUNCIATION_OVERRIDES = {
    "Lennox": "lˈɛnəks",
    "Misselthwaite": "mˈɪzəlθwˌeɪt",
    "Martha": "mˈɑːθə",
    "tha": "ðˈa",
    "thysen": "ðaɪsˈɛn",
    "Medlock": "mˈɛdlɒk",
    "sayin": "sˈeɪɪn",
    "bein": "bˈiːɪn",
    "sobbed": "sˈɒbd",
}
EXPECTED_PHONEME_HASHES = {
    "opening_india": "d085c433df483325f0096d4f55703ef5d3833e40fe1ae82e1a9f6053d8dfb9a6",
    "yorkshire_dialogue": "c4b3752265a621d9c3f6049d8532ced98b0ea82522ee1a685b4baf296911b45e",
    "mary_colin_emotion": "947378e05d4bfcf6dcc6d8e8f25dc10857deeca2bed738aadfde1b6eb7540c9c",
    "ending_return": "8553cd9d035099c1926a82df73260ed67bc4658861c291f9e78ed565f9a3f04e",
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "32ae026cd0437f59d23df57ab90365ce3327ca7bb2fdc2e89eb95c9d24da9fc4"
)

DEFAULT_PRIVATE_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-secret-garden/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_OUTPUT = PROFILE_BASE.BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_representative_v1.json"
)
AF_BELLA_EVIDENCE = PROFILE_BASE.BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_representative_v1.json"
)
AF_BELLA_REPAIR_EVIDENCE = PROFILE_BASE.BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_asr_repair_v1.json"
)

_AF_PREFLIGHT = PROFILE_BASE.preflight
_AF_EXECUTE = PROFILE_BASE.execute


def bf_emma_preflight(**kwargs: Any):
    payload, passages, artifacts = _AF_PREFLIGHT(**kwargs)
    payload["schema"] = "earnalism.kokoro.secret_garden_bf_emma_representative.v1"
    payload["voice_selection"] = {
        "selected_voice": VOICE,
        "selected_voice_sha256": VOICE_SHA256,
        "previous_voice": PREVIOUS_VOICE,
        "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
        "voice_tensor_is_materially_different": VOICE_SHA256 != PREVIOUS_VOICE_SHA256,
        "locale": "British English",
        "kokoro_lang_code": KOKORO_LANG_CODE,
        "g2p_british": G2P_BRITISH,
        "selection_reason": (
            "A period-appropriate British voice and British G2P directly target the "
            "closed af_bella lane's Yorkshire-dialogue pronunciation failures."
        ),
    }
    payload["go_no_go"] = "GO_ONE_PRIVATE_REPRESENTATIVE_EXECUTION_ONLY"
    return payload, passages, artifacts


def bf_emma_execute(**kwargs: Any):
    code, payload = _AF_EXECUTE(**kwargs)
    payload["schema"] = "earnalism.kokoro.secret_garden_bf_emma_representative.v1"
    payload["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if code == 0
        else "NO_GO_REPRESENTATIVE_OBJECTIVE_FAILED"
    )
    return code, payload


def configure_profile() -> None:
    PROFILE_BASE.PROFILE = PROFILE
    PROFILE_BASE.VOICE = VOICE
    PROFILE_BASE.VOICE_SHA256 = VOICE_SHA256
    PROFILE_BASE.SPEED = SPEED
    PROFILE_BASE.RANDOM_SEED = RANDOM_SEED
    PROFILE_BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    PROFILE_BASE.EXPECTED_PHONEME_HASHES = EXPECTED_PHONEME_HASHES
    PROFILE_BASE.EXPECTED_ATTEMPT_FINGERPRINT = EXPECTED_ATTEMPT_FINGERPRINT
    PROFILE_BASE.DEFAULT_PRIVATE_DIR = DEFAULT_PRIVATE_DIR
    PROFILE_BASE.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    PROFILE_BASE.preflight = bf_emma_preflight
    PROFILE_BASE.execute = bf_emma_execute

    base = PROFILE_BASE.BASE
    base.PROFILE_ID = PROFILE
    base.VOICE = VOICE
    base.VOICE_FILENAME = VOICE_FILENAME
    base.VOICE_SHA256 = VOICE_SHA256
    base.KOKORO_LANG_CODE = KOKORO_LANG_CODE
    base.G2P_BRITISH = G2P_BRITISH
    base.SPEED = SPEED
    base.RANDOM_SEED = RANDOM_SEED
    base.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    PROFILE_BASE.configure_base()
    base.KOKORO_LANG_CODE = KOKORO_LANG_CODE
    base.G2P_BRITISH = G2P_BRITISH


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults = (
        ("--slug", PROFILE_BASE.SLUG),
        ("--profile", PROFILE),
        ("--asset-root", PROFILE_BASE.BASE.ROOT),
        ("--artifact-dir", PROFILE_BASE.DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", PROFILE_BASE.DEFAULT_WHISPER_CACHE),
        ("--private-output-dir", DEFAULT_PRIVATE_DIR),
        ("--output", DEFAULT_OUTPUT),
        ("--paid-lock", PROFILE_BASE.DEFAULT_PAID_LOCK),
    )
    for option, value in defaults:
        if option not in options:
            args.extend((option, str(value)))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_profile()
    args = list(argv or [])
    if "--asr-reverify-existing" in args:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_FAIL_CLOSED",
                    "error": (
                        "ASR reverify is disabled until this bf_emma candidate's "
                        "four audio hashes are code-reviewed and pinned"
                    ),
                },
                indent=2,
            )
        )
        return 2
    return int(PROFILE_BASE.BASE.main(expand_defaults(args)))


configure_profile()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
