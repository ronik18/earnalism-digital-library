#!/usr/bin/env python3
"""Run one fallback-free Secret Garden ``af_bella`` representative pilot.

The adapter binds four risk-diverse passages to the complete 27-chapter
controlled publication, current rights/cover truth, pinned local Kokoro and
Whisper artifacts, and an immutable attempt fingerprint. It can only write
private WAV/evidence files; it has no listening, upload, publication, browser,
or release-gate mutation surface.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("secret_garden_kokoro_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Kokoro representative base: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-secret-garden"
TITLE = "The Secret Garden"
AUTHOR = "Frances Hodgson Burnett"
LANGUAGE = "eng"
PROFILE = "secret-garden-af-bella-v1"
VOICE = BASE.VOICE
VOICE_SHA256 = BASE.VOICE_SHA256
WHISPER_SHA256 = BASE.WHISPER_SHA256
EXPECTED_RECONCILIATION_SHA256 = (
    "4aac34ad4bda3586f1a062b24b3ca271a96edef7e4938d13042d0595f692f3a3"
)
EXPECTED_CONCATENATED_CONTENT_SHA256 = (
    "4aac34ad4bda3586f1a062b24b3ca271a96edef7e4938d13042d0595f692f3a3"
)
EXPECTED_SOURCE_CHARACTERS = 431_542
EXPECTED_CHAPTER_COUNT = 27
EXPECTED_FRONT_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779947920/"
    "earnalism/covers/front/cover_2b4da5be-b494-42c1-bf4b-302011b3ae3c.png"
)
EXPECTED_BACK_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779947939/"
    "earnalism/covers/back/back_cover_2b4da5be-b494-42c1-bf4b-302011b3ae3c.png"
)
EXPECTED_BOUND_FILE_HASHES = {
    "approval_evidence.json": "bb0b315a3f02fa15d72d27e53f8a262956baaec2f66cb186632dc7dfe32a209d",
    "public_book.json": "a0dfa5fa5cff672580b1d34062a472ba704838aba96107bf5f610d22251b994a",
    "source_evidence.json": "3d6309d38d1c1648d9427998430701ab0f9254cc4d64e7f26832a8438f0b982b",
}
PASSAGE_SPECS = (
    {
        "passage_id": "opening_india",
        "chapter": "chapter-001.json",
        "risk": "opening_names_colonial_setting_and_narrative_tone",
        "start": "When Mary Lennox was sent",
        "end": "must keep the child out of sight as much as possible.",
        "characters": 820,
        "sha256": "9921329ed99b36731d1ca45e6f209dd44e3fc22376009f75d3e4246d94daf341",
    },
    {
        "passage_id": "yorkshire_dialogue",
        "chapter": "chapter-004.json",
        "risk": "yorkshire_dialect_dialogue_and_character_contrast",
        "start": "“Who is going to dress me?” demanded Mary.",
        "end": "walk as if they was puppies!”",
        "characters": 855,
        "sha256": "be1275f2818dab21ed28678a84a6a4029a41166bc74fe7b2caedbc58290285ad",
    },
    {
        "passage_id": "mary_colin_emotion",
        "chapter": "chapter-017.json",
        "risk": "sustained_emotion_argument_and_punctuation",
        "start": "“If you scream another scream,”",
        "end": "Turn over and let me look at it!”",
        "characters": 963,
        "sha256": "ff3b5af98b532ad81f19df606c456aea0580519c9683d5a81b48de755a4023dd",
    },
    {
        "passage_id": "ending_return",
        "chapter": "chapter-027.json",
        "risk": "ending_reveal_names_and_triumphant_restraint",
        "start": "When Mrs. Medlock looked",
        "end": "Yorkshire—Master Colin!",
        "characters": 484,
        "sha256": "bdd08b81e13c0ec9c4e74854e1c8eb939963ba13c76187c258b39488193cb6cc",
    },
)
EXPECTED_PASSAGE_CHARACTERS = 3_122
PRONUNCIATION_OVERRIDES = {
    "Lennox": "lˈɛnəks",
    "Misselthwaite": "mˈɪzəlθwˌeɪt",
    "Martha": "mˈɑɹθə",
    "tha": "ðˈɑ",
    "thysen": "ðaɪsˈɛn",
    "Medlock": "mˈɛdlɑk",
    "sayin": "sˈeɪɪn",
    "bein": "bˈiɪn",
}
EXPECTED_PHONEME_HASHES = {
    "opening_india": "5f7a5912b0071e36fb31e2f4402438ca823fdcb1b070e29e06992232606901c4",
    "yorkshire_dialogue": "6e71fcc2f42bdb4650265731f50f93108d4f49e4e073612a629ee5bf2e2224c2",
    "mary_colin_emotion": "0370a80635651425e16e9afccdd90a602821417c5738613123d0fde94f2f20b0",
    "ending_return": "de83a767a126827f902f416823cbc8ff72915654a81649b626c95d4c7067092a",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical names and source spellings: Mary Lennox; Misselthwaite; Martha; "
    "Mrs. Medlock; Colin; Yorkshire; Ayah; Mem Sahib; tha; thysen; sayin; bein. "
    "Preserve every complete source word and the Yorkshire dialect."
)
ASR_PROMPT_POLICY = {str(item["passage_id"]): "canonical_vocabulary_prompt" for item in PASSAGE_SPECS}
SOURCE_EQUIVALENCE_POLICY = {str(item["passage_id"]): () for item in PASSAGE_SPECS}
RANDOM_SEED = 2026072002
SPEED = 1.0
EXPECTED_ATTEMPT_FINGERPRINT = (
    "85ea18462a896ab42f61cca055a8d6a24190077884c24fef9a80701e955d3a67"
)

DEFAULT_ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/artifacts"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/whisper-cache"
)
DEFAULT_PRIVATE_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-secret-garden/"
    "f3ff3571-af-bella-representative-v1"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_representative_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BASE.KokoroTitlePilotError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def controlled_source(asset_root: Path, slug: str) -> tuple[Path, list[dict[str, Any]]]:
    _require(slug, SLUG, "slug")
    root = asset_root / "data/controlled_publications" / slug
    backend = asset_root / "backend/data/controlled_publications" / slug
    book = BASE.read_json(root / "public_book.json")
    approval = BASE.read_json(root / "approval_evidence.json")
    source_evidence = BASE.read_json(root / "source_evidence.json")
    for name, expected_hash in EXPECTED_BOUND_FILE_HASHES.items():
        root_path = root / name
        backend_path = backend / name
        if root_path.read_bytes() != backend_path.read_bytes():
            raise BASE.KokoroTitlePilotError(f"root/backend metadata mismatch: {name}")
        _require(BASE.sha256_file(root_path), expected_hash, f"{name} SHA-256")
    for base in (root, backend):
        checksum = BASE.read_json(base / "checksum_manifest.json")
        checksum_files = {
            str(item.get("file")): str(item.get("sha256"))
            for item in checksum.get("files", [])
            if isinstance(item, dict)
        }
        for name, expected_hash in EXPECTED_BOUND_FILE_HASHES.items():
            _require(
                checksum_files.get(name),
                expected_hash,
                f"{base.relative_to(asset_root)} checksum for {name}",
            )
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "author_death_year": 1924,
        "original_publication_year": 1911,
    }.items():
        _require(book.get(key), expected, f"public_book.{key}")
    _require(book.get("cover_url"), EXPECTED_FRONT_COVER_URL, "front cover URL")
    _require(book.get("back_cover_url"), EXPECTED_BACK_COVER_URL, "back cover URL")
    _require(approval.get("audiobook_use_approved"), True, "audiobook use approval")
    _require(approval.get("audio_public_release"), "PUBLIC_AUDIO_RELEASE_NOT_APPROVED", "public audio release")
    _require(approval.get("audiobook_enabled"), False, "approval audiobook state")
    _require(source_evidence.get("author_death_year"), 1924, "source author death year")
    _require(source_evidence.get("original_publication_year"), 1911, "source publication year")
    _require(
        source_evidence.get("author_death_year_evidence_url"),
        "https://www.loc.gov/item/11021580/",
        "author death evidence URL",
    )
    _require(
        source_evidence.get("original_publication_evidence_url"),
        "https://www.loc.gov/item/11021580/",
        "publication evidence URL",
    )

    reconciliation = BASE.read_json(
        asset_root
        / "internal/audiobook_lab/sprint1_publication/sprint1_pipeline_input_reconciliation.json"
    )
    record = next(
        (item for item in reconciliation.get("titles", []) if item.get("slug") == SLUG),
        None,
    )
    if not isinstance(record, dict):
        raise BASE.KokoroTitlePilotError("Secret Garden reconciliation record is missing")
    for key, expected in {
        "canonical_source_file_count": EXPECTED_CHAPTER_COUNT,
        "canonical_source_sha256": EXPECTED_RECONCILIATION_SHA256,
        "canonical_source_chars": EXPECTED_SOURCE_CHARACTERS,
        "source_reconciliation_status": "ROOT_BACKEND_MATCH",
        "rights_status": "PASS",
        "cover_status": "PASS_DIRECT_FRONT_BACK",
        "sanitation_status": "PASS",
        "ready_for_audition": True,
        "exact_blocker": "NONE",
        "cover_front_url": EXPECTED_FRONT_COVER_URL,
        "cover_back_url": EXPECTED_BACK_COVER_URL,
    }.items():
        _require(record.get(key), expected, f"reconciliation.{key}")

    chapter_paths = sorted((root / "chapters").glob("chapter-*.json"))
    _require(len(chapter_paths), EXPECTED_CHAPTER_COUNT, "chapter count")
    contents: list[str] = []
    chapter_payloads: dict[str, dict[str, Any]] = {}
    for chapter_path in chapter_paths:
        backend_path = backend / "chapters" / chapter_path.name
        if chapter_path.read_bytes() != backend_path.read_bytes():
            raise BASE.KokoroTitlePilotError(
                f"root/backend chapter mismatch: {chapter_path.name}"
            )
        chapter = BASE.read_json(chapter_path)
        _require(chapter.get("processing_status"), "ready", f"{chapter_path.name} status")
        _require(chapter.get("processing_warnings"), [], f"{chapter_path.name} warnings")
        contents.append(str(chapter.get("content") or ""))
        chapter_payloads[chapter_path.name] = chapter
    # Match the canonical multi-chapter source convention used by the Sprint 1
    # reconciliation: two newlines between chapters and one terminal newline.
    manuscript = "\n\n".join(contents) + "\n"
    _require(len(manuscript), EXPECTED_SOURCE_CHARACTERS, "concatenated source characters")
    _require(
        BASE.sha256_text(manuscript),
        EXPECTED_CONCATENATED_CONTENT_SHA256,
        "concatenated source SHA-256",
    )

    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        flattened = re.sub(
            r"\s+", " ", str(chapter_payloads[str(spec["chapter"])].get("content") or "")
        ).strip()
        start_marker = str(spec["start"])
        end_marker = str(spec["end"])
        _require(flattened.count(start_marker), 1, f"{spec['passage_id']} start marker count")
        start = flattened.index(start_marker)
        end = flattened.index(end_marker, start) + len(end_marker)
        text = flattened[start:end]
        _require(len(text), spec["characters"], f"{spec['passage_id']} characters")
        _require(BASE.sha256_text(text), spec["sha256"], f"{spec['passage_id']} SHA-256")
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "risk": spec["risk"],
                "chapter": spec["chapter"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    _require(
        sum(int(item["characters"]) for item in passages),
        EXPECTED_PASSAGE_CHARACTERS,
        "passage character total",
    )
    return root / "chapters", passages


def g2p_preflight(passages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(
        trf=False, british=BASE.G2P_BRITISH, fallback=None, unk=""
    )
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    reports: list[dict[str, Any]] = []
    for passage in passages:
        phonemes, tokens = g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        passage_id = str(passage["passage_id"])
        observed_hash = BASE.sha256_text(str(phonemes))
        _require(unresolved, [], f"{passage_id} unresolved G2P tokens")
        _require(
            observed_hash,
            EXPECTED_PHONEME_HASHES[passage_id],
            f"{passage_id} phoneme SHA-256",
        )
        reports.append(
            {
                "passage_id": passage_id,
                "source_text_sha256": passage["text_sha256"],
                "phoneme_sha256": observed_hash,
                "unresolved_tokens": [],
                "fallback_enabled": False,
            }
        )
    return reports


_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute
_BASE_ATTEMPT_FINGERPRINT = BASE.attempt_fingerprint
_BASE_ENSURE_NOT_REPEATED = BASE.ensure_not_repeated


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    """Bind the base attempt to the exact language and fallback-free G2P contract."""

    contract = {
        "contract": "earnalism.kokoro.secret_garden_representative.v1",
        "base_contract_fingerprint": _BASE_ATTEMPT_FINGERPRINT(passages),
        "kokoro_lang_code": BASE.KOKORO_LANG_CODE,
        "g2p_british": BASE.G2P_BRITISH,
        "phoneme_hashes": EXPECTED_PHONEME_HASHES,
        "g2p_fallback_enabled": False,
    }
    return BASE.sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    """Reject the fingerprint anywhere in durable Sprint 1 attempt evidence."""

    _BASE_ENSURE_NOT_REPEATED(fingerprint, output)
    evidence_paths = [
        BASE.ROOT
        / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
        BASE.ROOT
        / "internal/audiobook_lab/sprint1_publication/title_runs/the-secret-garden_release_gate_evidence.json",
        BASE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ]
    evidence_paths.extend(
        sorted(
            (
                BASE.ROOT
                / "internal/audiobook_lab/sprint1_publication/title_runs"
            ).glob("*.json")
        )
    )
    resolved_output = output.expanduser().resolve()
    for evidence in evidence_paths:
        if not evidence.is_file() or evidence.resolve() == resolved_output:
            continue
        if fingerprint in evidence.read_text(encoding="utf-8", errors="strict"):
            raise BASE.KokoroTitlePilotError(
                f"attempt fingerprint already exists in durable evidence: {evidence}"
            )


def preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    fingerprint = str((payload.get("engine") or {}).get("attempt_fingerprint") or "")
    _require(fingerprint, EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    payload["schema"] = "earnalism.kokoro.secret_garden_representative.v1"
    payload["engine"].update(
        {
            "kokoro_lang_code": BASE.KOKORO_LANG_CODE,
            "g2p_british": BASE.G2P_BRITISH,
        }
    )
    payload["source"].update(
        {
            "chapter_count": EXPECTED_CHAPTER_COUNT,
            "reconciliation_sha256": EXPECTED_RECONCILIATION_SHA256,
            "concatenated_content_sha256": EXPECTED_CONCATENATED_CONTENT_SHA256,
            "source_characters": EXPECTED_SOURCE_CHARACTERS,
            "root_backend_bound_files_match": True,
            "bound_file_sha256": EXPECTED_BOUND_FILE_HASHES,
            "front_cover_url": EXPECTED_FRONT_COVER_URL,
            "back_cover_url": EXPECTED_BACK_COVER_URL,
        }
    )
    payload["g2p_preflight_evidence"] = g2p_preflight(passages)
    payload["rights"] = {
        "model_and_voicepack_license": "Apache-2.0",
        "model_card_url": (
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/"
            f"{BASE.MODEL_REVISION}/README.md"
        ),
        "model_license_url": (
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/"
            f"{BASE.MODEL_REVISION}/COPYING"
        ),
        "controlled_text_public_domain": True,
        "author_death_year": 1924,
        "author_death_year_evidence_url": "https://www.loc.gov/item/11021580/",
        "original_publication_year": 1911,
        "original_publication_evidence_url": "https://www.loc.gov/item/11021580/",
        "controlled_source_evidence_sha256": EXPECTED_BOUND_FILE_HASHES[
            "source_evidence.json"
        ],
        "private_audition_allowed": True,
        "production_release_approved": False,
        "public_disclosure_required_if_later_approved": "AI voice",
    }
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "SECRET_GARDEN_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return payload, passages, artifacts


def execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["schema"] = "earnalism.kokoro.secret_garden_representative.v1"
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "SECRET_GARDEN_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return code, payload


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = EXPECTED_RECONCILIATION_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = EXPECTED_SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(str(item["sha256"]) for item in PASSAGE_SPECS)
    BASE.EXPECTED_PASSAGE_CHARACTERS = EXPECTED_PASSAGE_CHARACTERS
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.SPEED = SPEED
    BASE.KOKORO_LANG_CODE = "a"
    BASE.G2P_BRITISH = False
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset()
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = {}
    BASE.attempt_fingerprint = attempt_fingerprint
    BASE.ensure_not_repeated = ensure_not_repeated
    BASE.controlled_source = controlled_source
    BASE.preflight = preflight
    BASE.execute = execute


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults = (
        ("--slug", SLUG),
        ("--profile", PROFILE),
        ("--asset-root", BASE.ROOT),
        ("--artifact-dir", DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", DEFAULT_WHISPER_CACHE),
        ("--private-output-dir", DEFAULT_PRIVATE_DIR),
        ("--output", DEFAULT_OUTPUT),
        ("--paid-lock", DEFAULT_PAID_LOCK),
    )
    for option, value in defaults:
        if option not in options:
            args.extend((option, str(value)))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_base()
    args = list(argv or [])
    if "--asr-reverify-existing" in args:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_FAIL_CLOSED",
                    "error": (
                        "ASR reverify is disabled until this generated candidate's "
                        "four audio hashes are code-reviewed and pinned"
                    ),
                },
                indent=2,
            )
        )
        return 2
    return int(BASE.main(expand_defaults(args)))


configure_base()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
