#!/usr/bin/env python3
"""Run one fallback-free Kokoro am_michael pilot for The Call of the Wild."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = SCRIPT_DIR / "sprint1_time_machine_bm_george_private_audition.py"
SPEC = importlib.util.spec_from_file_location("call_wild_profile_base", PROFILE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load representative profile base: {PROFILE_PATH}")
PROFILE_BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE_BASE)
BASE = PROFILE_BASE.BASE


SLUG = "the-call-of-the-wild"
TITLE = "The Call of the Wild"
AUTHOR = "Jack London"
LANGUAGE = "eng"
PROFILE = "call-wild-am-michael-v1"
VOICE = "am_michael"
VOICE_FILENAME = "voices/am_michael.pt"
VOICE_SHA256 = "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37"
WHISPER_SHA256 = BASE.WHISPER_SHA256
KOKORO_LANG_CODE = "a"
G2P_BRITISH = False
EXPECTED_RECONCILIATION_SHA256 = "36bf2714954e352c1c6a5fbbe65af1e77ab622e709e42907cd9451eda0982916"
EXPECTED_SOURCE_CHARACTERS = 177_305
EXPECTED_CHAPTER_COUNT = 7
EXPECTED_FRONT_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779568766/"
    "earnalism/covers/front/cover_32a20edc-5097-4d64-98d0-fb3d29487a9d.png"
)
EXPECTED_BACK_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779568843/"
    "earnalism/covers/back/back_cover_32a20edc-5097-4d64-98d0-fb3d29487a9d.png"
)
EXPECTED_BOUND_FILE_HASHES = {
    "approval_evidence.json": "e4e9e8fe177c17b5a2093d4f380039897cae963d860ea339fbd417ac059c55d9",
    "public_book.json": "163613f919b522eaa37585997eb0f2ac07569e921ab389f832a626c87c1a0b11",
    "source_evidence.json": "336301883a565d6b850abd525597a66ae5a3b7b67bdb3c706a712233f0a47f32",
}
PASSAGE_SPECS = (
    {
        "passage_id": "opening_exposition",
        "chapter": "chapter-001.json",
        "risk": "opening_exposition_places_and_long_sentence_pacing",
        "start": "Buck did not read the newspapers, or he would have known that trouble was brewing",
        "end": "furry coats to protect them from the frost.",
        "characters": 555,
        "sha256": "1791560e493d4ea492e40cca2a7ebb9722b70c1bd282a9853cb12877c5172216",
    },
    {
        "passage_id": "spitz_final_conflict",
        "chapter": "chapter-003.json",
        "risk": "action_escalation_animal_conflict_and_restrained_violence",
        "start": "But Buck possessed a quality that made for greatness—imagination.",
        "end": "the dominant primordial beast who had made his kill and found it good.",
        "characters": 1602,
        "sha256": "11ea4acd69bd769dcbb1ac522aa27f90f47bd900a94fffaab4890279a3af5d6f",
    },
    {
        "passage_id": "thornton_bond",
        "chapter": "chapter-006.json",
        "risk": "restrained_emotion_character_names_and_human_animal_bond",
        "start": "And as Buck understood the oaths to be love words",
        "end": "For a long time after his rescue, Buck did not like Thornton to get out of his sight.",
        "characters": 1171,
        "sha256": "a0f70373151c13d69f99afbec80f83fb548e4b473eb19ad2ab05497c43927567",
    },
    {
        "passage_id": "closing_call",
        "chapter": "chapter-007.json",
        "risk": "fictional_names_reflection_lyricism_and_exact_final_words",
        "start": "Each fall, when the Yeehats follow the movement of the moose",
        "end": "which is the song of the pack.",
        "characters": 1148,
        "sha256": "01835614d16f85410731e48e6a4b11b6fb8f2c75a8cdaa68ba34ab849d09134b",
    },
)
EXPECTED_PASSAGE_CHARACTERS = 4_476
PRONUNCIATION_OVERRIDES = {
    "Puget": "pjˈuːdʒɪt",
    "Diego": "diˈeɪɡoʊ",
    "manœuvred": "mənˈuːvɚd",
    "Nig": "nˈɪɡ",
    "Yeehat": "jˈiːhæt",
    "Yeehats": "jˈiːhæts",
}
EXPECTED_PHONEME_HASHES = {
    "opening_exposition": "c92b6c4507b09b48cde6dd153607f48b66eef6237980ead8fd56193c814d07cf",
    "spitz_final_conflict": "6f202af7cfbf213f748afa8d39c73cb808adcaddb24bf58690f8d748642e53e1",
    "thornton_bond": "4286ec2e74b58747d2d417ee0b3af80f2e184253f34be8ce6aad5abd146a47a1",
    "closing_call": "eeaafe8a0c7b18a658f0c2909c8f3cb911fb86787000bd57a510b2f6e5e6a9a7",
}
ASR_VOCABULARY_PROMPT = (
    "The Call of the Wild by Jack London. Canonical names and spellings: Buck; "
    "John Thornton; Skeet; Nig; Spitz; Yeehats; Puget Sound; San Diego; "
    "borealis; manœuvred. Preserve every complete source word."
)
ASR_PROMPT_POLICY = {
    str(item["passage_id"]): "canonical_vocabulary_prompt" for item in PASSAGE_SPECS
}
SOURCE_EQUIVALENCE_POLICY = {
    str(item["passage_id"]): () for item in PASSAGE_SPECS
}
SPEED = 0.96
RANDOM_SEED = 2026072101
EXPECTED_ATTEMPT_FINGERPRINT = "19e1586592c3d553ea9e7dcd6d2273e894f05869f760a6f072419f7028de4903"

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
    "internal/audiobook_lab/private_runs/kokoro/the-call-of-the-wild/"
    "f3ff3571-am-michael-representative-v1"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_representative_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


def require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BASE.KokoroTitlePilotError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def controlled_source(asset_root: Path, slug: str) -> tuple[Path, list[dict[str, Any]]]:
    require(slug, SLUG, "slug")
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
        require(BASE.sha256_file(root_path), expected_hash, f"{name} SHA-256")
        for base in (root, backend):
            manifest = BASE.read_json(base / "checksum_manifest.json")
            recorded = {
                str(item.get("file")): str(item.get("sha256"))
                for item in manifest.get("files", [])
                if isinstance(item, dict)
            }
            require(recorded.get(name), expected_hash, f"checksum for {name}")

    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "author_death_year": 1916,
        "original_publication_year": 1903,
    }.items():
        require(book.get(key), expected, f"public_book.{key}")
    require(book.get("cover_url"), EXPECTED_FRONT_COVER_URL, "front cover URL")
    require(book.get("back_cover_url"), EXPECTED_BACK_COVER_URL, "back cover URL")
    require(approval.get("audiobook_use_approved"), True, "audiobook use approval")
    require(
        approval.get("audiobook_use_scope"),
        "PRIVATE_SYNTHESIS_AND_QA_ONLY",
        "audiobook use scope",
    )
    require(
        approval.get("audio_public_release"),
        "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "public audio release",
    )
    require(approval.get("audiobook_enabled"), False, "approval audiobook state")
    require(source_evidence.get("author_death_year"), 1916, "author death year")
    require(source_evidence.get("original_publication_year"), 1903, "publication year")
    require(
        source_evidence.get("author_death_year_evidence_url"),
        "https://www.gutenberg.org/ebooks/215",
        "author death evidence URL",
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
        raise BASE.KokoroTitlePilotError("Call of the Wild reconciliation record is missing")
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
        require(record.get(key), expected, f"reconciliation.{key}")

    chapter_paths = sorted((root / "chapters").glob("chapter-*.json"))
    require(len(chapter_paths), EXPECTED_CHAPTER_COUNT, "chapter count")
    contents: list[str] = []
    chapters: dict[str, dict[str, Any]] = {}
    for chapter_path in chapter_paths:
        backend_path = backend / "chapters" / chapter_path.name
        if chapter_path.read_bytes() != backend_path.read_bytes():
            raise BASE.KokoroTitlePilotError(f"root/backend chapter mismatch: {chapter_path.name}")
        chapter = BASE.read_json(chapter_path)
        require(chapter.get("processing_status"), "ready", f"{chapter_path.name} status")
        require(chapter.get("processing_warnings"), [], f"{chapter_path.name} warnings")
        contents.append(str(chapter.get("content") or ""))
        chapters[chapter_path.name] = chapter
    manuscript = "\n\n".join(contents) + "\n"
    require(len(manuscript), EXPECTED_SOURCE_CHARACTERS, "source characters")
    require(BASE.sha256_text(manuscript), EXPECTED_RECONCILIATION_SHA256, "source SHA-256")

    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        flattened = re.sub(
            r"\s+", " ", str(chapters[str(spec["chapter"])].get("content") or "")
        ).strip()
        start_marker = str(spec["start"])
        end_marker = str(spec["end"])
        require(flattened.count(start_marker), 1, f"{spec['passage_id']} start marker count")
        start = flattened.index(start_marker)
        end = flattened.index(end_marker, start) + len(end_marker)
        text = flattened[start:end]
        require(len(text), spec["characters"], f"{spec['passage_id']} characters")
        require(BASE.sha256_text(text), spec["sha256"], f"{spec['passage_id']} SHA-256")
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
    require(sum(int(item["characters"]) for item in passages), EXPECTED_PASSAGE_CHARACTERS, "passage character total")
    return root / "chapters", passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.kokoro.call_wild_representative.v1",
        "base_contract_fingerprint": PROFILE_BASE._BASE_ATTEMPT_FINGERPRINT(passages),
        "kokoro_lang_code": KOKORO_LANG_CODE,
        "g2p_british": G2P_BRITISH,
        "phoneme_hashes": EXPECTED_PHONEME_HASHES,
        "g2p_fallback_enabled": False,
    }
    return BASE.sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    PROFILE_BASE._BASE_ENSURE_NOT_REPEATED(fingerprint, output)
    evidence_paths = [
        BASE.ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
        BASE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
        BASE.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ]
    evidence_paths.extend(
        sorted((BASE.ROOT / "internal/audiobook_lab/sprint1_publication/title_runs").glob("*.json"))
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
    payload, passages, artifacts = PROFILE_BASE._BASE_PREFLIGHT(**kwargs)
    fingerprint = str((payload.get("engine") or {}).get("attempt_fingerprint") or "")
    require(fingerprint, EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    payload["schema"] = "earnalism.kokoro.call_wild_representative.v1"
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
    payload["g2p_preflight_evidence"] = PROFILE_BASE.g2p_preflight(passages)
    payload["rights"] = {
        "model_and_voicepack_license": "Apache-2.0",
        "model_card_url": f"https://huggingface.co/hexgrad/Kokoro-82M/blob/{BASE.MODEL_REVISION}/README.md",
        "model_license_url": f"https://huggingface.co/hexgrad/Kokoro-82M/blob/{BASE.MODEL_REVISION}/COPYING",
        "voice_file_url": f"https://huggingface.co/hexgrad/Kokoro-82M/blob/{BASE.MODEL_REVISION}/{VOICE_FILENAME}",
        "controlled_text_public_domain": True,
        "author_death_year": 1916,
        "author_death_year_evidence_url": "https://www.gutenberg.org/ebooks/215",
        "original_publication_year": 1903,
        "original_publication_evidence_url": "https://www.gutenberg.org/ebooks/215",
        "private_audition_allowed": True,
        "production_release_approved": False,
        "public_disclosure_required_if_later_approved": "AI voice",
    }
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "CALL_WILD_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return payload, passages, artifacts


def execute(**kwargs: Any):
    code, payload = PROFILE_BASE._BASE_EXECUTE(**kwargs)
    payload["schema"] = "earnalism.kokoro.call_wild_representative.v1"
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "CALL_WILD_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return code, payload


def configure() -> None:
    replacements = {
        "SLUG": SLUG,
        "TITLE": TITLE,
        "AUTHOR": AUTHOR,
        "LANGUAGE": LANGUAGE,
        "PROFILE": PROFILE,
        "VOICE": VOICE,
        "VOICE_FILENAME": VOICE_FILENAME,
        "VOICE_SHA256": VOICE_SHA256,
        "KOKORO_LANG_CODE": KOKORO_LANG_CODE,
        "G2P_BRITISH": G2P_BRITISH,
        "EXPECTED_RECONCILIATION_SHA256": EXPECTED_RECONCILIATION_SHA256,
        "EXPECTED_SOURCE_CHARACTERS": EXPECTED_SOURCE_CHARACTERS,
        "EXPECTED_CHAPTER_COUNT": EXPECTED_CHAPTER_COUNT,
        "EXPECTED_FRONT_COVER_URL": EXPECTED_FRONT_COVER_URL,
        "EXPECTED_BACK_COVER_URL": EXPECTED_BACK_COVER_URL,
        "EXPECTED_BOUND_FILE_HASHES": EXPECTED_BOUND_FILE_HASHES,
        "PASSAGE_SPECS": PASSAGE_SPECS,
        "EXPECTED_PASSAGE_CHARACTERS": EXPECTED_PASSAGE_CHARACTERS,
        "PRONUNCIATION_OVERRIDES": PRONUNCIATION_OVERRIDES,
        "EXPECTED_PHONEME_HASHES": EXPECTED_PHONEME_HASHES,
        "ASR_VOCABULARY_PROMPT": ASR_VOCABULARY_PROMPT,
        "ASR_PROMPT_POLICY": ASR_PROMPT_POLICY,
        "SOURCE_EQUIVALENCE_POLICY": SOURCE_EQUIVALENCE_POLICY,
        "SPEED": SPEED,
        "RANDOM_SEED": RANDOM_SEED,
        "EXPECTED_ATTEMPT_FINGERPRINT": EXPECTED_ATTEMPT_FINGERPRINT,
        "DEFAULT_ARTIFACT_DIR": DEFAULT_ARTIFACT_DIR,
        "DEFAULT_WHISPER_CACHE": DEFAULT_WHISPER_CACHE,
        "DEFAULT_PRIVATE_DIR": DEFAULT_PRIVATE_DIR,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "controlled_source": controlled_source,
        "attempt_fingerprint": attempt_fingerprint,
        "ensure_not_repeated": ensure_not_repeated,
        "preflight": preflight,
        "execute": execute,
    }
    for name, value in replacements.items():
        setattr(PROFILE_BASE, name, value)
    PROFILE_BASE.configure_base()


def main(argv: Sequence[str] | None = None) -> int:
    configure()
    return PROFILE_BASE.main(argv)


configure()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
