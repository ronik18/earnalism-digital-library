#!/usr/bin/env python3
"""Prepare or run The Necklace's source-bound private Kokoro audition.

This title profile reuses the already-tested local Kokoro/Whisper executor but
replaces every title, manuscript, passage, voice, and pronunciation binding.
Preflight performs no synthesis or ASR.  ``--execute`` remains an explicit,
separate command and is limited to four private representative passages.
Neither mode uploads, publishes, changes release truth, or enables fallback
speech.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("earnalism_kokoro_title_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-necklace"
PROFILE = "necklace-af-sarah-ironic-restraint-v1"
TITLE = "The Necklace"
AUTHOR = "Guy de Maupassant"
LANGUAGE = "en"

ORIGIN_SOURCE_SHA256 = "bc5f461772b5583801472773e623c39ee14a218ae50b87715e24aa14b026549c"
SANITIZED_SOURCE_SHA256 = "ee0e443ea8e7cc6c5cbd9327e74f6bf3cdbf4aabcf92f345c79a07ab643a3ae3"
NORMALIZED_SOURCE_SHA256 = "981170428ff2cfc1233e14933153eb5b265ec20ccb21397986c210a053856a6d"
SOURCE_CHARACTERS = 16_094
NORMALIZED_SOURCE_CHARACTERS = 15_811
WORD_COUNT = 2_847

MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "af_sarah"
VOICE_SHA256 = "49bd364ea3be9eb3e9685e8f9a15448c4883112a7c0ff7ab139fa4088b08cef9"
PREVIOUS_KOKORO_VOICE = "af_bella"
PREVIOUS_KOKORO_VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

SPEED = 0.98
RANDOM_SEED = 2026071904

PASSAGE_SPECS = (
    {
        "passage_id": "opening_social_cadence",
        "start": "The girl was one of those pretty and charming young creatures who",
        "end": "of the people the equals of the very greatest ladies.",
        "characters": 748,
        "sha256": "5ec553147d58c23d446c329f2b7e81a414f053b8b73959db378382219db48971",
        "risk": "long literary sentences, social irony, and restrained opening cadence",
    },
    {
        "passage_id": "invitation_dialogue",
        "start": "She looked at him with an irritated glance and said impatiently:",
        "end": "Give your card to some colleague whose wife is better equipped than I am.\u201d",
        "characters": 671,
        "sha256": "b17eb95b67e2ce4bd0fb2a144e4ddf306392554d6f9cc173a95bdca904ca83e6",
        "risk": "speaker transitions, repeated questions, tears, and controlled emotional contrast",
    },
    {
        "passage_id": "necklace_loss_panic",
        "start": "She removed her wraps before the glass",
        "end": "\u201cWhat!--how? Impossible!\u201d",
        "characters": 399,
        "sha256": "6bc79554d60cdc0db280a123977e7eb535e76b0406adaa6b5f983ddf152d6cc6",
        "risk": "panic, interrupted speech, em-dash-like punctuation, and the name Forestier",
    },
    {
        "passage_id": "final_ironic_reveal",
        "start": "\u201cI brought you back another exactly like it.",
        "end": "only five hundred francs!\u201d",
        "characters": 569,
        "sha256": "87258569e9bfc0f02d132722a11f9e843cd9489b415f78f034bf7437d223a887",
        "risk": "French names, dialogue turns, and the story's quiet-to-shocking final reveal",
    },
)
PASSAGE_CHARACTERS = 2_387

PRIOR_ATTEMPTS = (
    {
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "speaking_rate": 0.94,
        "fingerprint": "2fda4f2789d86388",
        "scores": [8.4, 8.4, 7.0, 9.4],
        "fatal_flags": ["mechanical_cadence_detected", "robotic_texture_detected"],
        "status": "BLOCKED_LISTENING_QA",
    },
    {
        "provider": "google",
        "voice": "en-GB-Chirp3-HD-Achird",
        "speaking_rate": 0.9,
        "fingerprint": "8791b401758f5e9a",
        "scores": [8.6, 8.5, 9.4, 9.5],
        "fatal_flags": [],
        "status": "BLOCKED_LISTENING_QA",
    },
)

PRONUNCIATION_OVERRIDES = {
    "Mathilde": "m\u0251\u02d0t\u02c8i\u02d0ld",
    "Loisel": "lw\u0251\u02d0z\u02c8\u025bl",
    "Forestier": "f\u0254\u0279\u025bstj\u02c8e\u026a",
    "Madame": "m\u0259d\u02c8\u0251m",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical spellings: Mathilde Loisel; Madame Forestier; Guy de Maupassant; "
    "Ministry of Public Instruction. Preserve every source word in order."
)
ASR_PROMPT_POLICY = {
    "opening_social_cadence": "canonical_vocabulary_prompt",
    "invitation_dialogue": "canonical_vocabulary_prompt",
    "necklace_loss_panic": "canonical_vocabulary_prompt",
    "final_ironic_reveal": "canonical_vocabulary_prompt",
}
SOURCE_EQUIVALENCE_POLICY = {item["passage_id"]: () for item in PASSAGE_SPECS}

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
    "internal/audiobook_lab/private_runs/kokoro/the-necklace/"
    "f3ff3571-af-sarah-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-necklace_kokoro_af_sarah_representative_preflight_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, list[dict[str, Any]]]:
    """Return four exact passages only when catalog and manuscript truth match."""

    if slug != SLUG:
        raise BASE.KokoroTitlePilotError(
            f"slug is not allowed by {PROFILE}: {slug}; only {SLUG} is permitted"
        )
    publication = asset_root / "data/controlled_publications" / SLUG
    book = BASE.read_json(publication / "public_book.json")
    expected_book = {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "readerStatus": "reader_ready",
        "publicationStatus": "live",
        "audiobook_enabled": False,
        "audio_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }
    for key, expected in expected_book.items():
        if book.get(key) != expected:
            raise BASE.KokoroTitlePilotError(
                f"controlled catalog truth changed for {key}: expected {expected!r}, "
                f"observed {book.get(key)!r}"
            )
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = BASE.read_json(chapter_path)
    expected_chapter = {
        "id": "chapter-001",
        "bookSlug": SLUG,
        "language": LANGUAGE,
        "processing_status": "ready",
        "processing_warnings": [],
        "sourceSha256": ORIGIN_SOURCE_SHA256,
        "sanitizedSha256": SANITIZED_SOURCE_SHA256,
        "word_count": WORD_COUNT,
    }
    for key, expected in expected_chapter.items():
        if chapter.get(key) != expected:
            raise BASE.KokoroTitlePilotError(
                f"controlled chapter truth changed for {key}: expected {expected!r}, "
                f"observed {chapter.get(key)!r}"
            )
    manuscript = chapter.get("content")
    if not isinstance(manuscript, str):
        raise BASE.KokoroTitlePilotError("controlled manuscript is missing")
    if len(manuscript) != SOURCE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("controlled source character count changed")
    if BASE.sha256_text(manuscript) != SANITIZED_SOURCE_SHA256:
        raise BASE.KokoroTitlePilotError("controlled source bytes changed")
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    if len(normalized) != NORMALIZED_SOURCE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("normalized source character count changed")
    if BASE.sha256_text(normalized) != NORMALIZED_SOURCE_SHA256:
        raise BASE.KokoroTitlePilotError("normalized source hash changed")

    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start = normalized.find(str(spec["start"]))
        end_start = normalized.find(str(spec["end"]), start)
        if start < 0 or end_start < 0:
            raise BASE.KokoroTitlePilotError(
                f"canonical passage markers changed: {spec['passage_id']}"
            )
        end = end_start + len(str(spec["end"]))
        text = normalized[start:end]
        if len(text) != spec["characters"] or BASE.sha256_text(text) != spec["sha256"]:
            raise BASE.KokoroTitlePilotError(
                f"canonical passage binding changed: {spec['passage_id']}"
            )
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("bounded passage character total changed")
    return chapter_path, passages


_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute


def _exact_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/sprint1_necklace_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def necklace_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    risks = {str(item["passage_id"]): str(item["risk"]) for item in PASSAGE_SPECS}
    for passage in payload["source"]["passages"]:
        passage["risk"] = risks[str(passage["passage_id"])]
    payload.update(
        {
            "schema": "earnalism.kokoro.necklace_private_representative.v1",
            "source": {
                **payload["source"],
                "origin_source_sha256": ORIGIN_SOURCE_SHA256,
                "sanitized_source_sha256": SANITIZED_SOURCE_SHA256,
                "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
                "word_count": WORD_COUNT,
            },
            "prior_attempts": list(PRIOR_ATTEMPTS),
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "previous_campaign_kokoro_voice": PREVIOUS_KOKORO_VOICE,
                "previous_campaign_kokoro_voice_sha256": PREVIOUS_KOKORO_VOICE_SHA256,
                "voice_tensor_is_materially_different": VOICE_SHA256
                != PREVIOUS_KOKORO_VOICE_SHA256,
                "selected_asset_is_locally_installed_and_hash_verified": True,
                "selected_asset_source_repo": BASE.MODEL_REPO,
                "selected_asset_source_revision": MODEL_REVISION,
            },
            "rights": {
                "model_and_voicepack_license": "Apache-2.0",
                "private_audition_allowed": True,
                "title_scoped_production_risk_acceptance_bound": False,
                "production_release_approved": False,
                "public_disclosure_required_if_later_approved": "AI voice",
            },
            "next_stage_contract": {
                "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
                "exact_execute_command": _exact_command(Path(kwargs["asset_root"])),
                "scope": "four exact source-bound passages only",
                "g2p_fallback_enabled": False,
                "browser_or_system_speech_fallback": False,
                "local_synthesis_provider_calls": 0,
                "asr_must_pass_before_listening_qa": True,
                "full_title_generation_allowed": False,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
                "fail_closed_on": [
                    "catalog_or_source_hash_change",
                    "passage_hash_change",
                    "artifact_or_runtime_hash_change",
                    "unresolved_g2p_token_with_fallback_disabled",
                    "repeated_attempt_fingerprint",
                    "non_private_output_path",
                    "asr_source_score_below_9.7",
                    "missing_first_or_last_words",
                    "missing_duplicated_reordered_or_unexpected_content",
                ],
            },
        }
    )
    payload["engine"]["known_failed_fingerprint_count"] = len(PRIOR_ATTEMPTS)
    payload["blockers_to_release"] = [
        "REPRESENTATIVE_AUDIO_NOT_GENERATED",
        "REPRESENTATIVE_ASR_NOT_RUN",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "NECKLACE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    return payload, passages, artifacts


def necklace_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["blockers_to_release"] = [
        blocker.replace(
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "NECKLACE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        )
        for blocker in payload["blockers_to_release"]
    ]
    return code, payload


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = SANITIZED_SOURCE_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(str(item["sha256"]) for item in PASSAGE_SPECS)
    BASE.EXPECTED_PASSAGE_CHARACTERS = PASSAGE_CHARACTERS
    BASE.MODEL_REVISION = MODEL_REVISION
    BASE.MODEL_SHA256 = MODEL_SHA256
    BASE.CONFIG_SHA256 = CONFIG_SHA256
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = f"voices/{VOICE}.pt"
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.WHISPER_SHA256 = WHISPER_SHA256
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = {}
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset(
        str(item["fingerprint"]) for item in PRIOR_ATTEMPTS
    )
    BASE.controlled_source = controlled_source
    BASE.preflight = necklace_preflight
    BASE.execute = necklace_execute


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults: tuple[tuple[str, Path], ...] = (
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
    if "--slug" not in options:
        args.extend(("--slug", SLUG))
    if "--profile" not in options:
        args.extend(("--profile", PROFILE))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_base()
    return int(BASE.main(expand_defaults(argv)))


configure_base()


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
