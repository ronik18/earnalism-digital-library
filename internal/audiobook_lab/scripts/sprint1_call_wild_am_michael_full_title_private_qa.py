#!/usr/bin/env python3
"""Prepare or run one private Call of the Wild full-title objective pilot.

The runner adapts the proven local Kokoro full-title pipeline to the exact
seven-chapter controlled manuscript and the passing ``am_michael``
representative evidence. It uses deterministic sentence-bound sections,
fallback-free G2P, audio-derived ASR, and measured section sync. It cannot run
listening QA, upload, publish, enable audio, or mutate release truth.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load(
    "call_wild_full_title_core",
    SCRIPT_DIR / "sprint1_gift_kokoro_full_title_private_qa.py",
)
PROFILE = _load(
    "call_wild_full_title_profile",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_private_audition.py",
)
TARGET = _load(
    "call_wild_full_title_targeted_profile",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_targeted_resynthesis.py",
)

ROOT = PROFILE.BASE.ROOT
SLUG = PROFILE.SLUG
TITLE = PROFILE.TITLE
AUTHOR = PROFILE.AUTHOR
LANGUAGE = PROFILE.LANGUAGE
FULL_PROFILE = "call-wild-am-michael-full-v1"
SCHEMA = "earnalism.call_wild_kokoro_am_michael_full_title_private_qa.v1"
FULL_SOURCE_SHA256 = PROFILE.EXPECTED_RECONCILIATION_SHA256
FULL_SOURCE_CHARACTERS = PROFILE.EXPECTED_SOURCE_CHARACTERS
CANONICAL_NORMALIZED_SOURCE_SHA256 = (
    "7f665d7e8efd85643cd1f9783b3a5c3842f0284826afe94bb41a54d50dd5a320"
)
CANONICAL_NORMALIZED_SOURCE_CHARACTERS = 174_635
PREPARED_NORMALIZED_SOURCE_SHA256 = (
    "737b712b90a28eaa9489b26bac56b66c1de89bfaf99248abe36dce96ed27763c"
)
PREPARED_NORMALIZED_SOURCE_CHARACTERS = 174_638
PREPARED_NORMALIZED_SOURCE_WORDS = 31_714
EXPECTED_SECTION_COUNT = 280
SOURCE_RIGHTS_BASIS = (
    "Jack London died 1916; The Call of the Wild was first published 1903; "
    "controlled source evidence is public-domain approved."
)
ACCEPTANCE_POLICY_SHA256 = (
    "3f5836e911ede62119523aa2395414a946cb623f545b0d7941b8c2a10d33a0a5"
)
REPRESENTATIVE_EVIDENCE_SHA256 = (
    "166a3c412d8e71f12e922237e4510d462a041ea7c8d6049c984dcecb3ab24700"
)
REPRESENTATIVE_LISTENING_SHA256 = (
    "c9311b07e7c23638f5f6df1f4f73b5a23ea9d5604e908971e6a678224758d709"
)
REPRESENTATIVE_ATTEMPT_FINGERPRINT = TARGET.EXPECTED_ATTEMPT_FINGERPRINT
REPRESENTATIVE_LISTENING_FINGERPRINT = (
    "db726a1e0309e6cd2febda822431af827eb52f9d1a27f62306105a620b1f0ff6"
)
REPRESENTATIVE_ASR_FINGERPRINT = (
    "202233ae6913aefb18da02d8cce108edfd4bf3038955c146ec5d20aba0c60a46"
)

MODEL_REPO = PROFILE.BASE.MODEL_REPO
MODEL_REVISION = PROFILE.BASE.MODEL_REVISION
MODEL_SHA256 = PROFILE.BASE.MODEL_SHA256
CONFIG_SHA256 = PROFILE.BASE.CONFIG_SHA256
VOICE = PROFILE.VOICE
VOICE_SHA256 = PROFILE.VOICE_SHA256
SAMPLE_RATE = PROFILE.BASE.SAMPLE_RATE
SPEED = TARGET.SPEED
RANDOM_SEED = TARGET.RANDOM_SEED
WHISPER_MODEL = PROFILE.BASE.WHISPER_MODEL
WHISPER_SHA256 = PROFILE.BASE.WHISPER_SHA256
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
SYNC_SCORE_MIN = 9.7
LISTENING_SCORE_MIN = 9.3
LISTENING_CONFIDENCE_MIN = 0.90
PRONUNCIATION_OVERRIDES = {
    **TARGET.PRONUNCIATION_OVERRIDES,
    "Bennett": "bˈɛnɪt",
    "Billee": "bˈɪli",
    "Cassiar": "kˈæsiˌɑɹ",
    "Cañon": "kˈænjən",
    "Chilcoot": "ʧˈɪlkut",
    "Chook": "ʧˈʊk",
    "Clara": "klˈɛɹə",
    "Dyea": "dIˈiə",
    "Eldorado": "ˌɛldəɹˈɑdO",
    "François": "fɹænswˈɑ",
    "Heem": "hˈim",
    "Hootalinqua": "hˌutəlˈɪŋkwə",
    "Koona": "kˈunə",
    "Le": "lə",
    "Lissen": "lˈɪsən",
    "Manuel": "mænwˈɛl",
    "Matthewson": "mˈæθjusən",
    "Mebbe": "mˈAbi",
    "Nevaire": "nɛvˈɛɹ",
    "O'Brien": "ObɹˈIən",
    "Pelly": "pˈɛli",
    "Perrault": "pəɹˈO",
    "Py": "bˈI",
    "Sacredam": "sækɹˈA dˈæm",
    "Santa": "sˈæntə",
    "Shep": "ʃˈɛp",
    "Skaguay": "skˈæɡwA",
    "Spitzbergen": "spˈɪtsbəɹɡən",
    "St.": "sˈAnt",
    "Sunland": "sˈʌnlənd",
    "Tagish": "tˈæɡɪʃ",
    "Tahkeena": "tˌɑkˈinə",
    "Tanana": "tænˈɑnə",
    "Teek": "tˈik",
    "T'ree": "tɹˈi",
    "Ysabel": "ˌizəbˈɛl",
    "anyt'ing": "ˈɛniTɪŋ",
    "baggageman": "bˈæɡɪʤmən",
    "cagelike": "kˈAʤlˌIk",
    "complied": "kəmplˈId",
    "de": "də",
    "decivilization": "dɪsˌɪvɪlɪzˈAʃən",
    "defied": "dᵻfˈId",
    "denied": "dᵻnˈId",
    "dollair": "dˈɑləɹ",
    "feex": "fˈɪks",
    "ferine": "fˈɛɹIn",
    "fiftypound": "fˈɪfti pˈWnd",
    "fivescore": "fˈIvskˌɔɹ",
    "forevalued": "fˈɔɹvæljˌud",
    "frien": "fɹˈɛnd",
    "gayety": "ɡˈIəTi",
    "goldseekers": "ɡˈOld sˈikəɹz",
    "heem": "hˈim",
    "hydrophoby": "hˌIdɹəfˈObi",
    "lak": "lˈIk",
    "lionlike": "lˈIənlˌIk",
    "luringly": "lˈʊɹɪŋli",
    "manœuvre": "mənˈuvəɹ",
    "mebbe": "mˈAbi",
    "mek": "mˈAk",
    "mineself": "mIsˈɛlf",
    "moch": "mˈʌʧ",
    "multiplied": "mˌʌltɪplˈId",
    "nevaire": "nɛvˈɛɹ",
    "outa": "ˈWTə",
    "plentee": "plˈɛnti",
    "poorer": "pˈʊɹəɹ",
    "queek": "kwˈɪk",
    "resiliency": "ɹᵻsˈɪliənsi",
    "sacredam": "sækɹˈA dˈæm",
    "spik": "spˈik",
    "stoutest": "stˈWTɪst",
    "stuffin": "stˈʌfɪŋ",
    "tich": "tˈiʧ",
    "t'eef": "tˈif",
    "t'ink": "tˈɪŋk",
    "t'ousan": "tˈWzᵻn",
    "t'ousand": "tˈWzᵻnd",
    "uncontent": "ˌʌnkəntˈɛnt",
    "unforgetable": "ˌʌnfəɹɡˈɛTəbᵻl",
    "unpursued": "ˌʌnpəɹsˈud",
    "weazened": "wˈizənd",
    "withheld": "wɪθhˈɛld",
    "wolflike": "wˈʊlflˌIk",
    "wolverenes": "wˌʊlvəɹˈinz",
}
CANONICAL_PROPER_NAMES = (
    "Buck",
    "Thornton",
    "Skeet",
    "Nig",
    "Spitz",
    "Yeehats",
    "Puget",
    "Diego",
)
G2P_SETTINGS = {
    "language_code": "a",
    "transformer": False,
    "british": False,
    "fallback": None,
    "unknown_token": "",
}
ASR_SETTINGS = {
    "language": "en",
    "task": "transcribe",
    "fp16": False,
    "temperature": 0,
    "condition_on_previous_text": False,
    "initial_prompt": PROFILE.ASR_VOCABULARY_PROMPT,
    "word_timestamps": True,
}
SOURCE_EQUIVALENCE_POLICY = {
    "tide-water/tidewater": "tidewater",
    "fore-leg/foreleg": "foreleg",
    "manœuvred/manoeuvred/maneuvered": "maneuvered",
    "moose-hide/moosehide": "moosehide",
    "mould/mold": "mold",
    "St. Bernard/Saint Bernard": "saint bernard",
    "Spitz/spits": "spitz",
    "climes/climbs": "climes",
}
SOURCE_PREPARATIONS = (
    ("had found a yellow metal, and because", "had found a yellow metal—and because"),
    ("this feigned bite for a caress", "this feigned bite, for ... a caress"),
    (
        "gloriously coated wolf, like, and yet unlike",
        "gloriously coated wolf—like, and yet unlike",
    ),
    (
        "long winter nights come on and the wolves",
        "long winter nights come on—and the wolves",
    ),
)
APOSTROPHE_NORMALIZATION = {
    "source": "’",
    "prepared": "'",
    "expected_count": 272,
    "reason": "normalize punctuation code point for deterministic G2P without changing lexical tokens",
}
EXPECTED_FULL_TITLE_FINGERPRINT = (
    "b1eaee2ea9d5dbcdf2fd7fe643a3d23a2c0d31c5445795fc0768ae5e1162ae20"
)

DEFAULT_REPRESENTATIVE_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_targeted_asr_projection_v1.json"
)
DEFAULT_LISTENING_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_listening_qa_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_full_title_private_preflight_v1.json"
)
DEFAULT_PRIVATE_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-call-of-the-wild/"
    "f3ff3571-am-michael-full-v1"
)
DEFAULT_ARTIFACT_DIR = PROFILE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/the-call-of-the-wild_release_gate_evidence.json",
)

CallWildFullTitleError = BASE.GiftFullTitleError
_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute
_BASE_FINGERPRINT_PAYLOAD = BASE.fingerprint_payload


def prepare_manuscript(canonical: str) -> tuple[str, list[dict[str, str]]]:
    prepared = canonical
    evidence: list[dict[str, str]] = []
    for source, replacement in SOURCE_PREPARATIONS:
        if prepared.count(source) != 1:
            raise CallWildFullTitleError(f"source preparation marker changed: {source}")
        prepared = prepared.replace(source, replacement, 1)
        evidence.append(
            {
                "source": source,
                "prepared": replacement,
                "reason": "representative-proven punctuation preparation with identical lexical tokens",
            }
        )
    apostrophe_count = prepared.count(APOSTROPHE_NORMALIZATION["source"])
    if apostrophe_count != APOSTROPHE_NORMALIZATION["expected_count"]:
        raise CallWildFullTitleError("curly apostrophe count changed")
    prepared = prepared.replace(
        APOSTROPHE_NORMALIZATION["source"],
        APOSTROPHE_NORMALIZATION["prepared"],
    )
    evidence.append(
        {
            "source": APOSTROPHE_NORMALIZATION["source"],
            "prepared": APOSTROPHE_NORMALIZATION["prepared"],
            "reason": APOSTROPHE_NORMALIZATION["reason"],
            "occurrences": str(apostrophe_count),
        }
    )
    if PROFILE.BASE.lexical_tokens(canonical) != PROFILE.BASE.lexical_tokens(prepared):
        raise CallWildFullTitleError("full-title preparation changed lexical content")
    BASE.require(
        BASE.sha256_text(prepared) == PREPARED_NORMALIZED_SOURCE_SHA256,
        "prepared normalized source hash changed",
    )
    return prepared, evidence


def sentence_bound_sections(prepared: str) -> list[dict[str, Any]]:
    sections: list[list[str]] = []
    current: list[str] = []
    for word in prepared.split(" "):
        current.append(word)
        if len(current) >= 100 and re.search(r"[.!?][\"”’']*$", word):
            sections.append(current)
            current = []
    if current:
        if sections and len(current) < 50:
            sections[-1].extend(current)
        else:
            sections.append(current)
    BASE.require(len(sections) == EXPECTED_SECTION_COUNT, "section count changed")
    records: list[dict[str, Any]] = []
    for index, words in enumerate(sections, 1):
        text = " ".join(words)
        BASE.require(
            bool(re.search(r"[.!?][\"”’']*$", words[-1])),
            f"section-{index:03d} is not sentence-bound",
        )
        records.append(
            {
                "passage_id": f"section-{index:03d}",
                "section_index": index,
                "text": text,
                "text_sha256": BASE.sha256_text(text),
                "characters": len(text),
                "word_count": len(words),
            }
        )
    BASE.require(
        " ".join(item["text"] for item in records) == prepared,
        "sections are not a lossless prepared-source reconstruction",
    )
    return records


def controlled_source(
    asset_root: Path,
) -> tuple[Path, str, list[dict[str, Any]]]:
    PROFILE.controlled_source(asset_root, SLUG)
    publication = asset_root / "data/controlled_publications" / SLUG
    backend = asset_root / "backend/data/controlled_publications" / SLUG
    chapter_paths = sorted((publication / "chapters").glob("chapter-*.json"))
    BASE.require(len(chapter_paths) == PROFILE.EXPECTED_CHAPTER_COUNT, "chapter count changed")
    contents: list[str] = []
    for chapter_path in chapter_paths:
        backend_path = backend / "chapters" / chapter_path.name
        BASE.require(chapter_path.read_bytes() == backend_path.read_bytes(), "root/backend chapter mismatch")
        chapter = BASE.read_json(chapter_path)
        BASE.require(chapter.get("processing_status") == "ready", "chapter is not ready")
        BASE.require(chapter.get("processing_warnings") == [], "chapter warnings changed")
        contents.append(str(chapter.get("content") or ""))
    manuscript = "\n\n".join(contents) + "\n"
    BASE.require(len(manuscript) == FULL_SOURCE_CHARACTERS, "full source length changed")
    BASE.require(BASE.sha256_text(manuscript) == FULL_SOURCE_SHA256, "full source hash changed")
    canonical = re.sub(r"\s+", " ", manuscript).strip()
    BASE.require(
        len(canonical) == CANONICAL_NORMALIZED_SOURCE_CHARACTERS,
        "canonical normalized length changed",
    )
    BASE.require(
        BASE.sha256_text(canonical) == CANONICAL_NORMALIZED_SOURCE_SHA256,
        "canonical normalized hash changed",
    )
    prepared, transformations = prepare_manuscript(canonical)
    BASE.require(len(prepared) == PREPARED_NORMALIZED_SOURCE_CHARACTERS, "prepared length changed")
    BASE.require(len(prepared.split(" ")) == PREPARED_NORMALIZED_SOURCE_WORDS, "prepared word count changed")
    sections = sentence_bound_sections(prepared)
    BASE.SECTION_WORD_COUNTS = tuple(item["word_count"] for item in sections)
    BASE.SECTION_HASHES = tuple(item["text_sha256"] for item in sections)
    BASE.CALL_WILD_SOURCE_PREPARATION_EVIDENCE = transformations
    return publication / "chapters", prepared, sections


def validate_predecessor_evidence(
    representative_path: Path, listening_path: Path
) -> dict[str, Any]:
    BASE.verify_file(
        representative_path, REPRESENTATIVE_EVIDENCE_SHA256, "representative evidence"
    )
    BASE.verify_file(
        listening_path, REPRESENTATIVE_LISTENING_SHA256, "representative listening evidence"
    )
    audition = BASE.read_json(representative_path)
    listening = BASE.read_json(listening_path)
    BASE.require((audition.get("scope") or {}).get("slug") == SLUG, "representative slug changed")
    BASE.require(
        (audition.get("source") or {}).get("complete_source_sha256") == FULL_SOURCE_SHA256,
        "representative source changed",
    )
    BASE.require(
        audition.get("attempt_fingerprint") == REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "representative attempt fingerprint changed",
    )
    BASE.require(
        audition.get("projection_fingerprint") == REPRESENTATIVE_ASR_FINGERPRINT,
        "representative projection fingerprint changed",
    )
    reports = audition.get("combined_representative_reports") or []
    BASE.require(
        len(reports) == 4 and all(item.get("pass") is True for item in reports),
        "representative objective reports are not all exact",
    )
    BASE.require(
        all(float(item.get("score") or 0) == 10.0 for item in reports),
        "representative objective score changed",
    )
    BASE.require(
        listening.get("sample_fingerprint") == REPRESENTATIVE_LISTENING_FINGERPRINT,
        "listening fingerprint changed",
    )
    gate = listening.get("listening_gate") or {}
    minimums = gate.get("minimum_scores") or {}
    BASE.require(gate.get("platform_screen_pass") is True, "platform screen did not pass")
    BASE.require(
        float(minimums.get("overall_listening_score") or 0) >= LISTENING_SCORE_MIN,
        "representative listening below English premium floor",
    )
    BASE.require(
        float(minimums.get("confidence_score") or 0) >= LISTENING_CONFIDENCE_MIN,
        "representative confidence below floor",
    )
    BASE.require(gate.get("fatal_flags") == [], "representative fatal flags present")
    BASE.require(gate.get("sample_blockers") == [], "representative sample blockers present")
    policy_path = ROOT / "internal/earnalism_intelligence/audiobook_acceptance_policy.json"
    BASE.verify_file(policy_path, ACCEPTANCE_POLICY_SHA256, "acceptance policy")
    policy = BASE.read_json(policy_path)
    premium = (policy.get("listening_tiers") or {}).get("PREMIUM_AUDIO_APPROVED") or {}
    BASE.require(float(premium.get("overall_listening_score_min") or 0) == 9.3, "English premium floor changed")
    BASE.require(float(premium.get("confidence_score_min") or 0) == 0.9, "English confidence floor changed")
    BASE.require(premium.get("fatal_flags_required_false") is True, "fatal flag policy changed")
    return {
        "representative_evidence_path": str(representative_path),
        "representative_evidence_sha256": REPRESENTATIVE_EVIDENCE_SHA256,
        "representative_attempt_fingerprint": REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "representative_asr_fingerprint": REPRESENTATIVE_ASR_FINGERPRINT,
        "listening_evidence_path": str(listening_path),
        "listening_evidence_sha256": REPRESENTATIVE_LISTENING_SHA256,
        "listening_fingerprint": REPRESENTATIVE_LISTENING_FINGERPRINT,
        "acceptance_policy_sha256": ACCEPTANCE_POLICY_SHA256,
        "acceptance_tier": "PREMIUM_AUDIO_APPROVED",
        "platform_screen_pass": True,
        "minimum_overall_listening_score": minimums["overall_listening_score"],
        "minimum_confidence_score": minimums["confidence_score"],
        "fatal_flags": [],
        "owner_exact_10_observed": gate.get("owner_exact_10_pass") is True,
        "exact_10_is_private_full_title_gate": False,
        "authorization_basis": "active English premium 9.3/0.90/no-fatal tier; exact 10 is aspirational",
    }


def canonicalize_equivalences(text: str) -> tuple[str, list[dict[str, Any]]]:
    value = text
    applied: list[dict[str, Any]] = []
    rules = (
        (r"\btide[- ]?water\b", "tidewater", "tide-water/tidewater"),
        (r"\bfore[- ]?leg\b", "foreleg", "fore-leg/foreleg"),
        (r"\bman(?:œ|oe|eu)uvred\b|\bmaneuvered\b", "maneuvered", "manœuvred/maneuvered"),
        (r"\bmoose[- ]?hide\b", "moosehide", "moose-hide/moosehide"),
        (r"\bmould\b|\bmold\b", "mold", "mould/mold"),
        (r"\bSt\.? Bernard\b|\bSaint Bernard\b", "saint bernard", "St. Bernard/Saint Bernard"),
        (r"\bSpitz\b|\bspits\b", "spitz", "Spitz/spits"),
        (r"\bclimes\b|\bclimbs\b", "climes", "climes/climbs"),
    )
    for pattern, replacement, label in rules:
        value, count = re.subn(pattern, replacement, value, flags=re.IGNORECASE)
        if count:
            applied.append(
                {"equivalence": label, "replacement": replacement, "match_count": count}
            )
    return value, applied


def fingerprint_payload(sections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = _BASE_FINGERPRINT_PAYLOAD(sections)
    payload.update(
        {
            "canonical_normalized_source_sha256": CANONICAL_NORMALIZED_SOURCE_SHA256,
            "prepared_normalized_source_sha256": PREPARED_NORMALIZED_SOURCE_SHA256,
            "source_preparations": SOURCE_PREPARATIONS,
            "apostrophe_normalization": APOSTROPHE_NORMALIZATION,
            "section_builder_sha256": BASE.sha256_text(inspect.getsource(sentence_bound_sections)),
            "acceptance_policy_sha256": ACCEPTANCE_POLICY_SHA256,
        }
    )
    return payload


def preflight(**kwargs: Any):
    payload, sections, artifacts = _BASE_PREFLIGHT(**kwargs)
    observed = str((payload.get("engine") or {}).get("attempt_fingerprint") or "")
    if EXPECTED_FULL_TITLE_FINGERPRINT != "TO_BE_BOUND":
        BASE.require(observed == EXPECTED_FULL_TITLE_FINGERPRINT, "full-title fingerprint changed")
    payload["schema"] = SCHEMA
    payload["scope"].update({"profile": FULL_PROFILE, "section_count": EXPECTED_SECTION_COUNT})
    payload["source"].update(
        {
            "canonical_normalized_source_sha256": CANONICAL_NORMALIZED_SOURCE_SHA256,
            "canonical_normalized_characters": CANONICAL_NORMALIZED_SOURCE_CHARACTERS,
            "prepared_normalized_source_sha256": PREPARED_NORMALIZED_SOURCE_SHA256,
            "prepared_normalized_characters": PREPARED_NORMALIZED_SOURCE_CHARACTERS,
            "all_prepared_lexical_tokens_unchanged": True,
            "preparations": BASE.CALL_WILD_SOURCE_PREPARATION_EVIDENCE,
            "root_backend_bound_files_match": True,
            "bound_file_sha256": PROFILE.EXPECTED_BOUND_FILE_HASHES,
        }
    )
    payload["catalog_gate"] = {
        "status": "PASS_READER_LIVE_AUDIO_HIDDEN",
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "reader_enabled": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "controlled_publication_root_backend_match": True,
    }
    payload["cover_gate"] = {
        "status": "PASS_DIRECT_FRONT_BACK",
        "front_cover_url": PROFILE.EXPECTED_FRONT_COVER_URL,
        "back_cover_url": PROFILE.EXPECTED_BACK_COVER_URL,
    }
    payload["rights"] = {
        "text_rights_status": "PASS_PUBLIC_DOMAIN_TIER_A",
        "rights_basis": SOURCE_RIGHTS_BASIS,
        "source_evidence_path": str(
            ROOT / "data/controlled_publications" / SLUG / "source_evidence.json"
        ),
        "source_evidence_sha256": PROFILE.EXPECTED_BOUND_FILE_HASHES[
            "source_evidence.json"
        ],
        "approval_evidence_path": str(
            ROOT / "data/controlled_publications" / SLUG / "approval_evidence.json"
        ),
        "approval_evidence_sha256": PROFILE.EXPECTED_BOUND_FILE_HASHES[
            "approval_evidence.json"
        ],
        "model_and_voicepack_license": "Apache-2.0",
        "model_card_url": (
            f"https://huggingface.co/{MODEL_REPO}/blob/{MODEL_REVISION}/README.md"
        ),
        "model_license_url": (
            f"https://huggingface.co/{MODEL_REPO}/blob/{MODEL_REVISION}/COPYING"
        ),
        "voice_file_url": (
            f"https://huggingface.co/{MODEL_REPO}/blob/{MODEL_REVISION}/"
            f"{PROFILE.VOICE_FILENAME}"
        ),
        "private_full_title_allowed": True,
        "call_wild_title_scoped_publication_risk_acceptance_bound": False,
        "production_release_approved": False,
        "public_disclosure_required_if_later_approved": "Narration: AI voice",
    }
    estimate = round(38.75 * PREPARED_NORMALIZED_SOURCE_CHARACTERS / 554, 3)
    pcm_bytes = int(estimate * SAMPLE_RATE * 2 + 44)
    payload["cost_and_capacity"].update(
        {
            "estimated_duration_seconds": estimate,
            "estimated_pcm_wav_bytes": pcm_bytes,
            "estimated_pcm_wav_mib": round(pcm_bytes / 1_048_576, 3),
            "estimated_local_runtime_minutes": {
                "apple_silicon_expected": [120, 360],
                "cpu_fallback_expected": [240, 720],
            },
        }
    )
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "CALL_WILD_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    return payload, sections, artifacts


def execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["schema"] = SCHEMA
    payload["blockers_to_release"] = [
        str(item).replace("GIFT_TITLE_SCOPED", "CALL_WILD_TITLE_SCOPED")
        for item in payload["blockers_to_release"]
    ]
    BASE.write_json(Path(kwargs["output"]), payload)
    return code, payload


def configure_base() -> None:
    bindings = {
        "ROOT": ROOT,
        "representative": PROFILE.BASE,
        "SLUG": SLUG,
        "TITLE": TITLE,
        "AUTHOR": AUTHOR,
        "LANGUAGE": LANGUAGE,
        "PROFILE": FULL_PROFILE,
        "SCHEMA": SCHEMA,
        "FULL_SOURCE_SHA256": FULL_SOURCE_SHA256,
        "FULL_SOURCE_CHARACTERS": FULL_SOURCE_CHARACTERS,
        "NORMALIZED_SOURCE_SHA256": PREPARED_NORMALIZED_SOURCE_SHA256,
        "NORMALIZED_SOURCE_CHARACTERS": PREPARED_NORMALIZED_SOURCE_CHARACTERS,
        "NORMALIZED_SOURCE_WORDS": PREPARED_NORMALIZED_SOURCE_WORDS,
        "SOURCE_RIGHTS_BASIS": SOURCE_RIGHTS_BASIS,
        "REPRESENTATIVE_EVIDENCE_SHA256": REPRESENTATIVE_EVIDENCE_SHA256,
        "REPRESENTATIVE_LISTENING_SHA256": REPRESENTATIVE_LISTENING_SHA256,
        "REPRESENTATIVE_ATTEMPT_FINGERPRINT": REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "REPRESENTATIVE_LISTENING_FINGERPRINT": REPRESENTATIVE_LISTENING_FINGERPRINT,
        "REPRESENTATIVE_ASR_FINGERPRINT": REPRESENTATIVE_ASR_FINGERPRINT,
        "MODEL_REPO": MODEL_REPO,
        "MODEL_REVISION": MODEL_REVISION,
        "MODEL_SHA256": MODEL_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "VOICE": VOICE,
        "VOICE_SHA256": VOICE_SHA256,
        "SAMPLE_RATE": SAMPLE_RATE,
        "SPEED": SPEED,
        "RANDOM_SEED": RANDOM_SEED,
        "WHISPER_MODEL": WHISPER_MODEL,
        "WHISPER_SHA256": WHISPER_SHA256,
        "ASR_SCORE_MIN": ASR_SCORE_MIN,
        "ASR_COVERAGE_MIN": ASR_COVERAGE_MIN,
        "SYNC_SCORE_MIN": SYNC_SCORE_MIN,
        "LISTENING_SCORE_MIN": LISTENING_SCORE_MIN,
        "LISTENING_CONFIDENCE_MIN": LISTENING_CONFIDENCE_MIN,
        "PRONUNCIATION_OVERRIDES": PRONUNCIATION_OVERRIDES,
        "CANONICAL_PROPER_NAMES": CANONICAL_PROPER_NAMES,
        "G2P_SETTINGS": G2P_SETTINGS,
        "ASR_SETTINGS": ASR_SETTINGS,
        "SOURCE_EQUIVALENCE_POLICY": SOURCE_EQUIVALENCE_POLICY,
        "DEFAULT_REPRESENTATIVE_EVIDENCE": DEFAULT_REPRESENTATIVE_EVIDENCE,
        "DEFAULT_LISTENING_EVIDENCE": DEFAULT_LISTENING_EVIDENCE,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_PRIVATE_DIR": DEFAULT_PRIVATE_DIR,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "NO_REPEAT_FILES": NO_REPEAT_FILES,
        "controlled_source": controlled_source,
        "validate_predecessor_evidence": validate_predecessor_evidence,
        "canonicalize_equivalences": canonicalize_equivalences,
        "fingerprint_payload": fingerprint_payload,
        "preflight": preflight,
        "execute": execute,
    }
    for name, value in bindings.items():
        setattr(BASE, name, value)


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    for option, value in (
        ("--asset-root", ROOT),
        ("--artifact-dir", DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", DEFAULT_WHISPER_CACHE),
        ("--private-dir", DEFAULT_PRIVATE_DIR),
        ("--output", DEFAULT_OUTPUT),
        ("--paid-lock", DEFAULT_PAID_LOCK),
        ("--representative-evidence", DEFAULT_REPRESENTATIVE_EVIDENCE),
        ("--listening-evidence", DEFAULT_LISTENING_EVIDENCE),
    ):
        if option not in options:
            args.extend((option, str(value)))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_base()
    return int(BASE.main(expand_defaults(argv)))


configure_base()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
