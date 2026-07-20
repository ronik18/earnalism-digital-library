#!/usr/bin/env python3
"""Run one checksum-distinct ``af_sarah`` Cop representative pilot.

The adapter reuses the source-bound Cop executor while replacing the closed
``af_bella`` voice with a pinned ``af_sarah`` tensor.  It permits only four
canonical private passages and cannot run listening, full-title generation,
upload, publication, release mutation, browser speech, or public media output.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_cop_kokoro_private_audition.py"
SPEC = importlib.util.spec_from_file_location("earnalism_cop_af_bella_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load Cop representative executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


PROFILE = "cop-af-sarah-ironic-restraint-v1"
VOICE = "af_sarah"
VOICE_FILENAME = "voices/af_sarah.pt"
VOICE_SHA256 = "49bd364ea3be9eb3e9685e8f9a15448c4883112a7c0ff7ab139fa4088b08cef9"
PREVIOUS_VOICE = "af_bella"
PREVIOUS_VOICE_SHA256 = (
    "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
)
RANDOM_SEED = 2026072001
EXPECTED_ATTEMPT_FINGERPRINT = (
    "bb7c0f0967804c6d9bd4d715239b9e0741b47e7164c45f8e405e9ca1e6e9c553"
)
EXPECTED_PHONEME_HASHES = {
    "opening_winter": (
        "57acee3b38fb1dfdc2fbb6772b592f3c47eba23eb846899bc2fc433a2b4a062e"
    ),
    "waiter_dialogue": (
        "57fbc696b13594b5bd3d12bfe598946244d8e7cec67dcab62d114e7e7d228166"
    ),
    "church_reckoning": (
        "d5058fd1360f413806bba983071ed99c4a5ca08ca103374b0f85248c295d29c9"
    ),
    "ironic_ending": (
        "bea0903bdbc7f90f32fb68a77eb92e4526ccbce00679fabdfe7efe5b7320c885"
    ),
}
EXPECTED_EXISTING_AUDIO_HASHES = {
    "opening_winter": "bb297bbd8faf6645a1a7a47600c7f160f7638a3551c2c5c3c10df24d7c17f236",
    "waiter_dialogue": "93e51660309ee71eb4ed6aa2755e2cdd585da6c06a519355b577de455f8fcd37",
    "church_reckoning": "80a05603579ec39aabdf6f42740ba2b818783b75d3a192621b148f3ae5bb3d46",
    "ironic_ending": "b73b0891dcc2d6a5360e0ebb267e4fc345cae1b8e395bb67a694d308c472c825",
}
SOURCE_EQUIVALENCE_POLICY = {
    **BASE.SOURCE_EQUIVALENCE_POLICY,
    "waiter_dialogue": (
        *BASE.SOURCE_EQUIVALENCE_POLICY["waiter_dialogue"],
        {
            "pattern": r"\bcallus\b",
            "replacement": "callous",
            "reason": (
                "American fallback-free G2P gives source callous and decoded callus "
                "the same phoneme sequence"
            ),
        },
    ),
}
ASR_DIAGNOSTIC_SUMMARY = {
    "initial_prompted_run": {
        "status": "FAIL",
        "opening": "sealskin decoded as seal-skin",
        "waiter": "youse/use, callous/callus, and pitched/pitch",
        "church": "exact pass",
        "ending": "source spellings to-morrow, doin, and nothin decoded in modern form",
    },
    "allowed_new_equivalence": "callous/callus only; pitched/pitch and youse/use remain substantive",
}

DEFAULT_ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/artifacts"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-cop-and-the-anthem/"
    "f3ff3571-af-sarah-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_sarah_representative_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
AF_BELLA_EVIDENCE = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_representative_v1.json"
)
AF_BELLA_LISTENING_EVIDENCE = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_bella_listening_qa_v1.json"
)

_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute_private_representative
_BASE_ASR_REVERIFY = BASE.asr_reverify_existing


def exact_execute_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/sprint1_cop_af_sarah_private_audition.py "
        f"--execute --slug {BASE.ALLOWED_SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def af_sarah_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    fingerprint = str(payload["engine"]["attempt_fingerprint"])
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise BASE.CopKokoroPilotError(
            "Cop af_sarah fingerprint drift: "
            f"expected {EXPECTED_ATTEMPT_FINGERPRINT}, observed {fingerprint}"
        )
    observed_phonemes = {
        str(item["passage_id"]): str(item["phoneme_sha256"])
        for item in payload["g2p_preflight_evidence"]
    }
    if observed_phonemes != EXPECTED_PHONEME_HASHES:
        raise BASE.CopKokoroPilotError("Cop af_sarah fallback-free G2P hash drift")
    payload["schema"] = "earnalism.cop_kokoro_af_sarah_representative.v1"
    payload["go_no_go"] = "GO_ONE_PRIVATE_REPRESENTATIVE_EXECUTION_ONLY"
    payload["voice_selection"] = {
        "selected_voice": VOICE,
        "selected_voice_sha256": VOICE_SHA256,
        "previous_voice": PREVIOUS_VOICE,
        "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
        "voice_tensor_is_materially_different": VOICE_SHA256 != PREVIOUS_VOICE_SHA256,
        "selection_reason": (
            "One bounded zero-cost title experiment after the checksum-distinct voice "
            "was not previously attempted for this title. Prior af_sarah failures on "
            "other titles prevent any presumption of success."
        ),
    }
    payload["engine"]["selection_evidence"] = {
        "closed_title_voice": PREVIOUS_VOICE,
        "closed_title_voice_sha256": PREVIOUS_VOICE_SHA256,
        "closed_title_listening_scores": [8.7, 8.3, 9.5, 9.5],
        "closed_title_minimum_confidence": 0.85,
        "new_voice": VOICE,
        "new_voice_sha256": VOICE_SHA256,
        "new_voice_is_checksum_distinct": True,
        "prior_cross_title_af_sarah_objective_failures": [
            "the-necklace",
            "the-last-leaf",
        ],
        "success_not_assumed": True,
    }
    payload["engine"]["materially_distinct_from_prior"] = {
        "prior_provider_families": ["google_managed_tts", "open_weight_local_kokoro"],
        "prior_voices": ["en-GB-Studio-C", "en-GB-Chirp3-HD-Achird", PREVIOUS_VOICE],
        "current_family": "open_weight_local_kokoro",
        "current_voice": VOICE,
        "voice_tensor_checksum_distinct": True,
        "distinct": True,
    }
    payload["rights"].update(
        {
            "model_card_url": (
                "https://huggingface.co/hexgrad/Kokoro-82M/blob/"
                "f3ff3571791e39611d31c381e3a41a3af07b4987/README.md"
            ),
            "model_revision": BASE.MODEL_REVISION,
            "voice_asset_sha256": VOICE_SHA256,
        }
    )
    payload["next_stage_contract"] = {
        "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
        "exact_execute_command": exact_execute_command(Path(kwargs["asset_root"])),
        "scope": "four exact source-bound passages with af_sarah only",
        "asr_must_pass_before_listening_qa": True,
        "listening_qa_allowed_by_this_command": False,
        "full_title_generation_allowed": False,
        "upload_allowed": False,
        "publication_allowed": False,
        "release_gate_mutation_allowed": False,
    }
    return payload, passages, artifacts


def af_sarah_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    passed = code == 0 and (payload.get("asr") or {}).get("status") == "PASS"
    payload["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if passed
        else "NO_GO_REPRESENTATIVE_OBJECTIVE_GATE_FAILED"
    )
    payload["next_stage_contract"].update(
        {
            "status": (
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
                if passed
                else "REPRESENTATIVE_OBJECTIVE_FAIL_RETAINED_WAV_ASR_REPAIR_ONLY"
            ),
            "listening_qa_allowed_by_this_command": False,
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
        }
    )
    return code, payload


def af_sarah_asr_reverify(**kwargs: Any):
    code, payload = _BASE_ASR_REVERIFY(**kwargs)
    passed = code == 0 and (payload.get("asr") or {}).get("status") == "PASS"
    payload["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if passed
        else "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
    )
    payload["next_stage_contract"].update(
        {
            "status": (
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
                if passed
                else "REPRESENTATIVE_ASR_REPAIR_FAILED_CONFIGURATION_CLOSED"
            ),
            "listening_qa_allowed_by_this_command": False,
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
        }
    )
    return code, payload


def configure_profile() -> None:
    BASE.PROFILE_ID = PROFILE
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = VOICE_FILENAME
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = EXPECTED_EXISTING_AUDIO_HASHES
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.ASR_DIAGNOSTIC_SUMMARY = ASR_DIAGNOSTIC_SUMMARY
    BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (
                *BASE.NO_REPEAT_FILES,
                AF_BELLA_EVIDENCE,
                AF_BELLA_LISTENING_EVIDENCE,
                BASE.ROOT / DEFAULT_EVIDENCE,
            )
        )
    )
    BASE.preflight = af_sarah_preflight
    BASE.execute_private_representative = af_sarah_execute
    BASE.asr_reverify_existing = af_sarah_asr_reverify


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults = (
        ("--slug", BASE.ALLOWED_SLUG),
        ("--profile", PROFILE),
        ("--asset-root", BASE.ROOT),
        ("--artifact-dir", DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", DEFAULT_WHISPER_CACHE),
        ("--private-output-dir", DEFAULT_PRIVATE_OUTPUT),
        ("--output", DEFAULT_EVIDENCE),
        ("--paid-lock", DEFAULT_PAID_LOCK),
    )
    for option, value in defaults:
        if option not in options:
            args.extend((option, str(value)))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv or [])
    configure_profile()
    return int(BASE.main(expand_defaults(arguments)))


configure_profile()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
