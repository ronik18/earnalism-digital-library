#!/usr/bin/env python3
"""Run one fallback-free ``bm_george`` pilot for The Time Machine.

The profile binds four risk-diverse passages to the complete controlled
publication, current rights and cover evidence, and checksum-pinned local
Kokoro/Whisper artifacts.  It may write only private WAV/evidence files and
has no listening, full-title, upload, publication, browser, or release-gate
mutation surface.
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
SPEC = importlib.util.spec_from_file_location("time_machine_kokoro_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Kokoro representative base: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-time-machine"
TITLE = "The Time Machine"
AUTHOR = "H. G. Wells"
LANGUAGE = "eng"
PROFILE = "time-machine-bm-george-v1"
VOICE = "bm_george"
VOICE_FILENAME = "voices/bm_george.pt"
VOICE_SHA256 = "f1bc812213dc59774769e5c80004b13eeb79bd78130b11b2d7f934542dab811b"
WHISPER_SHA256 = BASE.WHISPER_SHA256
KOKORO_LANG_CODE = "b"
G2P_BRITISH = True
EXPECTED_RECONCILIATION_SHA256 = (
    "cb7c2b70194eeb8f0376f5ece4d6a5fdce547fbfca23d4c842337f2c024fe1e8"
)
EXPECTED_SOURCE_CHARACTERS = 181_242
EXPECTED_CHAPTER_COUNT = 16
EXPECTED_FRONT_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566866/"
    "earnalism/covers/front/cover_d4cb4472-7e0a-4bad-ab89-05f7d7ace821.png"
)
EXPECTED_BACK_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566887/"
    "earnalism/covers/back/back_cover_d4cb4472-7e0a-4bad-ab89-05f7d7ace821.png"
)
EXPECTED_BOUND_FILE_HASHES = {
    "approval_evidence.json": "3f39a3de047cc23fe9518c948711a5b81050a85833082e662d1cd89d40375a4c",
    "public_book.json": "290154ee5771ebd684eceef3f026de18a1a0b79ac7f08503763488ab07531abc",
    "source_evidence.json": "551ffed0f08c0e120cab9ae91cb4adfac8003e25f739d29a7b53c05ff269d0c5",
}
PASSAGE_SPECS = (
    {
        "passage_id": "opening_exposition",
        "chapter": "chapter-001.json",
        "risk": "opening_literary_exposition_long_sentences_and_punctuation",
        "start": "The Time Traveller (for so it will be convenient to speak of him) was",
        "end": "his earnestness over this new paradox (as we thought it) and his fecundity.",
        "characters": 745,
        "sha256": "22dc5f715d1f9ecf4a32b6a92c57d97cd6f86c39c70d7b997c453ec197eb82c2",
    },
    {
        "passage_id": "eloi_first_contact",
        "chapter": "chapter-005.json",
        "risk": "first_person_wonder_character_contrast_and_gentle_emotion",
        "start": "“In another moment we were standing face to face, I and this fragile",
        "end": "Then I turned again to see what I could do in the way of communication.",
        "characters": 1475,
        "sha256": "6262bd33a6ab3f8e742c55372b2eb4421ca84ec75e123c12ec36528c36a62077",
    },
    {
        "passage_id": "morlock_darkness",
        "chapter": "chapter-012.json",
        "risk": "suspense_pacing_names_and_short_sentence_escalation",
        "start": "“For some way I heard nothing but the crackling twigs under my feet,",
        "end": "Then the match scratched and fizzed.",
        "characters": 933,
        "sha256": "f1a209de898abbbaf96624ac4ca16d06f9f065bd2d6137a995586dc2610ee084",
    },
    {
        "passage_id": "epilogue_tenderness",
        "chapter": "chapter-016.json",
        "risk": "scientific_vocabulary_reflection_and_restrained_ending_emotion",
        "start": "One cannot choose but wonder. Will he ever return?",
        "end": "still lived on in the heart of man.",
        "characters": 1528,
        "sha256": "ef675e8a4077b5e93c07f9e71102cf66ff51711a28be1ab22fef05bc1f78782b",
    },
)
EXPECTED_PASSAGE_CHARACTERS = 4_681
PRONUNCIATION_OVERRIDES = {
    "Morlocks": "mˈɔːlɒks",
    "Weena": "wˈiːnə",
    "civilisation": "sˌɪvɪlaɪzˈeɪʃən",
}
EXPECTED_PHONEME_HASHES = {
    "opening_exposition": "c961205cd79814fc486a97d0ed4a7b275f26fcc34deedb49992ab8e90f9a5403",
    "eloi_first_contact": "b27ee448fda845f4eadb916610c876d2549aa239a77710b74cb1dcb27bf4a25a",
    "morlock_darkness": "89b4e71933964121e6ec8e61b671b570bf4319ea564610702c34a427d4508302",
    "epilogue_tenderness": "21ec5c946aa59e14c0eb5f798c382fbcc3035a99451b2f9297f022bb7da37793",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical names and spellings: Time Traveller; Weena; Morlocks; Cretaceous; "
    "Jurassic; plesiosaurus; Oolitic; Triassic; civilisation. Preserve every "
    "complete source word and the British spelling."
)
ASR_PROMPT_POLICY = {
    str(item["passage_id"]): "canonical_vocabulary_prompt" for item in PASSAGE_SPECS
}
SOURCE_EQUIVALENCE_POLICY = {
    str(item["passage_id"]): () for item in PASSAGE_SPECS
}
SPEED = 0.96
RANDOM_SEED = 2026072006
EXPECTED_ATTEMPT_FINGERPRINT = (
    "9d59dee17c4ddd2bf2ba1e67b0e3dc80b9dd4a2c95785147869e3a305d75b7e3"
)

DEFAULT_ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/artifacts"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_PRIVATE_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-time-machine/"
    "f3ff3571-bm-george-representative-v1"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_kokoro_bm_george_representative_v1.json"
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
        recorded = {
            str(item.get("file")): str(item.get("sha256"))
            for item in checksum.get("files", [])
            if isinstance(item, dict)
        }
        for name, expected_hash in EXPECTED_BOUND_FILE_HASHES.items():
            _require(recorded.get(name), expected_hash, f"checksum for {name}")

    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "author_death_year": 1946,
        "original_publication_year": 1895,
    }.items():
        _require(book.get(key), expected, f"public_book.{key}")
    _require(book.get("cover_url"), EXPECTED_FRONT_COVER_URL, "front cover URL")
    _require(book.get("back_cover_url"), EXPECTED_BACK_COVER_URL, "back cover URL")
    _require(approval.get("audiobook_use_approved"), True, "audiobook use approval")
    _require(
        approval.get("audio_public_release"),
        "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "public audio release",
    )
    _require(approval.get("audiobook_enabled"), False, "approval audiobook state")
    _require(source_evidence.get("author_death_year"), 1946, "author death year")
    _require(source_evidence.get("original_publication_year"), 1895, "publication year")
    _require(
        source_evidence.get("author_death_year_evidence_url"),
        "https://www.gutenberg.org/ebooks/35",
        "author death evidence URL",
    )
    _require(
        source_evidence.get("original_publication_evidence_url"),
        "https://www.gutenberg.org/ebooks/35",
        "publication evidence URL",
    )

    reconciliation = BASE.read_json(
        asset_root
        / "internal/audiobook_lab/sprint1_publication/"
        "sprint1_pipeline_input_reconciliation.json"
    )
    record = next(
        (item for item in reconciliation.get("titles", []) if item.get("slug") == SLUG),
        None,
    )
    if not isinstance(record, dict):
        raise BASE.KokoroTitlePilotError("Time Machine reconciliation record is missing")
    for key, expected in {
        "canonical_source_file_count": EXPECTED_CHAPTER_COUNT,
        "canonical_source_sha256": EXPECTED_RECONCILIATION_SHA256,
        "canonical_source_chars": EXPECTED_SOURCE_CHARACTERS,
        "source_reconciliation_status": "ROOT_BACKEND_MATCH",
        "rights_status": "PASS",
        "cover_status": "PASS_DIRECT_FRONT_BACK",
        "sanitation_status": "PASS",
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
    manuscript = "\n\n".join(contents) + "\n"
    _require(len(manuscript), EXPECTED_SOURCE_CHARACTERS, "source characters")
    _require(
        BASE.sha256_text(manuscript),
        EXPECTED_RECONCILIATION_SHA256,
        "source SHA-256",
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

    g2p = misaki_en.G2P(trf=False, british=G2P_BRITISH, fallback=None, unk="")
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
    contract = {
        "contract": "earnalism.kokoro.time_machine_representative.v1",
        "base_contract_fingerprint": _BASE_ATTEMPT_FINGERPRINT(passages),
        "kokoro_lang_code": KOKORO_LANG_CODE,
        "g2p_british": G2P_BRITISH,
        "phoneme_hashes": EXPECTED_PHONEME_HASHES,
        "g2p_fallback_enabled": False,
    }
    return BASE.sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    _BASE_ENSURE_NOT_REPEATED(fingerprint, output)
    evidence_paths = [
        BASE.ROOT
        / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
        BASE.ROOT
        / "internal/audiobook_lab/sprint1_publication/title_runs/"
        "the-time-machine_release_gate_evidence.json",
        BASE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ]
    evidence_paths.extend(
        sorted(
            (
                BASE.ROOT / "internal/audiobook_lab/sprint1_publication/title_runs"
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
    payload["schema"] = "earnalism.kokoro.time_machine_representative.v1"
    payload["engine"].update(
        {
            "voice": VOICE,
            "voice_sha256": VOICE_SHA256,
            "kokoro_lang_code": KOKORO_LANG_CODE,
            "g2p_british": G2P_BRITISH,
        }
    )
    payload["source"].update(
        {
            "chapter_count": EXPECTED_CHAPTER_COUNT,
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
        "voice_file_url": (
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/"
            f"{BASE.MODEL_REVISION}/{VOICE_FILENAME}"
        ),
        "controlled_text_public_domain": True,
        "author_death_year": 1946,
        "author_death_year_evidence_url": "https://www.gutenberg.org/ebooks/35",
        "original_publication_year": 1895,
        "original_publication_evidence_url": "https://www.gutenberg.org/ebooks/35",
        "private_audition_allowed": True,
        "production_release_approved": False,
        "public_disclosure_required_if_later_approved": "AI voice",
    }
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "TIME_MACHINE_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return payload, passages, artifacts


def execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["schema"] = "earnalism.kokoro.time_machine_representative.v1"
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "TIME_MACHINE_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return code, payload


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = VOICE_FILENAME
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.EXPECTED_SOURCE_SHA256 = EXPECTED_RECONCILIATION_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = EXPECTED_SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(
        str(item["sha256"]) for item in PASSAGE_SPECS
    )
    BASE.EXPECTED_PASSAGE_CHARACTERS = EXPECTED_PASSAGE_CHARACTERS
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.SPEED = SPEED
    BASE.KOKORO_LANG_CODE = KOKORO_LANG_CODE
    BASE.G2P_BRITISH = G2P_BRITISH
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
