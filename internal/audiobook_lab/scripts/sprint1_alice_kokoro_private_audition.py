#!/usr/bin/env python3
"""Prepare or run Alice in Wonderland's bounded private Kokoro pilot.

The profile binds the canonical twelve-chapter controlled publication,
public-domain rights, exact Cloudinary covers, four representative passages,
and a checksum-pinned British Kokoro voice. Preflight has no synthesis side
effect. ``--execute`` creates only private samples and cannot upload, publish,
or mutate release truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location(
    "earnalism_kokoro_title_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "alices-adventures-in-wonderland"
PROFILE = "alice-bf-emma-british-whimsy-v1"
TITLE = "Alice's Adventures in Wonderland"
AUTHOR = "Lewis Carroll"
LANGUAGE = "en"

SOURCE_EVIDENCE_SHA256 = (
    "49c44704fee971be4aff3b6ebf4764b9aabf0c1f338ca72942216a301205bd8d"
)
CONTENT_EVIDENCE_SHA256 = (
    "37e99a24d25aea8914744cf4717c7f7540303fa0aff01db75b1143f6fb637447"
)
CANONICAL_MANUSCRIPT_SHA256 = (
    "c8cd98430bcaa621dd206b8d3c880b34ca3daf4776e4b89c8a10d8c5f84cb2d3"
)
CANONICAL_MANUSCRIPT_CHARACTERS = 144_843
CHAPTER_COUNT = 12

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
SPEED = 0.97
RANDOM_SEED = 2026072802

PASSAGE_SPECS = (
    {
        "passage_id": "opening_rabbit_hook",
        "chapter_id": "chapter-001",
        "start": "Alice was beginning to get very tired",
        "end": "close by her.",
        "characters": 592,
        "sha256": (
            "9fa63f79b504b41a39bb743cca05f022ff6466fee7a379f95518efe33b95838c"
        ),
        "risk": (
            "opening authority, interior thought, long punctuation, and the "
            "White Rabbit reveal"
        ),
    },
    {
        "passage_id": "caterpillar_identity_dialogue",
        "chapter_id": "chapter-005",
        "start": "Who are _you?_",
        "end": "“I don’t see,” said the Caterpillar.",
        "characters": 488,
        "sha256": (
            "c4756e5876057019307352225d5fce7548bb7a9a44efea5b3b9a7cc7cf6b4273"
        ),
        "risk": (
            "rapid character dialogue, stammering, em-dash pauses, emphasis, "
            "and identity confusion"
        ),
    },
    {
        "passage_id": "mad_tea_party_exchange",
        "chapter_id": "chapter-007",
        "start": "The table was a large one",
        "end": (
            "It wasn’t very civil of you to sit down without being invited,” "
            "said the March Hare."
        ),
        "characters": 630,
        "sha256": (
            "cf7055d45141e8acc3f1c34b906174efba37a6b6c90fba1fec59cbef51c02877"
        ),
        "risk": (
            "comic ensemble timing, repeated dialogue, indignation, and "
            "speaker separation"
        ),
    },
    {
        "passage_id": "wonderland_reflective_finale",
        "chapter_id": "chapter-012",
        "start": (
            "Lastly, she pictured to herself how this same little sister of "
            "hers"
        ),
        "end": (
            "remembering her own child-life, and the happy summer days."
        ),
        "characters": 555,
        "sha256": (
            "5a5706f3b83a57db584682ba373e0de231f5c327de20a65374058d14264212f6"
        ),
        "risk": (
            "reflective emotional close, long semicolon structure, restrained "
            "warmth, and final cadence"
        ),
    },
)
PASSAGE_CHARACTERS = 2_265

PRONUNCIATION_OVERRIDES = {
    "Alice": "ˈalɪs",
    "Carroll": "kˈaɹəl",
    "Dormouse": "dˈɔːmaʊs",
    "Gryphon": "ɡɹˈɪfən",
    "Wonderland": "wˈʌndələnd",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical spellings: Alice; Lewis Carroll; White Rabbit; Caterpillar; "
    "March Hare; Hatter; Dormouse; Gryphon; Wonderland. Preserve every source "
    "word in exact order."
)
ASR_PROMPT_POLICY = {
    item["passage_id"]: "canonical_vocabulary_prompt"
    for item in PASSAGE_SPECS
}
SOURCE_EQUIVALENCE_POLICY = {
    item["passage_id"]: () for item in PASSAGE_SPECS
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
    tempfile.gettempdir()
) / (
    "earnalism-alice-kokoro-bf-emma-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "alices-adventures-in-wonderland_kokoro_bf_emma_representative_v1.json"
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
    "alices-adventures-in-wonderland_release_gate_evidence.json"
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
    """Return four exact passages while canonical truth remains bound."""

    if slug != SLUG:
        raise BASE.KokoroTitlePilotError(
            f"slug is not allowed by {PROFILE}: {slug}; only {SLUG} is permitted"
        )
    publication = asset_root / "data/controlled_publications" / SLUG
    if not (publication / "public_book.json").is_file():
        publication = asset_root / "backend/data/controlled_publications" / SLUG
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
                f"controlled catalog truth changed for {key}: expected "
                f"{value!r}, observed {book.get(key)!r}"
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
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED",
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
        "reader_facing_boilerplate_removed": True,
    }
    for key, value in expected_source.items():
        if source.get(key) != value:
            raise BASE.KokoroTitlePilotError(
                f"controlled source evidence changed for {key}"
            )
    if (
        "public domain" not in str(source.get("source_license") or "").lower()
        or not str(source.get("rights_basis") or "").strip()
    ):
        raise BASE.KokoroTitlePilotError(
            "controlled public-domain rights evidence is missing"
        )

    registry = BASE.read_json(PROVIDER_FAILURE_REGISTRY)
    title_record = (registry.get("titles") or {}).get(SLUG)
    if not isinstance(title_record, dict):
        raise BASE.KokoroTitlePilotError(
            "provider failure registry title is missing"
        )
    if title_record.get("attempts") != []:
        raise BASE.KokoroTitlePilotError(
            "Alice attempt history changed; reselect the profile"
        )
    release = BASE.read_json(CANONICAL_RELEASE_EVIDENCE)
    release_state = (
        release.get("quality_score"),
        release.get("release_gate_state"),
    )
    allowed_release_states = {
        ("NOT_RUN", "INCOMPLETE_FAIL_CLOSED"),
        (
            "REPRESENTATIVE_ASR_REPAIR_FAILED_3_OF_4_EXACT",
            "SOURCE_BOUND_DELIVERY_REQUIRED",
        ),
    }
    if release.get("slug") != SLUG or release_state not in allowed_release_states:
        raise BASE.KokoroTitlePilotError(
            "canonical release evidence changed; reselect the profile"
        )
    if release_state[1] == "SOURCE_BOUND_DELIVERY_REQUIRED":
        attempts = release.get("bounded_candidate_attempts")
        attempt = attempts[0] if isinstance(attempts, list) and attempts else {}
        if (
            len(attempts or []) != 1
            or attempt.get("attempt_fingerprint")
            != "c1e8a0ae6617093d8f13b0b07ca3a72115dd56d9336a04716f44d116f7aad458"
            or attempt.get("asr_repair_fingerprint")
            != "59ee181f736e534ccab753a355696de7cc2d40c22e647e68092fec3a056ba20c"
            or attempt.get("status")
            != "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED"
        ):
            raise BASE.KokoroTitlePilotError(
                "closed Alice attempt evidence changed"
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
        if (
            len(text) != spec["characters"]
            or BASE.sha256_text(text) != spec["sha256"]
        ):
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
        "sprint1_alice_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def alice_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    source_path = payload["source"].pop("chapter_path")
    risks = {
        str(item["passage_id"]): str(item["risk"])
        for item in PASSAGE_SPECS
    }
    chapter_ids = {
        str(item["passage_id"]): str(item["chapter_id"])
        for item in PASSAGE_SPECS
    }
    for passage in payload["source"]["passages"]:
        passage_id = str(passage["passage_id"])
        passage["chapter_id"] = chapter_ids[passage_id]
        passage["risk"] = risks[passage_id]
    payload.update(
        {
            "schema": "earnalism.kokoro.alice_private_representative.v1",
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
                "canonical_manuscript_characters": (
                    CANONICAL_MANUSCRIPT_CHARACTERS
                ),
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
                "audio_public_release": (
                    "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED"
                ),
                "legacy_remote_object_reuse_allowed": False,
            },
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "selection_reason": (
                    "hash-pinned British female voice selected for a British "
                    "children's fantasy with whimsical ensemble dialogue and "
                    "a reflective close; no prior TTS attempt exists"
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
                "exact_execute_command": _exact_command(
                    Path(kwargs["asset_root"])
                ),
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


def alice_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["blockers_to_release"] = [
        blocker.replace(
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "ALICE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        )
        for blocker in payload["blockers_to_release"]
        if blocker != "OWNER_10_TARGET_NOT_VERIFIED"
    ]
    if (
        "ALICE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
        in payload["blockers_to_release"]
    ):
        payload["blockers_to_release"].remove(
            "ALICE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
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
    BASE.preflight = alice_preflight
    BASE.execute = alice_execute


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
