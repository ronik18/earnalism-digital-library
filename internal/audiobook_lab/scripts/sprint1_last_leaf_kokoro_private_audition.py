#!/usr/bin/env python3
"""Prepare The Last Leaf's source-bound private Kokoro representative pilot.

The default ``--preflight`` path validates canonical catalog/manuscript truth,
four risk passages, locally pinned Kokoro/Whisper assets, audio-hidden release
truth, and no-repeat history without synthesizing or transcribing anything.
``--execute`` is retained only as the explicit next-stage contract: it remains
private, four-passage bounded, G2P-fallback-free, and unable to upload,
publish, or mutate release truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("earnalism_kokoro_title_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-last-leaf"
PROFILE = "last-leaf-af-sarah-compassionate-restraint-v1"
TITLE = "The Last Leaf"
AUTHOR = "O. Henry"
LANGUAGE = "en"

ORIGIN_SOURCE_SHA256 = "3b86fb4d8aae47c9471240ba708f681dc16aec5b34d97976faa9a642339290ba"
SANITIZED_SOURCE_SHA256 = "e3a825f58d8a086967586988d7eeaf902fbb415b53cd164340d935f98d7645f7"
NORMALIZED_SOURCE_SHA256 = "203c0f52039399e2a49dbc836f3d77374625106e61e5926a6d97224bf0cb2fd6"
SOURCE_CHARACTERS = 12_935
NORMALIZED_SOURCE_CHARACTERS = 12_727
WORD_COUNT = 2_402

MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "af_sarah"
VOICE_SHA256 = "49bd364ea3be9eb3e9685e8f9a15448c4883112a7c0ff7ab139fa4088b08cef9"
PREVIOUS_KOKORO_VOICE = "af_bella"
PREVIOUS_KOKORO_VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

SPEED = 0.98
RANDOM_SEED = 2026071905

PASSAGE_SPECS = (
    {
        "passage_id": "opening_literary_setting",
        "start": "In a little district west of Washington Square",
        "end": "and became a “colony.”",
        "characters": 720,
        "sha256": "05c55ee1edd72ef0609c782226e4537ff35051b2ea7ea81e0eedfd2901d02dd5",
        "risk": "long literary sentences, Greenwich Village names, and restrained irony",
    },
    {
        "passage_id": "johnsy_leaf_dialogue",
        "start": "“Six,” said Johnsy, in almost a whisper.",
        "end": "I’ve known that for three days. Didn’t the doctor tell you?”",
        "characters": 386,
        "sha256": "8ece41198a202de474bef1a33218949f8bd72fd18413f4af140548db7026b775",
        "risk": "quiet dialogue turns, vulnerability, contractions, and emotional restraint",
    },
    {
        "passage_id": "behrman_dialect_emotion",
        "start": "Old Behrman, with his red eyes plainly streaming,",
        "end": "Ach, dot poor lettle Miss Johnsy.”",
        "characters": 432,
        "sha256": "3ee0d5877dcd681e530ea3dc56fe0c7b11614d3bec736c9ca485799c897fafc1",
        "risk": "source-authentic dialect, exclamations, character contrast, and proper names",
    },
    {
        "passage_id": "final_masterpiece_reveal",
        "start": "“I have something to tell you, white mouse,”",
        "end": "the night that the last leaf fell.”",
        "characters": 764,
        "sha256": "9b92d5b089d00a5896d243c6c6ac4c8e5ad645a76f820131df9476f582e1bc00",
        "risk": "grief, sustained revelation, em-dash pause, and compassionate closing cadence",
    },
)
PASSAGE_CHARACTERS = 2_302

PRIOR_ATTEMPTS = (
    {
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "speaking_rate": 0.94,
        "fingerprint": "c0f5f836abe9976e",
        "scores": [8.4, 8.4, 9.4, 8.3],
        "fatal_flags": [],
        "status": "BLOCKED_LISTENING_QA",
    },
    {
        "provider": "google",
        "voice": "en-GB-Chirp3-HD-Achird",
        "speaking_rate": 0.9,
        "fingerprint": "313f9bf5249bc7b5",
        "scores": [9.4, 9.4, 8.4, 9.4],
        "fatal_flags": [],
        "status": "BLOCKED_LISTENING_QA",
    },
    {
        "provider": "kokoro",
        "voice": VOICE,
        "speaking_rate": SPEED,
        "fingerprint": "b62c996d97def9e3f805eba13be2aa2b29ebf03858200657b2c959676b9d4935",
        "scores": [],
        "fatal_flags": [],
        "status": "BLOCKED_UNRESOLVED_G2P_NO_AUDIO_GENERATED",
    },
)

PRONUNCIATION_OVERRIDES = {
    "Johnsy": "dʒˈɑnsi",
    "Joanna": "dʒoʊˈænə",
    "Behrman": "bˈɛɹmən",
    "Greenwich": "ɡɹˈɛnɪtʃ",
    "Sudie": "sˈudi",
    # O. Henry deliberately spells Behrman's German-accented dialogue this
    # way.  Bind only those exact source tokens to supported Kokoro phonemes;
    # never rewrite the canonical manuscript or enable a fallback G2P engine.
    "Vass": "vˈAs",
    "Vy": "vˌI",
    "bose": "bˈOz",
    "de": "də",
    "der": "dɛɹ",
    "dere": "dˈɛɹ",
    "dey": "dA",
    "haf": "hˈæf",
    "lettle": "lˈɛTᵊl",
    "mit": "mˈɪt",
    "prain": "pɹˈAn",
    "pusiness": "pˈɪznəs",
}
SOURCE_DIALECT_PRONUNCIATION_BINDINGS = {
    token: PRONUNCIATION_OVERRIDES[token]
    for token in (
        "Vass",
        "Vy",
        "bose",
        "de",
        "der",
        "dere",
        "dey",
        "haf",
        "lettle",
        "mit",
        "prain",
        "pusiness",
    )
}
ASR_VOCABULARY_PROMPT = (
    "Canonical spellings: O. Henry; Sue; Johnsy; Joanna; Behrman; Sudie; "
    "Greenwich Village; Washington Square. Preserve the source dialect "
    "spellings Vass, Vy, bose, de, der, dere, dey, haf, lettle, mit, prain, "
    "pusiness, and dot."
)
ASR_PROMPT_POLICY = {
    "opening_literary_setting": "canonical_vocabulary_prompt",
    "johnsy_leaf_dialogue": "canonical_vocabulary_prompt",
    "behrman_dialect_emotion": "canonical_vocabulary_prompt",
    "final_masterpiece_reveal": "canonical_vocabulary_prompt",
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
    "internal/audiobook_lab/private_runs/kokoro/the-last-leaf/"
    "f3ff3571-af-sarah-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-last-leaf_kokoro_af_sarah_representative_preflight_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
PROVIDER_FAILURE_REGISTRY = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json"
)
CANONICAL_RELEASE_EVIDENCE = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-last-leaf_release_gate_evidence.json"
)


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, list[dict[str, Any]]]:
    """Return the four passages only when exact catalog/source truth holds."""

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

    approval = BASE.read_json(publication / "approval_evidence.json")
    if approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_NOT_APPROVED":
        raise BASE.KokoroTitlePilotError("controlled audio-hidden approval truth changed")
    if approval.get("audiobook_enabled") is not False:
        raise BASE.KokoroTitlePilotError("controlled audiobook approval truth changed")

    chapter_path = publication / "chapters/chapter-001.json"
    chapter = BASE.read_json(chapter_path)
    expected_chapter = {
        "id": "chapter-001",
        "bookSlug": SLUG,
        "title": TITLE,
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
        "internal/audiobook_lab/scripts/sprint1_last_leaf_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def last_leaf_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    risks = {str(item["passage_id"]): str(item["risk"]) for item in PASSAGE_SPECS}
    for passage in payload["source"]["passages"]:
        passage["risk"] = risks[str(passage["passage_id"])]
    payload.update(
        {
            "schema": "earnalism.kokoro.last_leaf_private_representative.v1",
            "source": {
                **payload["source"],
                "origin_source_sha256": ORIGIN_SOURCE_SHA256,
                "sanitized_source_sha256": SANITIZED_SOURCE_SHA256,
                "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
                "word_count": WORD_COUNT,
            },
            "catalog_truth": {
                "reader_status": "reader_ready",
                "publication_status": "live",
                "audiobook_enabled": False,
                "audio_enabled": False,
                "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            },
            "prior_attempts": list(PRIOR_ATTEMPTS),
            "no_repeat_history": {
                "inspected_paths": [
                    str(path)
                    for path in BASE.NO_REPEAT_FILES
                    if path.is_file()
                ],
                "prior_fingerprints": [
                    str(item["fingerprint"]) for item in PRIOR_ATTEMPTS
                ],
                "exact_current_fingerprint_found": False,
                "fail_closed_on_completed_fingerprint": True,
            },
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "voice_audit_recommendation": "af_sarah",
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
                "execution_performed_by_this_preflight": False,
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
        "LAST_LEAF_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    return payload, passages, artifacts


def last_leaf_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["blockers_to_release"] = [
        blocker.replace(
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "LAST_LEAF_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
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
    BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (*BASE.NO_REPEAT_FILES, PROVIDER_FAILURE_REGISTRY, CANONICAL_RELEASE_EVIDENCE)
        )
    )
    BASE.controlled_source = controlled_source
    BASE.preflight = last_leaf_preflight
    BASE.execute = last_leaf_execute


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
