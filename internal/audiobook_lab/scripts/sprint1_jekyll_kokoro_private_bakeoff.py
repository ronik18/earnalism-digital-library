#!/usr/bin/env python3
"""Run a private two-voice Kokoro bakeoff for Jekyll and Hyde.

The profile binds four risk-diverse passages to the complete controlled
publication, current public-domain evidence, checksum-pinned local
Kokoro/Whisper artifacts, and the unchanged paid-TTS lock.  It can write only
private WAV/evidence files.  It has no listening, full-title, upload,
publication, browser, or release-gate mutation surface.

Direct front/back cover linkage is still absent from the controlled record.
That does not prevent this zero-provider-cost private audition, but it remains
an explicit hard blocker before any production audiobook can be approved.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("jekyll_kokoro_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Kokoro representative base: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "jekyll-and-hyde"
TITLE = "The Strange Case of Dr. Jekyll and Mr. Hyde"
AUTHOR = "Robert Louis Stevenson"
LANGUAGE = "eng"
EXPECTED_RECONCILIATION_SHA256 = (
    "0e8cc7fb6c18abd38def7c85cc2a8f4907bde5f11db48e36ba7fd9afff7fdc8e"
)
EXPECTED_SOURCE_CHARACTERS = 138_182
EXPECTED_CHAPTER_COUNT = 11
EXPECTED_BOUND_FILE_HASHES = {
    "approval_evidence.json": "ea3ef30e4fc42ad0b6e4c96a20727c2cf9c9e5eeac9a79acc035c9173c21f278",
    "public_book.json": "08e1cc4cace4b82dccdb2b8189e6297717477bce1f1ee271e5f5e126ca8a6019",
    "reader_manifest.json": "04a0b1df4bd25b9e1d554c3e1aa6994b7b44e5c51810392ff350ec3f998a81b6",
    "source_evidence.json": "f9afc2e7e51313207f9ff903219b8ebc62dc8d34fd39ba0f454cff54117aead3",
}
EXPECTED_CHECKSUM_MANIFEST_SHA256 = (
    "92bdd921a927ceb1e81ca9736c31d7f48497c71340ab6d19d4162af463c4f8e3"
)
PASSAGE_SPECS = (
    {
        "passage_id": "opening_character",
        "chapter": "chapter-001.json",
        "risk": "opening_character_exposition_long_sentences_and_dialogue",
        "start": "Mr. Utterson the lawyer was a man of a rugged countenance",
        "end": "“I let my brother go to the devil in his own way.”",
        "characters": 989,
        "sha256": "b491afef3119554f32c9250f5a81446b55bd81a63bf2fecf3b4940da8e4f1994",
    },
    {
        "passage_id": "carew_murder",
        "chapter": "chapter-004.json",
        "risk": "violent_escalation_suspense_pacing_and_restrained_horror",
        "start": "Presently her eye wandered to the other",
        "end": "At the horror of these sights and sounds, the maid fainted.",
        "characters": 915,
        "sha256": "b45aebd6abcc2e730d156ad71d2964eeff8a1f472cc7146ade53575ec386bd8f",
    },
    {
        "passage_id": "lanyon_transformation",
        "chapter": "chapter-010.json",
        "risk": "transformation_horror_short_clauses_and_emotional_outcry",
        "start": "He put the glass to his lips and drank at one gulp.",
        "end": "there stood Henry Jekyll!",
        "characters": 680,
        "sha256": "3bd9b43260be8299d10f73995dd4c5706e39eba3e0844bf88c619bc7373d47ff",
    },
    {
        "passage_id": "final_confession",
        "chapter": "chapter-011.json",
        "risk": "first_person_dread_reflection_questions_and_final_boundary",
        "start": "About a week has passed, and I am now finishing this statement",
        "end": "I bring the life of that unhappy Henry Jekyll to an end.",
        "characters": 1_460,
        "sha256": "fee77d935c85880bed743ddd65949450c5bb5f5528e8a40101d34cf3e2d11e93",
    },
)
EXPECTED_PASSAGE_CHARACTERS = 4_044
ASR_VOCABULARY_PROMPT = (
    "Canonical names and spellings: Mr. Utterson; Cain; Mr. Hyde; Henry Jekyll; "
    "recognise; theatre; reindue; fearstruck. Preserve every complete source "
    "word and the British spelling."
)
ASR_PROMPT_POLICY = {
    str(item["passage_id"]): "canonical_vocabulary_prompt" for item in PASSAGE_SPECS
}
SOURCE_EQUIVALENCE_POLICY = {
    str(item["passage_id"]): () for item in PASSAGE_SPECS
}
VOICE_PROFILES: dict[str, dict[str, Any]] = {
    "bm_george": {
        "profile": "jekyll-bm-george-v1",
        "voice_filename": "voices/bm_george.pt",
        "voice_sha256": "f1bc812213dc59774769e5c80004b13eeb79bd78130b11b2d7f934542dab811b",
        "kokoro_lang_code": "b",
        "g2p_british": True,
        "speed": 0.95,
        "random_seed": 2026072107,
        "pronunciation_overrides": {
            "Utterson": "ˈʌtəsən",
            "Hyde": "hˈaɪd",
            "Jekyll": "dʒˈɛkəl",
            "fearstruck": "fˈɪəstɹʌk",
        },
        "phoneme_hashes": {
            "opening_character": "c4b5329c8ecda3ec2db00fd0b131546f0a1866cbd4849cb4ee70dc040435accc",
            "carew_murder": "d44754a9374f2f6f4590122eac9b97e693426cc67a8912fd1ae806688cb2bf4b",
            "lanyon_transformation": "241ae80b022816cd45e1657485369330d624da4bdcced07095363cfed486831e",
            "final_confession": "83f057519e2bf67c4c416f089a650ea9d468aef6ca696493c1d56bf7f3d1a5c0",
        },
        "expected_attempt_fingerprint": "e10223569eb619615f05c83cc824eca7a247ede7788eba5d78e0fb17fea3ec2f",
    },
    "am_michael": {
        "profile": "jekyll-am-michael-v1",
        "voice_filename": "voices/am_michael.pt",
        "voice_sha256": "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37",
        "kokoro_lang_code": "a",
        "g2p_british": False,
        "speed": 0.95,
        "random_seed": 2026072107,
        "pronunciation_overrides": {
            "Utterson": "ˈʌtɚsən",
            "Hyde": "hˈaɪd",
            "Jekyll": "dʒˈɛkəl",
            "fearstruck": "fˈɪɹstɹʌk",
        },
        "phoneme_hashes": {
            "opening_character": "2d8444e25e110edee31976a72d59ba576e41cc11f3d13c82d24445d94374ad96",
            "carew_murder": "0bfbe3c6da74253dbca31c0884a16252c8256165a0fefb90134b82ba6eae9c83",
            "lanyon_transformation": "b6720e59def35b7ad065b18281e0604959ca38161c256c557a4280b6ec1e2e50",
            "final_confession": "07beae3f45a9c5cc8f94b5569fa63ae301f38e57f1c85d2e0fa7fecc3a76254d",
        },
        "expected_attempt_fingerprint": "d48d3bc8ce9ca01a7ceacea9f9aae806cb9b1cd6f58eb20f15a715230435f881",
    },
}

DEFAULT_ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/artifacts"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_PRIVATE_ROOT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/jekyll-and-hyde"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)

ACTIVE_VOICE = "bm_george"
ACTIVE_PROFILE = VOICE_PROFILES[ACTIVE_VOICE]


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
        checksum_path = base / "checksum_manifest.json"
        _require(
            BASE.sha256_file(checksum_path),
            EXPECTED_CHECKSUM_MANIFEST_SHA256,
            "checksum_manifest.json SHA-256",
        )
        checksum = BASE.read_json(checksum_path)
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
        "cover_url": None,
        "back_cover_url": None,
        "author_death_year": 1894,
        "original_publication_year": 1886,
    }.items():
        _require(book.get(key), expected, f"public_book.{key}")
    _require(approval.get("audiobook_use_approved"), True, "audiobook use approval")
    _require(
        approval.get("audio_public_release"),
        "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "public audio release",
    )
    _require(source_evidence.get("source_url"), "https://www.gutenberg.org/ebooks/43", "source URL")
    _require(
        source_evidence.get("rights_basis"),
        (
            "Author died 1894. Original publication 1886. Public domain in the "
            "United States and under the applicable life-plus-60 term."
        ),
        "rights basis",
    )
    _require(source_evidence.get("reader_facing_boilerplate_removed"), True, "sanitation")

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
        raise BASE.KokoroTitlePilotError("Jekyll reconciliation record is missing")
    for key, expected in {
        "canonical_source_file_count": EXPECTED_CHAPTER_COUNT,
        "canonical_source_sha256": EXPECTED_RECONCILIATION_SHA256,
        "canonical_source_chars": EXPECTED_SOURCE_CHARACTERS,
        "source_reconciliation_status": "ROOT_BACKEND_MATCH",
        "rights_status": "PASS",
        "cover_status": "PASS_GRAPHICAL_RUNTIME_FALLBACK",
        "cover_front_url": None,
        "cover_back_url": None,
        "sanitation_status": "PASS",
        "ready_for_audition": True,
    }.items():
        _require(record.get(key), expected, f"reconciliation.{key}")

    checksum = BASE.read_json(root / "checksum_manifest.json")
    recorded = {
        str(item.get("file")): str(item.get("sha256"))
        for item in checksum.get("files", [])
        if isinstance(item, dict)
    }
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
        _require(
            BASE.sha256_file(chapter_path),
            recorded.get(f"chapters/{chapter_path.name}"),
            f"recorded chapter hash for {chapter_path.name}",
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
        _require(flattened.count(end_marker), 1, f"{spec['passage_id']} end marker count")
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

    overrides = dict(ACTIVE_PROFILE["pronunciation_overrides"])
    g2p = misaki_en.G2P(
        trf=False,
        british=bool(ACTIVE_PROFILE["g2p_british"]),
        fallback=None,
        unk="",
    )
    g2p.lexicon.golds.update(overrides)
    g2p.lexicon.golds.update({key.lower(): value for key, value in overrides.items()})
    reports: list[dict[str, Any]] = []
    expected_hashes = dict(ACTIVE_PROFILE["phoneme_hashes"])
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
            expected_hashes[passage_id],
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
        "contract": "earnalism.kokoro.jekyll_representative.v1",
        "base_contract_fingerprint": _BASE_ATTEMPT_FINGERPRINT(passages),
        "voice": ACTIVE_VOICE,
        "kokoro_lang_code": ACTIVE_PROFILE["kokoro_lang_code"],
        "g2p_british": ACTIVE_PROFILE["g2p_british"],
        "phoneme_hashes": ACTIVE_PROFILE["phoneme_hashes"],
        "g2p_fallback_enabled": False,
        "cover_state": "DIRECT_FRONT_BACK_LINKAGE_MISSING_PRIVATE_ONLY",
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
        "jekyll-and-hyde_release_gate_evidence.json",
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
    _require(
        fingerprint,
        ACTIVE_PROFILE["expected_attempt_fingerprint"],
        "attempt fingerprint",
    )
    payload["schema"] = "earnalism.kokoro.jekyll_representative.v1"
    payload["engine"].update(
        {
            "voice": ACTIVE_VOICE,
            "voice_sha256": ACTIVE_PROFILE["voice_sha256"],
            "kokoro_lang_code": ACTIVE_PROFILE["kokoro_lang_code"],
            "g2p_british": ACTIVE_PROFILE["g2p_british"],
        }
    )
    payload["source"].update(
        {
            "chapter_count": EXPECTED_CHAPTER_COUNT,
            "source_characters": EXPECTED_SOURCE_CHARACTERS,
            "root_backend_bound_files_match": True,
            "bound_file_sha256": EXPECTED_BOUND_FILE_HASHES,
            "checksum_manifest_sha256": EXPECTED_CHECKSUM_MANIFEST_SHA256,
            "front_cover_url": None,
            "back_cover_url": None,
            "cover_status": "PASS_GRAPHICAL_RUNTIME_FALLBACK_PRIVATE_ONLY",
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
            f"{BASE.MODEL_REVISION}/{ACTIVE_PROFILE['voice_filename']}"
        ),
        "controlled_text_public_domain": True,
        "author_death_year": 1894,
        "original_publication_year": 1886,
        "source_rights_url": "https://www.gutenberg.org/ebooks/43",
        "private_audition_allowed": True,
        "production_release_approved": False,
        "public_disclosure_required_if_later_approved": "AI voice",
    }
    blockers = [
        str(item).replace("GIFT_TITLE_SCOPED", "JEKYLL_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    if "FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION" not in blockers:
        blockers.append("FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION")
    payload["blockers_to_release"] = blockers
    return payload, passages, artifacts


def execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["schema"] = "earnalism.kokoro.jekyll_representative.v1"
    blockers = [
        str(item).replace("GIFT_TITLE_SCOPED", "JEKYLL_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    if "FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION" not in blockers:
        blockers.append("FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION")
    payload["blockers_to_release"] = blockers
    return code, payload


def configure_base(voice: str) -> None:
    global ACTIVE_PROFILE, ACTIVE_VOICE
    if voice not in VOICE_PROFILES:
        raise BASE.KokoroTitlePilotError(f"unsupported voice: {voice}")
    ACTIVE_VOICE = voice
    ACTIVE_PROFILE = VOICE_PROFILES[voice]
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = str(ACTIVE_PROFILE["profile"])
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.VOICE = voice
    BASE.VOICE_FILENAME = str(ACTIVE_PROFILE["voice_filename"])
    BASE.VOICE_SHA256 = str(ACTIVE_PROFILE["voice_sha256"])
    BASE.EXPECTED_SOURCE_SHA256 = EXPECTED_RECONCILIATION_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = EXPECTED_SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(
        str(item["sha256"]) for item in PASSAGE_SPECS
    )
    BASE.EXPECTED_PASSAGE_CHARACTERS = EXPECTED_PASSAGE_CHARACTERS
    BASE.PRONUNCIATION_OVERRIDES = dict(ACTIVE_PROFILE["pronunciation_overrides"])
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.RANDOM_SEED = int(ACTIVE_PROFILE["random_seed"])
    BASE.SPEED = float(ACTIVE_PROFILE["speed"])
    BASE.KOKORO_LANG_CODE = str(ACTIVE_PROFILE["kokoro_lang_code"])
    BASE.G2P_BRITISH = bool(ACTIVE_PROFILE["g2p_british"])
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset()
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = {}
    BASE.attempt_fingerprint = attempt_fingerprint
    BASE.ensure_not_repeated = ensure_not_repeated
    BASE.controlled_source = controlled_source
    BASE.preflight = preflight
    BASE.execute = execute


def default_private_dir(voice: str) -> Path:
    return DEFAULT_PRIVATE_ROOT / f"f3ff3571-{voice.replace('_', '-')}-representative-v1"


def default_output(voice: str) -> Path:
    return BASE.ROOT / (
        "internal/audiobook_lab/sprint1_publication/title_runs/"
        f"jekyll-and-hyde_kokoro_{voice}_representative_v1.json"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--voice", choices=sorted(VOICE_PROFILES), required=True)
    parser.add_argument("--asset-root", type=Path, default=BASE.ROOT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--whisper-cache-dir", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--private-output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        configure_base(args.voice)
        private_dir = (args.private_output_dir or default_private_dir(args.voice)).expanduser().resolve()
        output = (args.output or default_output(args.voice)).expanduser().resolve()
        payload, passages, artifacts = preflight(
            asset_root=args.asset_root.expanduser().resolve(),
            slug=SLUG,
            profile=str(ACTIVE_PROFILE["profile"]),
            artifact_dir=args.artifact_dir,
            whisper_cache_dir=args.whisper_cache_dir,
            private_output_dir=private_dir,
            output=output,
            paid_lock=args.paid_lock,
        )
        if args.execute:
            code, payload = execute(
                payload=payload,
                passages=passages,
                artifacts=artifacts,
                private_dir=BASE.assert_private_audio_path(private_dir),
                whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
                paid_lock=args.paid_lock,
            )
        else:
            code = 0
        BASE.atomic_write_json(output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "voice": ACTIVE_VOICE,
                    "output": str(output),
                    "attempt_fingerprint": payload["engine"]["attempt_fingerprint"],
                    "provider_calls": 0,
                    "audio_generated": payload["safety"]["audio_generated"],
                    "publication_performed": False,
                    "blockers_to_release": payload["blockers_to_release"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return int(code)
    except BASE.KokoroTitlePilotError as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure_base(ACTIVE_VOICE)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
