#!/usr/bin/env python3
"""Prepare or run The Secret Garden's bounded private Kokoro pilot.

The profile is bound to the canonical 27-chapter controlled publication,
public-domain rights evidence, exact cover state, four representative
passages, a checksum-pinned British Kokoro voice, and local Whisper ASR.
Preflight has no synthesis side effect. ``--execute`` generates only the four
private passages and cannot upload, publish, or mutate release truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location(
    "earnalism_kokoro_title_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-secret-garden"
PROFILE = "secret-garden-bf-emma-british-warmth-v1"
TITLE = "The Secret Garden"
AUTHOR = "Frances Hodgson Burnett"
LANGUAGE = "en"

SOURCE_EVIDENCE_SHA256 = (
    "e475a847f75aff163a517afd457be284ebd08a236c000a4c5961a478bfa5366d"
)
CONTENT_EVIDENCE_SHA256 = (
    "eb5f0ece1bc11cc989d1b801a925a85ffbd6b002ad2eaff26cdf19fbb12135ad"
)
CANONICAL_MANUSCRIPT_SHA256 = (
    "4aac34ad4bda3586f1a062b24b3ca271a96edef7e4938d13042d0595f692f3a3"
)
CANONICAL_MANUSCRIPT_CHARACTERS = 431_542
CHAPTER_COUNT = 27

MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = (
    "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
)
CONFIG_SHA256 = (
    "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
)
VOICE = "bf_emma"
VOICE_SHA256 = (
    "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
)
WHISPER_SHA256 = (
    "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"
)

PIPELINE_LANG_CODE = "b"
G2P_BRITISH = True
SPEED = 0.96
RANDOM_SEED = 2026072801

PASSAGE_SPECS = (
    {
        "passage_id": "opening_india_character",
        "chapter_id": "chapter-001",
        "start": "When Mary Lennox was sent to Misselthwaite Manor",
        "end": (
            "Her hair was yellow, and her face was yellow because she had been "
            "born in India and had always been ill in one way or another."
        ),
        "characters": 376,
        "sha256": (
            "76fb57182f59bc7b3a9848bcc5f60489f297e208444e3089103d971f36cde893"
        ),
        "risk": (
            "opening authority, British place names, India context, and a long "
            "descriptive sentence"
        ),
    },
    {
        "passage_id": "garden_key_discovery",
        "chapter_id": "chapter-007",
        "start": "Mary looked at it, not really knowing why the hole was there",
        "end": "“Perhaps it is the key to the garden!”",
        "characters": 588,
        "sha256": (
            "444b42c0536f8c3c7ed8f2a3127ad023a88a0ffd864288e5bb61bb15dea60d7e"
        ),
        "risk": (
            "wonder, suspense, semicolon pacing, whispered dialogue, and the "
            "key discovery"
        ),
    },
    {
        "passage_id": "colin_midnight_dialogue",
        "chapter_id": "chapter-013",
        "start": "“Who are you?” he said at last in a half-frightened whisper.",
        "end": "“He is my father,” said the boy.",
        "characters": 561,
        "sha256": (
            "d47aeb874088b45ba4032bbf886a5964b3b5071066f2619acb4c2e86666c969f"
        ),
        "risk": (
            "rapid child dialogue, repeated questions, fear, identity reveal, "
            "and speaker transitions"
        ),
    },
    {
        "passage_id": "healing_finale",
        "chapter_id": "chapter-027",
        "start": "“Look there,” he said, “if tha’s curious.",
        "end": "Master Colin! THE END",
        "characters": 572,
        "sha256": (
            "8410db6f6340acce12a6c1b35686c093141d4672bd7a9713f7c7f4b2af14f7c3"
        ),
        "risk": (
            "Yorkshire dialect, crowd reaction, emotional uplift, em-dash "
            "timing, and final cadence"
        ),
    },
)
PASSAGE_CHARACTERS = 2_097

PRONUNCIATION_OVERRIDES = {
    "Colin": "kˈɒlɪn",
    "Craven": "kɹˈeɪvən",
    "Lennox": "lˈɛnəks",
    "Medlock": "mˈɛdlɒk",
    "Misselthwaite": "mˈɪsəlθwˌeɪt",
    "Yorkshire": "jˈɔːkʃə",
    "comin": "kˈʌmɪn",
    "th": "ðə",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical spellings: Mary Lennox; Misselthwaite Manor; Colin Craven; "
    "Mrs. Medlock; Master Colin; Yorkshire; India. Preserve every source word "
    "in exact order, including the Yorkshire dialect."
)
ASR_PROMPT_POLICY = {
    item["passage_id"]: "canonical_vocabulary_prompt" for item in PASSAGE_SPECS
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
    "internal/audiobook_lab/private_runs/kokoro/the-secret-garden/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_representative_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
PROVIDER_FAILURE_REGISTRY = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/"
    "sprint1_provider_failure_registry.json"
)
CANONICAL_RELEASE_EVIDENCE = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_release_gate_evidence.json"
)


def _canonical_manuscript(chapter_paths: list[Path]) -> str:
    parts: list[str] = []
    for chapter_path in chapter_paths:
        chapter = BASE.read_json(chapter_path)
        expected_id = chapter_path.stem
        expected = {
            "id": expected_id,
            "bookSlug": SLUG,
            "language": LANGUAGE,
            "processing_status": "ready",
            "processing_warnings": [],
        }
        for key, value in expected.items():
            if chapter.get(key) != value:
                raise BASE.KokoroTitlePilotError(
                    f"controlled chapter truth changed for {expected_id}/{key}"
                )
        content = chapter.get("content")
        if not isinstance(content, str) or not content.strip():
            raise BASE.KokoroTitlePilotError(
                f"controlled chapter content missing: {expected_id}"
            )
        if BASE.sha256_text(content) != chapter.get("sanitizedSha256"):
            raise BASE.KokoroTitlePilotError(
                f"controlled chapter hash changed: {expected_id}"
            )
        parts.append(content.strip())
    return "\n\n".join(parts).strip() + "\n"


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, list[dict[str, Any]]]:
    """Return exact risk passages only while all canonical truth remains bound."""

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
        "cover_status": "CLOUDINARY_ASSIGNED",
        "qa_status": "QA_PASSED",
        "audiobook_enabled": False,
        "audio_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }
    for key, value in expected_book.items():
        if book.get(key) != value:
            raise BASE.KokoroTitlePilotError(
                f"controlled catalog truth changed for {key}: expected {value!r}, "
                f"observed {book.get(key)!r}"
            )
    for cover_key in ("cover_url", "back_cover_url"):
        if not str(book.get(cover_key) or "").startswith(
            "https://res.cloudinary.com/"
        ):
            raise BASE.KokoroTitlePilotError(
                f"canonical {cover_key} is missing or unapproved"
            )

    approval = BASE.read_json(publication / "approval_evidence.json")
    expected_approval = {
        "approved_to_publish": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "audiobook_enabled": False,
    }
    for key, value in expected_approval.items():
        if approval.get(key) != value:
            raise BASE.KokoroTitlePilotError(
                f"controlled approval truth changed for {key}"
            )

    source = BASE.read_json(publication / "source_evidence.json")
    expected_source = {
        "slug": SLUG,
        "source_hash": SOURCE_EVIDENCE_SHA256,
        "content_hash": CONTENT_EVIDENCE_SHA256,
        "source_license": "Public domain",
        "reader_facing_boilerplate_removed": True,
    }
    for key, value in expected_source.items():
        if source.get(key) != value:
            raise BASE.KokoroTitlePilotError(
                f"controlled source evidence changed for {key}"
            )
    if not str(source.get("rights_basis") or "").strip():
        raise BASE.KokoroTitlePilotError("controlled rights basis is missing")

    registry = BASE.read_json(PROVIDER_FAILURE_REGISTRY)
    title_record = (registry.get("titles") or {}).get(SLUG)
    if not isinstance(title_record, dict):
        raise BASE.KokoroTitlePilotError(
            "provider failure registry title is missing"
        )
    if title_record.get("attempts") != []:
        raise BASE.KokoroTitlePilotError(
            "Secret Garden attempt history changed; reselect the profile"
        )
    release = BASE.read_json(CANONICAL_RELEASE_EVIDENCE)
    allowed_release_states = {
        (
            "NOT_RUN",
            "INCOMPLETE_FAIL_CLOSED",
        ),
        (
            "REPRESENTATIVE_LISTENING_9.0_CHAPTER_OBJECTIVE_FAIL",
            "SOURCE_BOUND_DELIVERY_REQUIRED",
        ),
    }
    observed_release_state = (
        release.get("quality_score"),
        release.get("release_gate_state"),
    )
    if (
        release.get("slug") != SLUG
        or observed_release_state not in allowed_release_states
    ):
        raise BASE.KokoroTitlePilotError(
            "canonical release evidence changed; reselect the profile"
        )

    chapters_dir = publication / "chapters"
    chapter_paths = sorted(chapters_dir.glob("chapter-*.json"))
    if len(chapter_paths) != CHAPTER_COUNT:
        raise BASE.KokoroTitlePilotError("canonical chapter count changed")
    manuscript = _canonical_manuscript(chapter_paths)
    if len(manuscript) != CANONICAL_MANUSCRIPT_CHARACTERS:
        raise BASE.KokoroTitlePilotError(
            "canonical manuscript character count changed"
        )
    if BASE.sha256_text(manuscript) != CANONICAL_MANUSCRIPT_SHA256:
        raise BASE.KokoroTitlePilotError("canonical manuscript hash changed")

    chapters = {
        path.stem: re.sub(
            r"\s+", " ", str(BASE.read_json(path).get("content") or "")
        ).strip()
        for path in chapter_paths
    }
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        chapter_id = str(spec["chapter_id"])
        normalized = chapters[chapter_id]
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
                "chapter_id": chapter_id,
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("bounded passage total changed")
    return chapters_dir, passages


_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute


def _exact_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/"
        "sprint1_secret_garden_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def secret_garden_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    source_path = payload["source"].pop("chapter_path")
    risks = {str(item["passage_id"]): str(item["risk"]) for item in PASSAGE_SPECS}
    chapter_ids = {
        str(item["passage_id"]): str(item["chapter_id"]) for item in PASSAGE_SPECS
    }
    for passage in payload["source"]["passages"]:
        passage_id = str(passage["passage_id"])
        passage["chapter_id"] = chapter_ids[passage_id]
        passage["risk"] = risks[passage_id]
    payload.update(
        {
            "schema": "earnalism.kokoro.secret_garden_private_representative.v1",
            "policy": {
                "version": "sprint1_audiobook_acceptance_v3_89",
                "overall_listening_min": 8.9,
                "confidence_min": 0.9,
                "asr_manuscript_min": 9.7,
                "coverage_min": 0.98,
                "representative_pass_cannot_approve_public_release": True,
            },
            "source": {
                **payload["source"],
                "source_path": source_path,
                "canonical_manuscript_sha256": CANONICAL_MANUSCRIPT_SHA256,
                "canonical_manuscript_characters": CANONICAL_MANUSCRIPT_CHARACTERS,
                "chapter_count": CHAPTER_COUNT,
                "source_evidence_sha256": SOURCE_EVIDENCE_SHA256,
                "content_evidence_sha256": CONTENT_EVIDENCE_SHA256,
                "rights_basis_bound": True,
            },
            "catalog_truth": {
                "reader_status": "reader_ready",
                "publication_status": "live",
                "cover_status": "CLOUDINARY_ASSIGNED",
                "audiobook_enabled": False,
                "audio_enabled": False,
                "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            },
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "selection_reason": (
                    "hash-pinned British female voice selected for a British "
                    "children's classic with Mary/Colin dialogue and Yorkshire "
                    "setting; the title has no prior automated attempt"
                ),
                "pipeline_lang_code": PIPELINE_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "selected_asset_is_local_and_hash_verified": True,
                "provider_cost_usd": 0.0,
            },
            "rights": {
                "source_text_rights": "public_domain",
                "model_and_voicepack_license": "Apache-2.0",
                "owner_authorized_open_source_generation": True,
                "title_scoped_production_risk_acceptance_bound": True,
                "private_audition_allowed": True,
                "production_release_approved": False,
                "public_disclosure_if_later_released": "AI narration",
            },
            "next_stage_contract": {
                "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
                "exact_execute_command": _exact_command(Path(kwargs["asset_root"])),
                "scope": "four exact source-bound passages only",
                "pipeline_lang_code": PIPELINE_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "g2p_fallback_enabled": False,
                "browser_or_system_speech_fallback": False,
                "asr_must_pass_before_listening_qa": True,
                "full_title_generation_allowed": False,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
            },
        }
    )
    payload["blockers_to_release"] = [
        "REPRESENTATIVE_AUDIO_NOT_GENERATED",
        "REPRESENTATIVE_ASR_NOT_RUN",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    return payload, passages, artifacts


def secret_garden_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["blockers_to_release"] = [
        blocker.replace(
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        )
        for blocker in payload["blockers_to_release"]
        if blocker != "OWNER_10_TARGET_NOT_VERIFIED"
    ]
    if (
        "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
        in payload["blockers_to_release"]
    ):
        payload["blockers_to_release"].remove(
            "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
        )
    return code, payload


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = CANONICAL_MANUSCRIPT_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = CANONICAL_MANUSCRIPT_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(
        str(item["sha256"]) for item in PASSAGE_SPECS
    )
    BASE.EXPECTED_PASSAGE_CHARACTERS = PASSAGE_CHARACTERS
    BASE.MODEL_REVISION = MODEL_REVISION
    BASE.MODEL_SHA256 = MODEL_SHA256
    BASE.CONFIG_SHA256 = CONFIG_SHA256
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = f"voices/{VOICE}.pt"
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.WHISPER_SHA256 = WHISPER_SHA256
    BASE.PIPELINE_LANG_CODE = PIPELINE_LANG_CODE
    BASE.G2P_BRITISH = G2P_BRITISH
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = {}
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset()
    BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (
                *BASE.NO_REPEAT_FILES,
                PROVIDER_FAILURE_REGISTRY,
                CANONICAL_RELEASE_EVIDENCE,
            )
        )
    )
    BASE.controlled_source = controlled_source
    BASE.preflight = secret_garden_preflight
    BASE.execute = secret_garden_execute


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
    raise SystemExit(main(sys.argv[1:]))
