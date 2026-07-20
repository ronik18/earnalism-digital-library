#!/usr/bin/env python3
"""Generate and objectively verify one private Gift of the Magi full title.

The runner is deliberately title-specific and fail closed.  It binds the exact
controlled manuscript, the passing representative evidence, pinned local
Kokoro/af_bella/Whisper artifacts, lossless sentence-bound sections, local
audio-derived ASR, and measured section sync.  It cannot call a listening
provider, upload media, publish, or mutate controlled release truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_kokoro_title_private_audition as representative  # noqa: E402


SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
LANGUAGE = "eng"
PROFILE = "gift-full-v1"
SCHEMA = "earnalism.gift_kokoro_full_title_private_qa.v1"
FULL_SOURCE_SHA256 = "be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e"
FULL_SOURCE_CHARACTERS = 11_298
NORMALIZED_SOURCE_SHA256 = "f32ebf1df2826126eac28341a0dba111be5a734828d9f7b6fffb41d9b95bfe27"
NORMALIZED_SOURCE_CHARACTERS = 11_122
NORMALIZED_SOURCE_WORDS = 2_057
SOURCE_RIGHTS_BASIS = "O. Henry died 1910; first published 1905. Public domain in India and the U.S."

REPRESENTATIVE_EVIDENCE_SHA256 = "7c0aa1286d5915899afa1b2eafc2afb7d79512ea14548c8ec490f570be217dde"
REPRESENTATIVE_LISTENING_SHA256 = "6da110e6c0017ac7dd4c79eb299efed7ee81567841f9a75357462167b5764358"
REPRESENTATIVE_ATTEMPT_FINGERPRINT = "bf5ff8b24d23e4ae912d332b247d26d5efb60eeb0b91ebad0bc179e40a7ea015"
REPRESENTATIVE_LISTENING_FINGERPRINT = "1ef9100b249fae4540df00cad7eba5d03dc29fa6008f3eb393ec3163b243fdf4"
REPRESENTATIVE_ASR_FINGERPRINT = "1b932d7d1193947aad72e51cc2deba889a4c09468b21618d02b21b38db124755"

MODEL_REPO = representative.MODEL_REPO
MODEL_REVISION = representative.MODEL_REVISION
MODEL_SHA256 = representative.MODEL_SHA256
CONFIG_SHA256 = representative.CONFIG_SHA256
VOICE = representative.VOICE
VOICE_SHA256 = representative.VOICE_SHA256
SAMPLE_RATE = representative.SAMPLE_RATE
SPEED = representative.SPEED
RANDOM_SEED = representative.RANDOM_SEED
WHISPER_MODEL = representative.WHISPER_MODEL
WHISPER_SHA256 = representative.WHISPER_SHA256
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
SYNC_SCORE_MIN = 9.7
LISTENING_SCORE_MIN = 9.2
LISTENING_CONFIDENCE_MIN = 0.90

# These counts and hashes were frozen from the exact normalized controlled
# manuscript.  Sections end at sentence boundaries and reconstruct the source
# byte-for-byte when joined by one ASCII space.
SECTION_WORD_COUNTS = (
    105, 110, 108, 125, 117, 108, 106, 107, 109, 108,
    105, 120, 109, 111, 106, 130, 109, 118, 46,
)
SECTION_HASHES = (
    "f9d0cd1b456936cc2d708ae5705b6cbc7f9e53e611d98f833c79e0d2e84ace73",
    "85100b18e3734c13411d07fa9c8f6250d76dd2949fc5bd30373f0c21583d9374",
    "09fee0603b288178d9765437d4fcc4ff2dc3de984c8c7e1dd07ec240e66e3b27",
    "aafc64445c47d06c5f442c82b1bf60780bc257ea04008885f53bae51fe285f91",
    "86030586b0999c88203e88bc8eb8900f1dfe9d2cabb29c50306a71b9fc19d0ba",
    "45c22620381c223b54ac855ed11b94c1e53e20fad424b2c576c2595293bec10f",
    "c3b40d45c886795d0b77a4b06940ef39b743283a399b52bbc6c928c4c02cabf8",
    "a5ba8ed2f8a10fb9980f870ae44c208a387032c309e84dd3910053bbd658b41d",
    "3b99c0e4ea034eeb10b729a54bdbf59d5946e12d15eef234ae5f66c16f934754",
    "947c59526026448beb788cfe2411c97e9783c3a1346448bb258735fc136cf4dc",
    "62a0919f84ecd93a1f1e793ca7f963700f5c9b13cb5da7eafb9cba4fcf221c95",
    "f74a46256d68f7d1d65f6b85a41e5b9453ece5865e154eb605643b0598ca4c4c",
    "f4d90dfa2ea8c93e8a1bd1d4cc72a52028ddcffff3020cf966fdc7a90a80d1b7",
    "60fe005e44c6d6259c5830c0ea09b396b66125589c3f645ca38f0204dfdb047f",
    "99168aa86bdd68efcc485b7642dc35813b5d1df7a23996b2384ba9b81064fbb9",
    "f3fbdbbe79fa4f0e0180a43dd8935f0c759250b950f125843d7c05e615e20517",
    "5400e7427937794214331a39246ea47a036bc769cdfc4c39647183b983c54215",
    "3a64383412b0f6ab5bdf52bedc0b16ff09f8302194cfed574a8467fb5edfbf03",
    "305f66db4ae11a06cacff9e05a06bec1762155da6d46c8094262e8655b0cf58d",
)

PRONUNCIATION_OVERRIDES = {
    "Della": "dˈɛlə",
    "Jim": "dʒˈɪm",
    "Dillingham": "dˈɪlɪŋhæm",
    "Sofronie": "səfɹˈoʊni",
    "Broadway": "bɹˈɔdweɪ",
    "Coney": "kˈoʊni",
    "Solomon": "sˈɑləmən",
    "Sheba": "ʃˈibə",
    "magi": "mˈeɪdʒaɪ",
    "Mme": "mədˈæm",
    "airshaft": "ˈɛɹʃæft",
}
CANONICAL_PROPER_NAMES = (
    "Della", "Jim", "Dillingham", "Sofronie", "Broadway", "Coney", "Solomon", "Sheba",
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
    "initial_prompt": None,
    "word_timestamps": True,
}
SOURCE_EQUIVALENCE_POLICY = {
    "$1.87": "one dollar and eighty-seven cents",
    "$8": "eight dollars",
    "$20": "twenty dollars",
    "$30": "thirty dollars",
    "Mr.": "mister",
    "Mrs.": "mrs",
    "Mme.": "madame",
    "your": "yer",
}

DEFAULT_REPRESENTATIVE_EVIDENCE = (
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_representative_v1.json"
)
DEFAULT_LISTENING_EVIDENCE = (
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_listening_qa_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_full_title_private_preflight_v1.json"
)
DEFAULT_PRIVATE_DIR = (
    ROOT / "internal/audiobook_lab/private_runs/kokoro/the-gift-of-the-magi/full-v1"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
NO_REPEAT_FILES = representative.NO_REPEAT_FILES


class GiftFullTitleError(RuntimeError):
    """Raised when any private full-title contract is not exact."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return representative.sha256_file(path)


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GiftFullTitleError(message)


def read_json(path: Path) -> dict[str, Any]:
    value = representative.read_json(path)
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    representative.atomic_write_json(path, payload)


def verify_file(path: Path, expected: str, label: str) -> None:
    try:
        representative.verify_hash(path, expected, label)
    except representative.KokoroTitlePilotError as exc:
        raise GiftFullTitleError(str(exc)) from exc


def controlled_source(asset_root: Path) -> tuple[Path, str, list[dict[str, Any]]]:
    publication = asset_root / "data/controlled_publications" / SLUG
    book = read_json(publication / "public_book.json")
    source = read_json(publication / "source_evidence.json")
    approval = read_json(publication / "approval_evidence.json")
    expected_book = {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "approved_to_publish": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
    }
    for key, expected in expected_book.items():
        require(book.get(key) == expected, f"controlled book truth changed for {key}")
    require(source.get("rights_basis") == SOURCE_RIGHTS_BASIS, "source rights basis changed")
    require(source.get("provenance_hash") == book.get("provenance_hash"), "source provenance binding changed")
    require(approval.get("audio_public_release") == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED", "audio release truth changed")
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    manuscript = str(chapter.get("content") or "")
    require(chapter.get("processing_status") == "ready", "controlled chapter is not ready")
    require(chapter.get("processing_warnings") == [], "controlled chapter has warnings")
    require(chapter.get("sanitizedSha256") == FULL_SOURCE_SHA256, "recorded full source hash changed")
    require(sha256_text(manuscript) == FULL_SOURCE_SHA256, "controlled full source bytes changed")
    require(len(manuscript) == FULL_SOURCE_CHARACTERS, "controlled source character count changed")
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    require(sha256_text(normalized) == NORMALIZED_SOURCE_SHA256, "normalized source hash changed")
    require(len(normalized) == NORMALIZED_SOURCE_CHARACTERS, "normalized source length changed")
    words = normalized.split(" ")
    require(len(words) == NORMALIZED_SOURCE_WORDS, "normalized source word count changed")
    require(sum(SECTION_WORD_COUNTS) == len(words), "section word layout no longer covers source")
    sections: list[dict[str, Any]] = []
    offset = 0
    for index, (count, expected_hash) in enumerate(zip(SECTION_WORD_COUNTS, SECTION_HASHES), 1):
        text = " ".join(words[offset : offset + count])
        offset += count
        require(sha256_text(text) == expected_hash, f"section-{index:03d} hash changed")
        require(re.search(r"[.!?][\"”’']*$", text), f"section-{index:03d} is not sentence-bound")
        sections.append({
            "passage_id": f"section-{index:03d}",
            "section_index": index,
            "text": text,
            "text_sha256": expected_hash,
            "characters": len(text),
            "word_count": count,
        })
    require(offset == len(words), "section layout has uncovered source words")
    require(" ".join(item["text"] for item in sections) == normalized, "sections are not lossless")
    return chapter_path, normalized, sections


def validate_predecessor_evidence(
    representative_path: Path, listening_path: Path
) -> dict[str, Any]:
    verify_file(representative_path, REPRESENTATIVE_EVIDENCE_SHA256, "representative evidence")
    verify_file(listening_path, REPRESENTATIVE_LISTENING_SHA256, "representative listening evidence")
    audition = read_json(representative_path)
    listening = read_json(listening_path)
    require((audition.get("scope") or {}).get("slug") == SLUG, "representative slug changed")
    require((audition.get("source") or {}).get("source_sha256") == FULL_SOURCE_SHA256, "representative source changed")
    require((audition.get("engine") or {}).get("attempt_fingerprint") == REPRESENTATIVE_ATTEMPT_FINGERPRINT, "representative fingerprint changed")
    require((audition.get("asr") or {}).get("status") == "PASS", "representative ASR is not PASS")
    require(listening.get("sample_fingerprint") == REPRESENTATIVE_LISTENING_FINGERPRINT, "listening fingerprint changed")
    gate = listening.get("listening_gate") or {}
    minimums = gate.get("minimum_scores") or {}
    require(gate.get("platform_screen_pass") is True, "representative platform screen did not pass")
    require(float(minimums.get("overall_listening_score") or 0) >= LISTENING_SCORE_MIN, "representative listening below owner floor")
    require(float(minimums.get("confidence_score") or 0) >= LISTENING_CONFIDENCE_MIN, "representative confidence below floor")
    require(gate.get("fatal_flags") == [], "representative listening has fatal flags")
    require(gate.get("sample_blockers") == [], "representative listening has sample blockers")
    return {
        "representative_evidence_path": str(representative_path),
        "representative_evidence_sha256": REPRESENTATIVE_EVIDENCE_SHA256,
        "representative_attempt_fingerprint": REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "representative_asr_fingerprint": REPRESENTATIVE_ASR_FINGERPRINT,
        "listening_evidence_path": str(listening_path),
        "listening_evidence_sha256": REPRESENTATIVE_LISTENING_SHA256,
        "listening_fingerprint": REPRESENTATIVE_LISTENING_FINGERPRINT,
        "platform_screen_pass": True,
        "minimum_overall_listening_score": minimums["overall_listening_score"],
        "minimum_confidence_score": minimums["confidence_score"],
        "fatal_flags": [],
        "owner_exact_10_observed": gate.get("owner_exact_10_pass") is True,
        "exact_10_is_private_full_title_gate": False,
        "authorization_basis": "owner-authorized global 9.2 floor; exact 10 remains an aspiration, not a release gate",
    }


def full_title_g2p_preflight(sections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        from misaki import en as misaki_en  # noqa: PLC0415
    except ImportError as exc:
        raise GiftFullTitleError("misaki is required for full-title G2P preflight") from exc
    g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update({key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()})
    encountered: set[str] = set()
    reports: list[dict[str, Any]] = []
    unresolved_all: set[str] = set()
    for section in sections:
        phonemes, tokens = g2p(str(section["text"]))
        unresolved = sorted({
            str(token.text)
            for token in tokens
            if re.search(r"[A-Za-z0-9]", str(token.text or ""))
            and not str(token.phonemes or "").strip()
        })
        applied = [name for name in CANONICAL_PROPER_NAMES if re.search(rf"\b{re.escape(name)}\b", str(section["text"]))]
        encountered.update(applied)
        unresolved_all.update(unresolved)
        reports.append({
            "section_id": section["passage_id"],
            "source_text_sha256": section["text_sha256"],
            "phoneme_sha256": sha256_text(str(phonemes or "")),
            "pronunciation_checkpoints": applied,
            "unresolved_tokens": unresolved,
            "pass": bool(phonemes) and not unresolved,
        })
    missing_names = sorted(set(CANONICAL_PROPER_NAMES) - encountered)
    require(not missing_names, "canonical pronunciation checkpoints missing: " + ", ".join(missing_names))
    require(not unresolved_all and all(item["pass"] for item in reports), "G2P unresolved tokens: " + ", ".join(sorted(unresolved_all)))
    return {
        "status": "PASS",
        "fallback_enabled": False,
        "settings": G2P_SETTINGS,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "canonical_proper_names_encountered": sorted(encountered),
        "unresolved_token_count": 0,
        "unresolved_tokens": [],
        "implementation_sha256": sha256_text(inspect.getsource(full_title_g2p_preflight)),
        "sections": reports,
    }


def fingerprint_payload(sections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "contract": SCHEMA,
        "profile": PROFILE,
        "slug": SLUG,
        "full_source_sha256": FULL_SOURCE_SHA256,
        "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
        "section_hashes": [item["text_sha256"] for item in sections],
        "section_word_counts": SECTION_WORD_COUNTS,
        "predecessor_evidence_sha256": REPRESENTATIVE_EVIDENCE_SHA256,
        "predecessor_listening_sha256": REPRESENTATIVE_LISTENING_SHA256,
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "config_sha256": CONFIG_SHA256,
        "voice": VOICE,
        "voice_sha256": VOICE_SHA256,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "sample_rate_hz": SAMPLE_RATE,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "g2p_settings": G2P_SETTINGS,
        "g2p_implementation_sha256": sha256_text(inspect.getsource(full_title_g2p_preflight)),
        "synthesis_implementation_sha256": sha256_text(inspect.getsource(synthesize_sections)),
        "asr_model": WHISPER_MODEL,
        "asr_model_sha256": WHISPER_SHA256,
        "asr_settings": ASR_SETTINGS,
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "asr_implementation_sha256": sha256_text(inspect.getsource(run_asr)),
        "sync_implementation_sha256": sha256_text(inspect.getsource(measured_section_sync)),
        "scope": "one_private_full_title_no_listening_upload_or_publication",
    }


def full_title_fingerprint(sections: Sequence[Mapping[str, Any]]) -> str:
    return canonical_hash(fingerprint_payload(sections))


def _fingerprints(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _fingerprints(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _fingerprints(child, key)
    elif "fingerprint" in key.lower() and isinstance(value, str):
        yield value


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    require(fingerprint not in {
        REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        REPRESENTATIVE_LISTENING_FINGERPRINT,
        REPRESENTATIVE_ASR_FINGERPRINT,
    }, "full-title fingerprint collides with representative evidence")
    for path in NO_REPEAT_FILES:
        if path.is_file():
            require(fingerprint not in set(_fingerprints(read_json(path))), f"full-title fingerprint already exists in {path}")
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        generated = bool((prior.get("safety") or {}).get("full_title_generated"))
        require(not (prior_fingerprint == fingerprint and generated), "this exact full-title attempt already generated audio")


def assert_private_path(path: Path) -> Path:
    try:
        return representative.assert_private_audio_path(path)
    except representative.KokoroTitlePilotError as exc:
        raise GiftFullTitleError(str(exc)) from exc


def preflight(
    *, asset_root: Path, artifact_dir: Path, whisper_cache_dir: Path,
    private_dir: Path, output: Path, paid_lock: Path,
    representative_evidence: Path, listening_evidence: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    chapter_path, manuscript, sections = controlled_source(asset_root)
    predecessor = validate_predecessor_evidence(representative_evidence, listening_evidence)
    fingerprint = full_title_fingerprint(sections)
    ensure_not_repeated(fingerprint, output)
    private = assert_private_path(private_dir)
    try:
        artifacts, artifact_evidence = representative.validate_artifacts(artifact_dir, whisper_cache_dir)
        runtime = representative.runtime_evidence()
        lock = representative.lock_snapshot(paid_lock)
    except representative.KokoroTitlePilotError as exc:
        raise GiftFullTitleError(str(exc)) from exc
    g2p = full_title_g2p_preflight(sections)
    estimated_seconds = round(105.775 * NORMALIZED_SOURCE_CHARACTERS / 1_765, 3)
    estimated_pcm_bytes = int(estimated_seconds * SAMPLE_RATE * 2 + 44)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_PRIVATE_FULL_TITLE_EXECUTION",
        "scope": {
            "slug": SLUG, "title": TITLE, "author": AUTHOR, "language": LANGUAGE,
            "profile": PROFILE, "private_only": True, "section_count": len(sections),
            "full_title_generated": False,
        },
        "source": {
            "chapter_path": str(chapter_path),
            "source_sha256": FULL_SOURCE_SHA256,
            "source_characters": FULL_SOURCE_CHARACTERS,
            "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
            "normalized_characters": len(manuscript),
            "normalized_words": NORMALIZED_SOURCE_WORDS,
            "lossless_section_reconstruction": True,
            "section_word_counts": list(SECTION_WORD_COUNTS),
            "sections": [
                {key: item[key] for key in ("passage_id", "section_index", "text_sha256", "characters", "word_count")}
                for item in sections
            ],
        },
        "predecessor_gate": predecessor,
        "rights": {
            "text_rights_status": "PASS_PUBLIC_DOMAIN_TIER_A",
            "rights_basis": SOURCE_RIGHTS_BASIS,
            "model_and_voicepack_license": "Apache-2.0",
            "private_full_title_allowed": True,
            "gift_title_scoped_publication_risk_acceptance_bound": False,
            "production_release_approved": False,
            "public_disclosure_required_if_later_approved": "Narration: AI voice",
        },
        "engine": {
            "family": "open_weight_local_tts",
            "package": "kokoro", "package_version": representative.KOKORO_VERSION,
            "model_repo": MODEL_REPO, "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256, "config_sha256": CONFIG_SHA256,
            "voice": VOICE, "voice_sha256": VOICE_SHA256,
            "speed": SPEED, "random_seed": RANDOM_SEED, "sample_rate_hz": SAMPLE_RATE,
            "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
            "g2p_fallback_enabled": False,
            "attempt_fingerprint": fingerprint,
            "fingerprint_payload_sha256": canonical_hash(fingerprint_payload(sections)),
        },
        "g2p_preflight": g2p,
        "asr_contract": {
            "model": WHISPER_MODEL, "model_sha256": WHISPER_SHA256,
            "source_score_min": ASR_SCORE_MIN, "coverage_min": ASR_COVERAGE_MIN,
            "first_words_required": True, "last_words_required": True,
            "no_missing_duplicated_reordered_or_unexpected_content_required": True,
            "audio_derived": True, "settings": ASR_SETTINGS,
            "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        },
        "sync_contract": {
            "tier": "PARAGRAPH_OR_SECTION_SYNC_PREMIUM",
            "measured_section_sync_min": SYNC_SCORE_MIN,
            "audio_derived_or_measured_required": True,
            "estimated_sync_allowed": False,
            "public_word_level_sync_claim_allowed": False,
        },
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "cost_and_capacity": {
            "tts_provider_cost_usd": 0.0, "asr_provider_cost_usd": 0.0,
            "listening_provider_cost_usd_this_stage": 0.0,
            "estimated_duration_seconds": estimated_seconds,
            "estimated_pcm_wav_bytes": estimated_pcm_bytes,
            "estimated_pcm_wav_mib": round(estimated_pcm_bytes / 1_048_576, 3),
            "estimated_local_runtime_minutes": {"apple_silicon_expected": [12, 35], "cpu_fallback_expected": [30, 90]},
        },
        "safety": {
            "provider_calls": 0, "listening_provider_calls": 0,
            "paid_tts_lock": lock, "paid_tts_lock_touched": False,
            "private_output_dir": str(private), "audio_generated": False,
            "full_title_generated": False, "upload_performed": False,
            "publication_performed": False, "release_gate_mutated": False,
            "public_audio_approved": False, "browser_or_system_speech_fallback": False,
        },
        "blockers_to_release": [
            "PRIVATE_FULL_TITLE_NOT_GENERATED",
            "FULL_TITLE_AUDIO_DERIVED_ASR_NOT_RUN",
            "MEASURED_FULL_TITLE_SECTION_SYNC_NOT_RUN",
            "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        ],
    }
    return payload, sections, artifacts


def synthesize_sections(
    sections: Sequence[Mapping[str, Any]], artifacts: Mapping[str, Path], private_dir: Path
) -> list[dict[str, Any]]:
    previous_filelock, _stub = representative._install_local_filelock_stub()
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from kokoro import KModel, KPipeline  # noqa: PLC0415
        from misaki import en as misaki_en  # noqa: PLC0415
    finally:
        if previous_filelock is None:
            sys.modules.pop("filelock", None)
        else:
            sys.modules["filelock"] = previous_filelock
    private = assert_private_path(private_dir)
    private.mkdir(parents=True, exist_ok=True)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = KModel(config=str(artifacts["config"]), model=str(artifacts["model"]))
    pipeline = KPipeline(lang_code="a", model=model, repo_id=None)
    pipeline.g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    pipeline.g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    pipeline.g2p.lexicon.golds.update({key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()})
    voice_tensor = torch.load(str(artifacts["voice"]), map_location="cpu", weights_only=True)
    prepared: list[tuple[Mapping[str, Any], Any]] = []
    for section in sections:
        _phonemes, tokens = pipeline.g2p(str(section["text"]))
        unresolved = sorted({
            str(token.text) for token in tokens
            if re.search(r"[A-Za-z0-9]", str(token.text or ""))
            and not str(token.phonemes or "").strip()
        })
        require(not unresolved, f"G2P fallback disabled; unresolved tokens in {section['passage_id']}: {', '.join(unresolved)}")
        prepared.append((section, tokens))
    results: list[dict[str, Any]] = []
    for section, tokens in prepared:
        chunks: list[Any] = []
        phonemes: list[str] = []
        for item in pipeline.generate_from_tokens(tokens, voice=voice_tensor, speed=SPEED):
            require(item.audio is not None, f"Kokoro returned no audio: {section['passage_id']}")
            chunks.append(item.audio.detach().cpu().numpy())
            phonemes.append(str(item.phonemes or ""))
        require(bool(chunks), f"Kokoro returned zero chunks: {section['passage_id']}")
        target = private / f"{section['passage_id']}.wav"
        sf.write(target, np.concatenate(chunks), SAMPLE_RATE, subtype="PCM_16")
        metrics = representative.wav_metrics(target)
        require(metrics["objective_format_pass"] is True, f"objective WAV check failed: {section['passage_id']}")
        results.append({
            "passage_id": section["passage_id"],
            "source_text_sha256": section["text_sha256"],
            "characters": section["characters"], "word_count": section["word_count"],
            "audio_path": str(target), "phoneme_sha256": sha256_text("".join(phonemes)),
            "g2p_fallback_enabled": False, **metrics,
        })
    return results


def recompose(samples: Sequence[Mapping[str, Any]], target: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
    except ImportError as exc:
        raise GiftFullTitleError("numpy and soundfile are required") from exc
    target = assert_private_path(target)
    arrays: list[Any] = []
    boundaries: list[dict[str, Any]] = []
    cursor = 0
    for sample in samples:
        audio = assert_private_path(Path(str(sample["audio_path"])))
        verify_file(audio, str(sample["audio_sha256"]), f"section audio {sample['passage_id']}")
        data, rate = sf.read(str(audio), dtype="float32")
        require(rate == SAMPLE_RATE and data.ndim == 1 and len(data) > 0, f"invalid section WAV: {sample['passage_id']}")
        arrays.append(data)
        boundaries.append({
            "section_id": sample["passage_id"], "start_frame": cursor,
            "end_frame": cursor + len(data), "audio_sha256": sample["audio_sha256"],
        })
        cursor += len(data)
    require(bool(arrays), "cannot recompose empty full title")
    target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(target, np.concatenate(arrays), SAMPLE_RATE, subtype="PCM_16")
    metrics = representative.wav_metrics(target)
    require(metrics["objective_format_pass"] is True, "full-title WAV objective check failed")
    return {"full_audio_path": str(target), "full_audio_frame_count": cursor, **metrics}, boundaries


def canonicalize_equivalences(text: str) -> tuple[str, list[dict[str, Any]]]:
    value = text
    applied: list[dict[str, Any]] = []
    rules = (
        (r"\$1\.87\b", "one dollar and eighty-seven cents", "$1.87"),
        (r"\$8\b", "eight dollars", "$8"),
        (r"\$20\b", "twenty dollars", "$20"),
        (r"\$30\b", "thirty dollars", "$30"),
        (r"\bMr\.?\b|\bmister\b", "mister", "Mr."),
        (r"\bMrs\.?\b|\bmissus\b", "mrs", "Mrs."),
        (r"\bMme\.?\b|\bmadame\b", "madame", "Mme."),
        (r"\byour\b|\byer\b", "yer", "your/yer"),
    )
    for pattern, replacement, label in rules:
        value, count = re.subn(pattern, replacement, value, flags=re.IGNORECASE)
        if count:
            applied.append({"equivalence": label, "replacement": replacement, "match_count": count})
    return value, applied


def ordered_metrics(source: str, transcript: str) -> dict[str, Any]:
    source_evaluated, source_equivalences = canonicalize_equivalences(source)
    transcript_evaluated, transcript_equivalences = canonicalize_equivalences(transcript)
    metrics = representative.ordered_token_integrity(source_evaluated, transcript_evaluated)
    passed = bool(
        float(metrics["score"]) >= ASR_SCORE_MIN
        and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
        and metrics["first_words_match"] is True
        and metrics["last_words_match"] is True
        and metrics["ordered_content_integrity_pass"] is True
        and metrics["no_missing_content"] is True
        and metrics["no_duplicate_content"] is True
        and metrics["no_reordered_content"] is True
        and metrics["no_unexpected_content"] is True
    )
    return {
        **metrics,
        "evaluated_source_sha256": sha256_text(source_evaluated),
        "evaluated_transcript_sha256": sha256_text(transcript_evaluated),
        "source_equivalences_applied": source_equivalences,
        "transcript_equivalences_applied": transcript_equivalences,
        "pass": passed,
    }


def verified_words(result: Mapping[str, Any], duration: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    words: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    previous_end = -1.0
    for segment in result.get("segments") or []:
        for raw in segment.get("words") or []:
            word = str(raw.get("word") or "").strip()
            start = float(raw.get("start") or 0.0)
            end = float(raw.get("end") or 0.0)
            if not word or start < 0 or end <= start or end > duration + 0.05 or start + 0.05 < previous_end:
                anomalies.append({"word": word, "start": start, "end": end, "reason": "INVALID_OR_NON_MONOTONIC_TIMESTAMP"})
                continue
            previous_end = end
            words.append({
                "word": word, "start_seconds": round(start, 6), "end_seconds": round(end, 6),
                "probability": round(float(raw.get("probability") or 0.0), 6),
            })
    if not words:
        anomalies.append({"reason": "NO_AUDIO_DERIVED_WORD_TIMESTAMPS"})
    return words, anomalies


def asr_config_fingerprint(samples: Sequence[Mapping[str, Any]], attempt_fingerprint: str) -> str:
    return canonical_hash({
        "contract": "earnalism.gift_full_title_audio_derived_asr.v1",
        "slug": SLUG, "source_sha256": FULL_SOURCE_SHA256,
        "attempt_fingerprint": attempt_fingerprint,
        "model": WHISPER_MODEL, "model_sha256": WHISPER_SHA256,
        "audio_hashes": {item["passage_id"]: item["audio_sha256"] for item in samples},
        "settings": ASR_SETTINGS, "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
    })


def run_asr(
    samples: Sequence[Mapping[str, Any]], sections: Sequence[Mapping[str, Any]],
    whisper_cache_dir: Path, attempt_fingerprint: str,
) -> dict[str, Any]:
    try:
        import whisper  # noqa: PLC0415
    except ImportError as exc:
        raise GiftFullTitleError("openai-whisper is required") from exc
    model_path = whisper_cache_dir / representative.WHISPER_FILENAME
    verify_file(model_path, WHISPER_SHA256, "pinned Whisper model")
    model = whisper.load_model(WHISPER_MODEL, download_root=str(whisper_cache_dir))
    by_id = {item["passage_id"]: item for item in sections}
    reports: list[dict[str, Any]] = []
    aggregate_transcripts: list[str] = []
    for sample in samples:
        section_id = str(sample["passage_id"])
        section = by_id[section_id]
        audio = assert_private_path(Path(str(sample["audio_path"])))
        verify_file(audio, str(sample["audio_sha256"]), f"ASR input {section_id}")
        result = model.transcribe(str(audio), **ASR_SETTINGS)
        transcript = str(result.get("text") or "").strip()
        metrics = ordered_metrics(str(section["text"]), transcript)
        words, anomalies = verified_words(result, float(sample["duration_seconds"]))
        passed = bool(metrics["pass"] and words and not anomalies)
        aggregate_transcripts.append(transcript)
        reports.append({
            "section_id": section_id, "audio_sha256": sample["audio_sha256"],
            "source_text_sha256": section["text_sha256"], "transcript": transcript,
            "transcript_sha256": sha256_text(transcript), "audio_derived_word_timestamps": words,
            "word_timestamp_anomalies": anomalies, "word_timestamp_evidence_valid": bool(words) and not anomalies,
            **metrics, "pass": passed,
        })
    aggregate = ordered_metrics(" ".join(item["text"] for item in sections), " ".join(aggregate_transcripts))
    passed = bool(all(item["pass"] for item in reports) and aggregate["pass"])
    return {
        "status": "PASS" if passed else "FAIL",
        "config_fingerprint": asr_config_fingerprint(samples, attempt_fingerprint),
        "model": WHISPER_MODEL, "model_sha256": WHISPER_SHA256,
        "audio_derived": True, "settings": ASR_SETTINGS,
        "reports": reports, "full_title_aggregate": aggregate,
    }


def measured_section_sync(
    sections: Sequence[Mapping[str, Any]], samples: Sequence[Mapping[str, Any]],
    boundaries: Sequence[Mapping[str, Any]], asr: Mapping[str, Any],
    recomposition: Mapping[str, Any],
) -> dict[str, Any]:
    sample_by_id = {item["passage_id"]: item for item in samples}
    boundary_by_id = {item["section_id"]: item for item in boundaries}
    report_by_id = {item["section_id"]: item for item in asr.get("reports") or []}
    records: list[dict[str, Any]] = []
    prior_end = 0
    for section in sections:
        section_id = section["passage_id"]
        sample = sample_by_id.get(section_id) or {}
        boundary = boundary_by_id.get(section_id) or {}
        report = report_by_id.get(section_id) or {}
        start_frame = int(boundary.get("start_frame") or 0)
        end_frame = int(boundary.get("end_frame") or 0)
        frame_count = int(round(float(sample.get("duration_seconds") or 0) * SAMPLE_RATE))
        binding_pass = bool(
            sample.get("source_text_sha256") == section["text_sha256"]
            and boundary.get("audio_sha256") == sample.get("audio_sha256")
            and report.get("audio_sha256") == sample.get("audio_sha256")
            and report.get("source_text_sha256") == section["text_sha256"]
            and start_frame == prior_end and end_frame > start_frame
            and abs((end_frame - start_frame) - frame_count) <= 1
            and report.get("word_timestamp_evidence_valid") is True
            and report.get("pass") is True
        )
        records.append({
            "section_id": section_id, "source_text_sha256": section["text_sha256"],
            "audio_sha256": sample.get("audio_sha256"),
            "start_seconds": round(start_frame / SAMPLE_RATE, 6),
            "end_seconds": round(end_frame / SAMPLE_RATE, 6),
            "audio_derived_word_timestamp_sha256": canonical_hash(report.get("audio_derived_word_timestamps") or []),
            "source_score": report.get("score"), "source_coverage": report.get("coverage"),
            "binding_pass": binding_pass,
        })
        prior_end = end_frame
    aggregate = asr.get("full_title_aggregate") or {}
    scores = [float(item.get("source_score") or 0) for item in records]
    coverages = [float(item.get("source_coverage") or 0) for item in records]
    recomposition_pass = bool(
        prior_end == int(recomposition.get("full_audio_frame_count") or 0)
        and recomposition.get("objective_format_pass") is True
        and bool(recomposition.get("audio_sha256"))
    )
    score = min(scores + [float(aggregate.get("score") or 0)]) if scores else 0.0
    coverage = min(coverages + [float(aggregate.get("coverage") or 0)]) if coverages else 0.0
    passed = bool(
        recomposition_pass and records and all(item["binding_pass"] for item in records)
        and score >= SYNC_SCORE_MIN and coverage >= ASR_COVERAGE_MIN
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "sync_tier": "PARAGRAPH_OR_SECTION_SYNC_PREMIUM",
        "granularity": "measured_section",
        "sync_score": round(score, 4), "coverage": round(coverage, 4),
        "required_score": SYNC_SCORE_MIN, "required_coverage": ASR_COVERAGE_MIN,
        "audio_derived_or_measured": True, "auto_estimated_sync": False,
        "public_word_level_sync_claim_allowed": False,
        "full_audio_sha256": recomposition.get("audio_sha256"),
        "full_audio_frame_count": recomposition.get("full_audio_frame_count"),
        "recomposition_pass": recomposition_pass, "sections": records,
        "sync_pass": passed,
    }


def execute(
    *, preflight_payload: dict[str, Any], sections: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path], private_dir: Path, whisper_cache_dir: Path,
    paid_lock: Path, output: Path,
) -> tuple[int, dict[str, Any]]:
    lock_before = representative.lock_snapshot(paid_lock)
    fingerprint = str(preflight_payload["engine"]["attempt_fingerprint"])
    samples = synthesize_sections(sections, artifacts, private_dir)
    recomposition, boundaries = recompose(samples, assert_private_path(private_dir) / f"{SLUG}-full.wav")
    lock_after_synthesis = representative.lock_snapshot(paid_lock)
    require(lock_before == lock_after_synthesis, "paid_tts.lock changed during local synthesis")
    checkpoint = {
        **preflight_payload, "generated_at": utc_now(),
        "status": "PRIVATE_FULL_TITLE_SYNTHESIZED_ASR_IN_PROGRESS",
        "samples": samples, "recomposition": {**recomposition, "section_boundaries": boundaries},
        "safety": {**preflight_payload["safety"], "audio_generated": True, "full_title_generated": True},
    }
    write_json(output, checkpoint)
    asr = run_asr(samples, sections, whisper_cache_dir, fingerprint)
    sync = measured_section_sync(sections, samples, boundaries, asr, recomposition)
    lock_after = representative.lock_snapshot(paid_lock)
    require(lock_before == lock_after, "paid_tts.lock changed during local objective QA")
    objective_pass = bool(asr.get("status") == "PASS" and sync.get("sync_pass") is True)
    blockers = [
        "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
        "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    if not objective_pass:
        blockers.insert(0, "PRIVATE_FULL_TITLE_OBJECTIVE_QA_FAILED")
    payload = {
        **checkpoint, "generated_at": utc_now(),
        "status": "PRIVATE_FULL_TITLE_OBJECTIVE_PASS_LISTENING_PENDING" if objective_pass else "PRIVATE_FULL_TITLE_REJECTED_OBJECTIVE_QA",
        "asr": asr, "measured_sync": sync,
        "safety": {
            **checkpoint["safety"], "provider_calls": 0, "listening_provider_calls": 0,
            "paid_tts_lock_before": lock_before, "paid_tts_lock_after": lock_after,
            "paid_tts_lock_unchanged": lock_before == lock_after,
            "upload_performed": False, "publication_performed": False,
            "release_gate_mutated": False, "public_audio_approved": False,
        },
        "blockers_to_release": blockers,
    }
    write_json(output, payload)
    return (0 if objective_pass else 5), payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--whisper-cache-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--representative-evidence", type=Path, default=DEFAULT_REPRESENTATIVE_EVIDENCE)
    parser.add_argument("--listening-evidence", type=Path, default=DEFAULT_LISTENING_EVIDENCE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload, sections, artifacts = preflight(
        asset_root=args.asset_root.expanduser().resolve(),
        artifact_dir=args.artifact_dir.expanduser().resolve(),
        whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
        private_dir=args.private_dir.expanduser().resolve(),
        output=args.output.expanduser().resolve(),
        paid_lock=args.paid_lock.expanduser().resolve(),
        representative_evidence=args.representative_evidence.expanduser().resolve(),
        listening_evidence=args.listening_evidence.expanduser().resolve(),
    )
    if args.dry_run:
        write_json(args.output.expanduser().resolve(), payload)
        code = 0
    else:
        code, payload = execute(
            preflight_payload=payload, sections=sections, artifacts=artifacts,
            private_dir=args.private_dir.expanduser().resolve(),
            whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
            paid_lock=args.paid_lock.expanduser().resolve(),
            output=args.output.expanduser().resolve(),
        )
    print(json.dumps({
        "status": payload["status"], "output": str(args.output.expanduser().resolve()),
        "attempt_fingerprint": payload["engine"]["attempt_fingerprint"],
        "section_count": payload["scope"]["section_count"],
        "provider_calls": payload["safety"]["provider_calls"],
        "full_title_generated": payload["safety"]["full_title_generated"],
        "publication_performed": payload["safety"]["publication_performed"],
    }, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
