#!/usr/bin/env python3
"""Fail-closed, source-bound Kokoro representative adapter for one title.

This contract permits only ``the-cop-and-the-anthem`` and four hash-bound
passages from its current controlled publication.  It uses checksum-pinned
local Kokoro and Whisper artifacts, never downloads a model, never calls a
provider, accepts only private audio paths, and treats the paid-TTS lock as a
read-only safety input.  It cannot upload, publish, or mutate release truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
import types
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]

ALLOWED_SLUG = "the-cop-and-the-anthem"
PROFILE_ID = "cop-ironic-restraint-v1"
TITLE = "The Cop and the Anthem"
AUTHOR = "O. Henry"
LANGUAGE = "eng"

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_FILENAME = "kokoro-v1_0.pth"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_FILENAME = "config.json"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "af_bella"
VOICE_FILENAME = "voices/af_bella.pt"
VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
WHISPER_MODEL = "medium.en"
WHISPER_FILENAME = "medium.en.pt"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

KOKORO_VERSION = "0.9.4"
PYTHON_VERSION = "3.11.15"
PYTHON_IMPLEMENTATION = "CPython"
PYTHON_EXECUTABLE_SHA256 = "50de159a94723fa71090030ac642b101e27f8d29488ec4bdae91edfa1e86dbbd"
RUNTIME_VERSIONS = {
    "kokoro": "0.9.4",
    "misaki": "0.9.4",
    "torch": "2.13.0",
    "transformers": "5.14.1",
    "spacy": "3.8.14",
    "soundfile": "0.14.0",
    "numpy": "2.4.6",
    "en-core-web-sm": "3.8.0",
    "openai-whisper": "20250625",
}

EXPECTED_SOURCE_SHA256 = "77a6d1c7ff6162cc7aad47b950666c6bb1dedf0beb55a08f3f476e27e57bd3ab"
EXPECTED_SOURCE_CHARACTERS = 13_232
EXPECTED_FLATTENED_SHA256 = "e23828f07e7bcd8fc48a0206427a267682e8c8cb155226ca1ee166be3172c64c"
PASSAGE_SPECS = (
    {
        "passage_id": "opening_winter",
        "risk": "opening_and_narrative_tone",
        "start": "On his bench in Madison Square Soapy moved uneasily.",
        "end": "you may know that winter is near at hand.",
        "characters": 254,
        "sha256": "99ec90941755c7e7b70c98f2a122f1aeefdf7c996bd3e66bade805b8149f4a4c",
    },
    {
        "passage_id": "waiter_dialogue",
        "risk": "comic_dialogue_and_dialect",
        "start": "“Now, get busy and call a cop,” said Soapy.",
        "end": "The Island seemed very far away.",
        "characters": 445,
        "sha256": "9b7aa5abbd52519cc2fd4c155ceb43711cd287f068792c319b8e1cf4554e50b8",
    },
    {
        "passage_id": "church_reckoning",
        "risk": "emotional_reversal_and_restraint",
        "start": "The conjunction of Soapy’s receptive state of mind",
        "end": "made up his existence.",
        "characters": 316,
        "sha256": "8af80b2d0f436da3933b2a50bed8dc98d299367d982d520110c0b07da8b364ae",
    },
    {
        "passage_id": "ironic_ending",
        "risk": "sustained_emotion_dialogue_and_ironic_ending",
        "start": "And also in a moment his heart responded thrillingly",
        "end": "the next morning.",
        "characters": 1001,
        "sha256": "cb03b2bf6553545bc323f4417dafced01e0042aca8d5f31f32245311357f3c3d",
    },
)
EXPECTED_PASSAGE_HASHES = tuple(str(item["sha256"]) for item in PASSAGE_SPECS)
EXPECTED_PASSAGE_CHARACTERS = 2_016

SAMPLE_RATE = 24_000
SPEED = 0.98
RANDOM_SEED = 20260719
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
PRONUNCIATION_OVERRIDES = {
    "Soapy": "sˈoʊpi",
    "youse": "jˈuːz",
    "Manhattan": "mænhˈætən",
    # Misaki normalizes both straight and curly apostrophe-final source forms
    # to these lowercase lexicon keys before lookup.
    "doin'": "dˈuːɪn",
    "nothin'": "nˈʌθɪn",
}
SOURCE_DIALECT_PRONUNCIATION_BINDINGS = {
    "doin’": {"lexicon_key": "doin'", "phonemes": "dˈuːɪn"},
    "Nothin’": {"lexicon_key": "nothin'", "phonemes": "nˈʌθɪn"},
}
ASR_VOCABULARY_PROMPT = (
    "Canonical names and spellings: Soapy; Madison Square; Manhattan; O. Henry; "
    "Jack Frost; the Island. Preserve the complete source wording and dialect."
)
EXPECTED_EXISTING_AUDIO_HASHES = {
    "opening_winter": "cdccca49984fac5f84eb27bab12050888936a3c6b27137d770f2a65e682c05ec",
    "waiter_dialogue": "60230065b6fb0181c9f2e0891d948ae901a5f85c986ec6c874a652bdb58559e9",
    "church_reckoning": "e6c8b69f1bb3ebd826c96522a506e4ac937848f34ed8fe8e9c7c78baf275dd5f",
    "ironic_ending": "986f2afe63ba4dfb28d72d7680d2f335ae7c6d534bcae6ace744402ef88b004b",
}
ASR_REVERIFY_POLICY = {
    "opening_winter": {
        "prompt_mode": "canonical_vocabulary_prompt",
        "beam_size": 5,
        "patience": 1.0,
        "hallucination_silence_threshold": None,
    },
    "waiter_dialogue": {
        "prompt_mode": "no_prompt",
        "beam_size": 10,
        "patience": 1.0,
        "hallucination_silence_threshold": 0.5,
    },
    "church_reckoning": {
        "prompt_mode": "canonical_vocabulary_prompt",
        "beam_size": 5,
        "patience": 1.0,
        "hallucination_silence_threshold": None,
    },
    "ironic_ending": {
        "prompt_mode": "no_prompt",
        "beam_size": 5,
        "patience": 1.0,
        "hallucination_silence_threshold": 0.5,
    },
}
SOURCE_EQUIVALENCE_POLICY = {
    "opening_winter": (
        {
            "pattern": r"\bseal[\s-]+skin\b",
            "replacement": "sealskin",
            "reason": "Whisper spacing or hyphenation for the exact spoken source compound sealskin",
        },
    ),
    "waiter_dialogue": (
        {
            "pattern": r"\byous\b",
            "replacement": "youse",
            "reason": "Whisper spelling for the exact spoken source dialect youse",
        },
    ),
    "church_reckoning": (),
    "ironic_ending": (
        {
            "pattern": r"\btomorrow\b",
            "replacement": "to-morrow",
            "reason": "Whisper modern spelling for the exact spoken source form to-morrow",
        },
        {
            "pattern": r"\bdoing\b",
            "replacement": "doin’",
            "reason": "Whisper standard spelling for the exact spoken source dialect doin’",
        },
        {
            "pattern": r"\bnothing\b",
            "replacement": "nothin’",
            "reason": "Whisper standard spelling for the exact spoken source dialect Nothin’",
        },
    ),
}
ASR_DIAGNOSTIC_SUMMARY = {
    "prompted_waiter": {
        "trailing_unexpected_speech": "Thank you for watching.",
        "max_no_speech_probability": 0.4664532244205475,
    },
    "plain_unprompted_waiter": {
        "trailing_unexpected_speech": "Thank you for joining us today.",
        "max_no_speech_probability": 0.37671467661857605,
    },
    "selected_unprompted_waiter": {
        "beam_size": 10,
        "patience": 1.0,
        "hallucination_silence_threshold": 0.5,
        "trailing_unexpected_speech": None,
        "raw_transcript_ends_with": "The island seemed very far away.",
        "manual_transcript_deletion_performed": False,
    },
}

# The two completed Google synthesis fingerprints and their registry-derived
# identities are immutable no-repeat evidence for this title.
KNOWN_GOOGLE_FINGERPRINTS = frozenset(
    {
        "bd4b31c2312dfa26",
        "9311f74b6465c550",
        "15fc2ccfb4816706f69a0f255075928f978a68182961fda6b575ad0c81e52f88",
        "c876cfcfd99507630077f953619e1114dd95f1110d80ffe9fe158aef6fbc90bc",
    }
)
SUPERSEDED_PRE_SYNTHESIS_ATTEMPTS = (
    {
        "attempt_fingerprint": "473233a16da8afc80e6a30c56a9a7d56c2bf964f7d99198d11ca6a80132df38f",
        "status": "G2P_PRECHECK_BLOCKED_BEFORE_SYNTHESIS",
        "reason": "canonical dialect tokens doin’ and Nothin’ had no explicit pronunciation",
        "audio_generated": False,
        "asr_run": False,
        "private_audio_files_written": 0,
        "eligible_to_retry_exact_fingerprint": False,
    },
    {
        "attempt_fingerprint": "18caca9ef65a850cda74a27991600f6b2a640eb8100a6c1e209b46dcef4aceda",
        "status": "G2P_PRECHECK_BLOCKED_BEFORE_SYNTHESIS",
        "reason": "source-curly-apostrophe lexicon keys did not match Misaki normalized lookup keys",
        "audio_generated": False,
        "asr_run": False,
        "private_audio_files_written": 0,
        "eligible_to_retry_exact_fingerprint": False,
    },
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/the-cop-and-the-anthem_release_gate_evidence.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
)


class CopKokoroPilotError(RuntimeError):
    """Raised whenever the exact private-pilot contract cannot be preserved."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopKokoroPilotError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CopKokoroPilotError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise CopKokoroPilotError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise CopKokoroPilotError(
            f"{label} SHA-256 mismatch: expected {expected}, observed {observed}"
        )


def assert_private_audio_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"{resolved.as_posix().lower()}/"
    forbidden = (
        "/frontend/public/",
        "/frontend/build/",
        "/public/audio/",
        "/static/audio/",
    )
    if any(marker in rendered for marker in forbidden):
        raise CopKokoroPilotError(f"public audio path is forbidden: {resolved}")
    private_marker = "/internal/audiobook_lab/private_runs/"
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if private_marker not in rendered and not (
        resolved == temporary_root or temporary_root in resolved.parents
    ):
        raise CopKokoroPilotError(
            "audio output must be under internal/audiobook_lab/private_runs or the OS temp root"
        )
    return resolved


def lock_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    payload = read_json(resolved)
    if payload.get("status") != "active":
        raise CopKokoroPilotError("paid_tts.lock is not active")
    if payload.get("current_holder") != "none":
        raise CopKokoroPilotError("paid_tts.lock has a current holder")
    if payload.get("allowed_next_holders") != []:
        raise CopKokoroPilotError("paid_tts.lock allowlist is not empty")
    raw = resolved.read_bytes()
    return {
        "path": str(resolved),
        "sha256": sha256_bytes(raw),
        "size_bytes": len(raw),
        "status": "active",
        "current_holder": "none",
        "allowed_next_holders": [],
        "read_only": True,
    }


def controlled_source(asset_root: Path, slug: str) -> tuple[Path, list[dict[str, Any]]]:
    if slug != ALLOWED_SLUG:
        raise CopKokoroPilotError(
            f"slug is not allowed by {PROFILE_ID}: {slug}; only {ALLOWED_SLUG} is permitted"
        )
    publication = asset_root / "data/controlled_publications" / slug
    book = read_json(publication / "public_book.json")
    expected_truth = {
        "slug": ALLOWED_SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "is_published": True,
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        "readerStatus": "reader_ready",
        "allowPublicReading": True,
        "audiobook_enabled": False,
        "audio_enabled": False,
        "generate_audiobook": False,
        "audiobook": {},
    }
    for key, expected in expected_truth.items():
        if book.get(key) != expected:
            raise CopKokoroPilotError(
                f"controlled catalog truth changed for {key}: expected {expected!r}, "
                f"observed {book.get(key)!r}"
            )
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    if chapter.get("processing_status") != "ready":
        raise CopKokoroPilotError("controlled chapter is not ready")
    if chapter.get("processing_warnings") != []:
        raise CopKokoroPilotError("controlled chapter has processing warnings")
    manuscript = str(chapter.get("content") or "")
    if chapter.get("sanitizedSha256") != EXPECTED_SOURCE_SHA256:
        raise CopKokoroPilotError("recorded controlled source hash changed")
    if sha256_text(manuscript) != EXPECTED_SOURCE_SHA256:
        raise CopKokoroPilotError("controlled source bytes changed")
    if len(manuscript) != EXPECTED_SOURCE_CHARACTERS:
        raise CopKokoroPilotError("controlled source character count changed")
    flattened = re.sub(r"\s+", " ", manuscript).strip()
    if sha256_text(flattened) != EXPECTED_FLATTENED_SHA256:
        raise CopKokoroPilotError("flattened controlled source changed")
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start = flattened.index(str(spec["start"]))
        end_marker = str(spec["end"])
        end = flattened.index(end_marker, start) + len(end_marker)
        text = flattened[start:end]
        if len(text) != spec["characters"]:
            raise CopKokoroPilotError(
                f"passage character count changed: {spec['passage_id']}"
            )
        if sha256_text(text) != spec["sha256"]:
            raise CopKokoroPilotError(f"passage hash changed: {spec['passage_id']}")
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "risk": spec["risk"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != EXPECTED_PASSAGE_CHARACTERS:
        raise CopKokoroPilotError("bounded passage character total changed")
    return chapter_path, passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.cop_kokoro_representative.v1",
        "profile": PROFILE_ID,
        "slug": ALLOWED_SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "passage_hashes": [item["text_sha256"] for item in passages],
        "provider_family": "open_weight_local_kokoro",
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "config_sha256": CONFIG_SHA256,
        "voice": VOICE,
        "voice_sha256": VOICE_SHA256,
        "whisper_model": WHISPER_MODEL,
        "whisper_sha256": WHISPER_SHA256,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "source_dialect_pronunciation_bindings": SOURCE_DIALECT_PRONUNCIATION_BINDINGS,
        "scope": "four_passage_private_representative_pilot",
    }
    return sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _fingerprints(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _fingerprints(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _fingerprints(child, key)
    elif "fingerprint" in key.lower() and isinstance(value, str):
        yield value


def ensure_materially_distinct(fingerprint: str) -> None:
    for blocked in KNOWN_GOOGLE_FINGERPRINTS:
        if fingerprint == blocked or fingerprint.startswith(blocked) or blocked.startswith(fingerprint):
            raise CopKokoroPilotError("attempt repeats a completed Google fingerprint")


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    ensure_materially_distinct(fingerprint)
    for evidence in NO_REPEAT_FILES:
        if evidence.is_file() and fingerprint in set(_fingerprints(read_json(evidence))):
            raise CopKokoroPilotError(f"attempt fingerprint already exists in {evidence}")
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        audio_generated = bool((prior.get("safety") or {}).get("audio_generated"))
        if prior_fingerprint == fingerprint and audio_generated:
            raise CopKokoroPilotError("this exact pilot already generated audio")


def validate_artifacts(
    artifact_dir: Path, whisper_cache_dir: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    root = artifact_dir.expanduser().resolve()
    voice = root / VOICE_FILENAME
    if not voice.is_file():
        voice = root / Path(VOICE_FILENAME).name
    paths = {
        "model": root / MODEL_FILENAME,
        "config": root / CONFIG_FILENAME,
        "voice": voice,
        "whisper": whisper_cache_dir.expanduser().resolve() / WHISPER_FILENAME,
    }
    expected = {
        "model": MODEL_SHA256,
        "config": CONFIG_SHA256,
        "voice": VOICE_SHA256,
        "whisper": WHISPER_SHA256,
    }
    for name, path in paths.items():
        verify_hash(path, expected[name], name)
    read_json(paths["config"])
    evidence = {
        name: {
            "path": str(path),
            "sha256": expected[name],
            "size_bytes": path.stat().st_size,
        }
        for name, path in paths.items()
    }
    return paths, evidence


def runtime_evidence() -> dict[str, Any]:
    if platform.python_version() != PYTHON_VERSION:
        raise CopKokoroPilotError(
            f"Python version mismatch: expected {PYTHON_VERSION}, observed {platform.python_version()}"
        )
    if platform.python_implementation() != PYTHON_IMPLEMENTATION:
        raise CopKokoroPilotError("Python implementation mismatch")
    executable_hash = sha256_file(Path(sys.executable))
    if executable_hash != PYTHON_EXECUTABLE_SHA256:
        raise CopKokoroPilotError(
            f"Python executable hash mismatch: expected {PYTHON_EXECUTABLE_SHA256}, observed {executable_hash}"
        )
    observed: dict[str, str] = {}
    for package, expected in RUNTIME_VERSIONS.items():
        try:
            observed[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise CopKokoroPilotError(f"pinned runtime package missing: {package}") from exc
        if observed[package] != expected:
            raise CopKokoroPilotError(
                f"runtime package mismatch for {package}: expected {expected}, observed {observed[package]}"
            )
    return {
        "python_version": PYTHON_VERSION,
        "python_implementation": PYTHON_IMPLEMENTATION,
        "python_executable": sys.executable,
        "python_executable_sha256": executable_hash,
        "package_versions": observed,
        "deterministic_algorithms_required": True,
        "torch_thread_count": 1,
        "offline_local_artifacts_only": True,
    }


def configured_g2p() -> Any:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    return g2p


def validate_g2p_passages(
    passages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    for source_token, binding in SOURCE_DIALECT_PRONUNCIATION_BINDINGS.items():
        if not any(source_token in str(passage["text"]) for passage in passages):
            raise CopKokoroPilotError(
                f"title-bound dialect token missing from controlled passages: {source_token}"
            )
        lexicon_key = str(binding["lexicon_key"])
        phonemes = str(binding["phonemes"])
        if PRONUNCIATION_OVERRIDES.get(lexicon_key) != phonemes:
            raise CopKokoroPilotError(
                f"title-bound dialect lookup binding changed: {source_token}"
            )
    g2p = configured_g2p()
    evidence: list[dict[str, Any]] = []
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
        if unresolved:
            raise CopKokoroPilotError(
                f"G2P fallback is disabled; unresolved tokens in {passage['passage_id']}: "
                + ", ".join(unresolved)
            )
        evidence.append(
            {
                "passage_id": passage["passage_id"],
                "source_text_sha256": passage["text_sha256"],
                "phoneme_sha256": sha256_text(str(phonemes)),
                "unresolved_tokens": [],
                "fallback_enabled": False,
            }
        )
    return evidence


def preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    artifact_dir: Path,
    whisper_cache_dir: Path,
    private_output_dir: Path,
    output: Path,
    paid_lock: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    if profile != PROFILE_ID:
        raise CopKokoroPilotError(f"unsupported profile: {profile}")
    private_dir = assert_private_audio_path(private_output_dir)
    chapter_path, passages = controlled_source(asset_root, slug)
    fingerprint = attempt_fingerprint(passages)
    ensure_not_repeated(fingerprint, output)
    artifacts, artifact_evidence = validate_artifacts(artifact_dir, whisper_cache_dir)
    lock = lock_snapshot(paid_lock)
    runtime = runtime_evidence()
    g2p_preflight = validate_g2p_passages(passages)
    payload = {
        "schema": "earnalism.cop_kokoro_representative.v1",
        "generated_at": utc_now(),
        "status": "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION",
        "scope": {
            "slug": ALLOWED_SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "language": LANGUAGE,
            "profile": PROFILE_ID,
            "passage_count": len(passages),
            "characters": EXPECTED_PASSAGE_CHARACTERS,
            "representative_only": True,
            "full_title_generated": False,
            "reader_live": True,
            "public_audio_hidden": True,
        },
        "source": {
            "chapter_path": str(chapter_path),
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "flattened_source_sha256": EXPECTED_FLATTENED_SHA256,
            "passages": [
                {
                    "passage_id": item["passage_id"],
                    "risk": item["risk"],
                    "characters": item["characters"],
                    "text_sha256": item["text_sha256"],
                }
                for item in passages
            ],
        },
        "engine": {
            "family": "open_weight_local_tts",
            "package": "kokoro",
            "package_version": KOKORO_VERSION,
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
            "source_dialect_pronunciation_bindings": SOURCE_DIALECT_PRONUNCIATION_BINDINGS,
            "g2p_fallback_enabled": False,
            "attempt_fingerprint": fingerprint,
            "superseded_pre_synthesis_attempts": SUPERSEDED_PRE_SYNTHESIS_ATTEMPTS,
            "selection_evidence": {
                "same_author_prior_title": "the-gift-of-the-magi",
                "same_author_voice": "af_bella",
                "representative_asr_scores": [10.0, 10.0, 10.0, 10.0],
                "representative_listening_overall": [9.6, 9.6, 9.5, 9.5],
                "minimum_confidence": 0.95,
                "fatal_flags": [],
                "cop_specific_change": "ironic-restraint profile at speed 0.98 with four new title-bound passages",
            },
            "materially_distinct_from_prior": {
                "prior_family": "google_managed_tts",
                "current_family": "open_weight_local_kokoro",
                "prior_fingerprints": sorted(KNOWN_GOOGLE_FINGERPRINTS),
                "distinct": True,
            },
        },
        "asr_contract": {
            "model": WHISPER_MODEL,
            "model_sha256": WHISPER_SHA256,
            "source_score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "first_words_required": True,
            "last_words_required": True,
            "ordered_content_integrity_required": True,
            "initial_prompt_sha256": sha256_text(ASR_VOCABULARY_PROMPT),
        },
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "g2p_preflight_evidence": g2p_preflight,
        "rights": {
            "model_and_voicepack_license": "Apache-2.0",
            "private_audition_allowed": True,
            "title_text_rights_basis": "controlled_publication_tier_A",
            "production_risk_acceptance_bound": False,
            "production_release_approved": False,
            "public_disclosure_required_if_later_approved": "AI voice",
        },
        "safety": {
            "provider_calls": 0,
            "estimated_tts_provider_cost_usd": 0.0,
            "paid_tts_lock": lock,
            "paid_tts_lock_touched": False,
            "private_output_dir": str(private_dir),
            "audio_generated": False,
            "asr_run": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "browser_or_system_speech_fallback": False,
        },
        "blockers_to_release": [
            "REPRESENTATIVE_AUDIO_NOT_GENERATED",
            "REPRESENTATIVE_ASR_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
            "OWNER_10_TARGET_NOT_VERIFIED",
        ],
    }
    return payload, passages, artifacts


def wav_metrics(path: Path) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415

    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="int16", always_2d=True)
    frames = int(data.shape[0])
    channels = int(data.shape[1])
    if rate != SAMPLE_RATE or channels != 1 or info.subtype != "PCM_16" or frames <= 0:
        raise CopKokoroPilotError(f"invalid private WAV format: {path}")
    samples = data[:, 0].astype(np.int64)
    absolute = np.abs(samples)
    peak = int(absolute.max())
    clipped = int(np.count_nonzero(absolute >= 32760))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    return {
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": 2,
        "duration_seconds": round(frames / rate, 6),
        "size_bytes": path.stat().st_size,
        "audio_sha256": sha256_file(path),
        "peak_fraction": round(peak / 32767, 6),
        "rms_fraction": round(rms / 32767, 6),
        "clipped_sample_fraction": round(clipped / frames, 8),
        "objective_format_pass": clipped == 0 and peak > 0 and rms / 32767 >= 0.001,
    }


def _install_local_filelock_stub() -> types.ModuleType | None:
    stub = types.ModuleType("filelock")

    class LocalArtifactOnlyFileLock:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.lock_file = args[0] if args else None

        def acquire(self, *args: Any, **kwargs: Any) -> "LocalArtifactOnlyFileLock":
            return self

        def release(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "LocalArtifactOnlyFileLock":
            return self.acquire()

        def __exit__(self, *args: Any) -> None:
            self.release()

    class LocalArtifactOnlyTimeout(TimeoutError):
        pass

    stub.BaseFileLock = LocalArtifactOnlyFileLock
    stub.FileLock = LocalArtifactOnlyFileLock
    stub.SoftFileLock = LocalArtifactOnlyFileLock
    stub.Timeout = LocalArtifactOnlyTimeout
    previous = sys.modules.get("filelock")
    sys.modules["filelock"] = stub
    return previous


def synthesize(
    passages: Sequence[Mapping[str, Any]], artifacts: Mapping[str, Path], private_dir: Path
) -> list[dict[str, Any]]:
    previous_filelock = _install_local_filelock_stub()
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from kokoro import KModel, KPipeline  # noqa: PLC0415
    finally:
        if previous_filelock is None:
            sys.modules.pop("filelock", None)
        else:
            sys.modules["filelock"] = previous_filelock
    private_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = KModel(config=str(artifacts["config"]), model=str(artifacts["model"]))
    pipeline = KPipeline(lang_code="a", model=model, repo_id=None)
    pipeline.g2p = configured_g2p()
    voice_tensor = torch.load(str(artifacts["voice"]), map_location="cpu", weights_only=True)
    prepared: list[tuple[Mapping[str, Any], Any]] = []
    for passage in passages:
        _phonemes, tokens = pipeline.g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        if unresolved:
            raise CopKokoroPilotError(
                f"G2P fallback is disabled; unresolved tokens in {passage['passage_id']}: "
                + ", ".join(unresolved)
            )
        prepared.append((passage, tokens))
    results: list[dict[str, Any]] = []
    for passage, tokens in prepared:
        chunks: list[Any] = []
        phonemes: list[str] = []
        for item in pipeline.generate_from_tokens(tokens, voice=voice_tensor, speed=SPEED):
            if item.audio is None:
                raise CopKokoroPilotError(f"Kokoro returned no audio: {passage['passage_id']}")
            chunks.append(item.audio.detach().cpu().numpy())
            phonemes.append(str(item.phonemes or ""))
        if not chunks:
            raise CopKokoroPilotError(f"Kokoro returned zero chunks: {passage['passage_id']}")
        target = private_dir / f"{passage['passage_id']}.wav"
        sf.write(target, np.concatenate(chunks), SAMPLE_RATE, subtype="PCM_16")
        results.append(
            {
                "passage_id": passage["passage_id"],
                "source_text_sha256": passage["text_sha256"],
                "characters": passage["characters"],
                "audio_path": str(target),
                "phoneme_sha256": sha256_text("".join(phonemes)),
                "g2p_fallback_enabled": False,
                **wav_metrics(target),
            }
        )
    return results


def lexical_tokens(text: str) -> list[str]:
    normalized = (
        text.lower().replace("’", "'").replace("‘", "'").replace("—", " ").replace("–", " ")
    )
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", normalized)


def ordered_token_integrity(source: str, transcript: str) -> dict[str, Any]:
    source_tokens = lexical_tokens(source)
    transcript_tokens = lexical_tokens(transcript)
    matcher = SequenceMatcher(None, source_tokens, transcript_tokens, autojunk=False)
    operations: list[dict[str, Any]] = []
    equal_tokens = 0
    for tag, source_start, source_end, transcript_start, transcript_end in matcher.get_opcodes():
        if tag == "equal":
            equal_tokens += source_end - source_start
            continue
        operations.append(
            {
                "operation": tag,
                "source_range": [source_start, source_end],
                "transcript_range": [transcript_start, transcript_end],
                "source_tokens": source_tokens[source_start:source_end],
                "transcript_tokens": transcript_tokens[transcript_start:transcript_end],
            }
        )
    source_count = Counter(source_tokens)
    transcript_count = Counter(transcript_tokens)
    missing = {token: count - transcript_count[token] for token, count in source_count.items() if count > transcript_count[token]}
    unexpected = {token: count - source_count[token] for token, count in transcript_count.items() if count > source_count[token]}
    duplicate = {token: transcript_count[token] - count for token, count in source_count.items() if transcript_count[token] > count}
    available_positions: dict[str, list[int]] = {}
    for index, token in enumerate(source_tokens):
        available_positions.setdefault(token, []).append(index)
    consumed: Counter[str] = Counter()
    common_positions: list[int] = []
    for token in transcript_tokens:
        positions = available_positions.get(token, [])
        occurrence = consumed[token]
        if occurrence < len(positions):
            common_positions.append(positions[occurrence])
            consumed[token] += 1
    coverage = equal_tokens / len(source_tokens) if source_tokens else 0.0
    precision = equal_tokens / len(transcript_tokens) if transcript_tokens else 0.0
    harmonic = 2 * coverage * precision / (coverage + precision) if coverage + precision else 0.0
    first_window = min(5, len(source_tokens), len(transcript_tokens))
    last_window = min(5, len(source_tokens), len(transcript_tokens))
    exact = source_tokens == transcript_tokens
    return {
        "score": round(10 * harmonic, 4),
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "source_token_count": len(source_tokens),
        "transcript_token_count": len(transcript_tokens),
        "equal_token_count": equal_tokens,
        "first_words_match": bool(first_window and source_tokens[:first_window] == transcript_tokens[:first_window]),
        "last_words_match": bool(last_window and source_tokens[-last_window:] == transcript_tokens[-last_window:]),
        "ordered_content_integrity_pass": exact,
        "no_missing_content": not missing,
        "no_duplicate_content": not duplicate,
        "no_reordered_content": common_positions == sorted(common_positions),
        "no_unexpected_content": not unexpected,
        "missing_tokens": missing,
        "duplicate_tokens": duplicate,
        "unexpected_tokens": unexpected,
        "ordered_alignment_operations": operations,
    }


def run_asr(
    samples: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_cache_dir: Path,
) -> dict[str, Any]:
    import whisper  # noqa: PLC0415

    by_id = {str(item["passage_id"]): item for item in passages}
    model = whisper.load_model(WHISPER_MODEL, download_root=str(whisper_cache_dir.resolve()))
    reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        passage = by_id[passage_id]
        audio = assert_private_audio_path(Path(str(sample["audio_path"])))
        verify_hash(audio, str(sample["audio_sha256"]), f"sample {passage_id}")
        result = model.transcribe(
            str(audio),
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=ASR_VOCABULARY_PROMPT,
            word_timestamps=True,
        )
        transcript = str(result.get("text") or "").strip()
        metrics = ordered_token_integrity(str(passage["text"]), transcript)
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
        reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": sample["audio_sha256"],
                "source_text_sha256": passage["text_sha256"],
                "transcript": transcript,
                "transcript_sha256": sha256_text(transcript),
                **metrics,
                "pass": passed,
            }
        )
    return {
        "status": "PASS" if all(item["pass"] for item in reports) else "FAIL",
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_derived": True,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "prompt_sha256": sha256_text(ASR_VOCABULARY_PROMPT),
        "reports": reports,
    }


def apply_source_equivalences(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    if passage_id not in SOURCE_EQUIVALENCE_POLICY:
        raise CopKokoroPilotError(
            f"no source-equivalence policy exists for {passage_id}"
        )
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in SOURCE_EQUIVALENCE_POLICY[passage_id]:
        updated, count = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if count:
            evaluated = updated
            applications.append(
                {
                    "pattern": rule["pattern"],
                    "replacement": rule["replacement"],
                    "reason": rule["reason"],
                    "match_count": count,
                }
            )
    return evaluated, applications


def asr_reverify_config_fingerprint(
    samples: Sequence[Mapping[str, Any]],
) -> str:
    contract = {
        "contract": "earnalism.cop_existing_audio_asr_reverify.v1",
        "slug": ALLOWED_SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "passage_hashes": list(EXPECTED_PASSAGE_HASHES),
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_hashes": {
            str(item["passage_id"]): str(item["audio_sha256"]) for item in samples
        },
        "prompt_policy": ASR_REVERIFY_POLICY,
        "prompt_sha256": sha256_text(ASR_VOCABULARY_PROMPT),
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "unexpected_speech_may_be_discarded": False,
    }
    return sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def validate_existing_samples(
    payload: Mapping[str, Any], passages: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if (payload.get("scope") or {}).get("slug") != ALLOWED_SLUG:
        raise CopKokoroPilotError("existing evidence is for the wrong slug")
    expected_attempt = attempt_fingerprint(passages)
    if (payload.get("engine") or {}).get("attempt_fingerprint") != expected_attempt:
        raise CopKokoroPilotError("existing evidence attempt fingerprint changed")
    safety = payload.get("safety") or {}
    if safety.get("audio_generated") is not True:
        raise CopKokoroPilotError("existing evidence does not prove generated audio")
    if safety.get("provider_calls") != 0:
        raise CopKokoroPilotError("existing evidence records provider calls")
    if safety.get("upload_performed") is not False:
        raise CopKokoroPilotError("existing evidence records an upload")
    if safety.get("publication_performed") is not False:
        raise CopKokoroPilotError("existing evidence records publication")
    samples_value = payload.get("samples")
    if not isinstance(samples_value, list) or len(samples_value) != len(PASSAGE_SPECS):
        raise CopKokoroPilotError("exactly four existing sample records are required")
    passage_by_id = {str(item["passage_id"]): item for item in passages}
    sample_by_id: dict[str, dict[str, Any]] = {}
    for value in samples_value:
        if not isinstance(value, dict):
            raise CopKokoroPilotError("existing sample record is not an object")
        passage_id = str(value.get("passage_id") or "")
        if passage_id in sample_by_id:
            raise CopKokoroPilotError(f"duplicate existing sample: {passage_id}")
        sample_by_id[passage_id] = value
    if set(sample_by_id) != set(EXPECTED_EXISTING_AUDIO_HASHES):
        raise CopKokoroPilotError("existing sample IDs changed")
    ordered_samples: list[dict[str, Any]] = []
    snapshot: dict[str, str] = {}
    for spec in PASSAGE_SPECS:
        passage_id = str(spec["passage_id"])
        sample = sample_by_id[passage_id]
        expected_audio_hash = EXPECTED_EXISTING_AUDIO_HASHES[passage_id]
        if sample.get("audio_sha256") != expected_audio_hash:
            raise CopKokoroPilotError(
                f"existing evidence audio hash changed: {passage_id}"
            )
        if sample.get("source_text_sha256") != passage_by_id[passage_id]["text_sha256"]:
            raise CopKokoroPilotError(
                f"existing evidence source binding changed: {passage_id}"
            )
        if sample.get("objective_format_pass") is not True:
            raise CopKokoroPilotError(
                f"existing audio did not pass objective format QA: {passage_id}"
            )
        audio = assert_private_audio_path(Path(str(sample.get("audio_path") or "")))
        if audio.name != f"{passage_id}.wav":
            raise CopKokoroPilotError(
                f"existing sample filename changed: {passage_id}"
            )
        verify_hash(audio, expected_audio_hash, f"existing sample {passage_id}")
        snapshot[passage_id] = sha256_file(audio)
        ordered_samples.append(dict(sample))
    return ordered_samples, snapshot


def run_asr_reverify(
    samples: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_cache_dir: Path,
) -> dict[str, Any]:
    import whisper  # noqa: PLC0415

    by_id = {str(item["passage_id"]): item for item in passages}
    model = whisper.load_model(
        WHISPER_MODEL, download_root=str(whisper_cache_dir.resolve())
    )
    config_fingerprint = asr_reverify_config_fingerprint(samples)
    reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        passage = by_id[passage_id]
        audio = assert_private_audio_path(Path(str(sample["audio_path"])))
        verify_hash(audio, str(sample["audio_sha256"]), f"sample {passage_id}")
        policy = ASR_REVERIFY_POLICY[passage_id]
        initial_prompt = (
            ASR_VOCABULARY_PROMPT
            if policy["prompt_mode"] == "canonical_vocabulary_prompt"
            else None
        )
        decode_options: dict[str, Any] = {
            "beam_size": int(policy["beam_size"]),
            "patience": float(policy["patience"]),
        }
        if policy["hallucination_silence_threshold"] is not None:
            decode_options["hallucination_silence_threshold"] = float(
                policy["hallucination_silence_threshold"]
            )
        result = model.transcribe(
            str(audio),
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
            word_timestamps=True,
            **decode_options,
        )
        raw_transcript = str(result.get("text") or "").strip()
        evaluated_transcript, equivalences = apply_source_equivalences(
            passage_id, raw_transcript
        )
        metrics = ordered_token_integrity(
            str(passage["text"]), evaluated_transcript
        )
        segments = (
            result.get("segments")
            if isinstance(result.get("segments"), list)
            else []
        )
        no_speech_probabilities = [
            float(item["no_speech_prob"])
            for item in segments
            if isinstance(item, dict)
            and isinstance(item.get("no_speech_prob"), (int, float))
        ]
        waiter_forbidden_tail = bool(
            passage_id == "waiter_dialogue"
            and re.search(
                r"\bthank you for (?:watching|joining us today)\b",
                raw_transcript,
                flags=re.IGNORECASE,
            )
        )
        waiter_unprompted_contract = bool(
            passage_id != "waiter_dialogue"
            or (
                policy["prompt_mode"] == "no_prompt"
                and not waiter_forbidden_tail
                and metrics["no_unexpected_content"] is True
            )
        )
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
            and waiter_unprompted_contract
        )
        reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": sample["audio_sha256"],
                "source_text_sha256": passage["text_sha256"],
                "prompt_mode": policy["prompt_mode"],
                "decode_options": decode_options,
                "prompt_sha256": (
                    sha256_text(ASR_VOCABULARY_PROMPT)
                    if initial_prompt
                    else None
                ),
                "raw_transcript": raw_transcript,
                "raw_transcript_sha256": sha256_text(raw_transcript),
                "evaluated_transcript": evaluated_transcript,
                "evaluated_transcript_sha256": sha256_text(evaluated_transcript),
                "source_equivalences_applied": equivalences,
                "unexpected_speech_discarded": False,
                "waiter_forbidden_trailing_speech_detected": waiter_forbidden_tail,
                "waiter_unprompted_raw_contract_pass": waiter_unprompted_contract,
                "segment_count": len(segments),
                "segment_no_speech_probabilities": no_speech_probabilities,
                "max_no_speech_probability": (
                    round(max(no_speech_probabilities), 6)
                    if no_speech_probabilities
                    else None
                ),
                **metrics,
                "pass": passed,
            }
        )
    return {
        "status": "PASS" if all(item["pass"] for item in reports) else "FAIL",
        "mode": "ASR_REVERIFY_EXISTING_AUDIO_ONLY",
        "config_fingerprint": config_fingerprint,
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_derived": True,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "prompt_policy": ASR_REVERIFY_POLICY,
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "diagnostic_summary": ASR_DIAGNOSTIC_SUMMARY,
        "unexpected_speech_may_be_discarded": False,
        "reports": reports,
    }


def asr_reverify_existing(
    *,
    payload: dict[str, Any],
    asset_root: Path,
    whisper_cache_dir: Path,
    paid_lock: Path,
) -> tuple[int, dict[str, Any]]:
    _chapter, passages = controlled_source(asset_root, ALLOWED_SLUG)
    samples, audio_before = validate_existing_samples(payload, passages)
    fingerprint = asr_reverify_config_fingerprint(samples)
    if (
        (payload.get("asr") or {}).get("mode")
        == "ASR_REVERIFY_EXISTING_AUDIO_ONLY"
        and (payload.get("asr") or {}).get("config_fingerprint") == fingerprint
    ):
        raise CopKokoroPilotError("this exact ASR-only reverify already executed")
    prior_asr = payload.get("asr")
    if not isinstance(prior_asr, dict) or prior_asr.get("status") != "FAIL":
        raise CopKokoroPilotError("a recorded failed prior ASR result is required")
    whisper_path = whisper_cache_dir.expanduser().resolve() / WHISPER_FILENAME
    verify_hash(whisper_path, WHISPER_SHA256, "whisper")
    runtime = runtime_evidence()
    lock_before = lock_snapshot(paid_lock)
    repaired_asr = run_asr_reverify(samples, passages, whisper_cache_dir)
    lock_after = lock_snapshot(paid_lock)
    if lock_after != lock_before:
        raise CopKokoroPilotError("paid_tts.lock changed during ASR-only repair")
    _samples_after, audio_after = validate_existing_samples(payload, passages)
    if audio_after != audio_before:
        raise CopKokoroPilotError("private audio changed during ASR-only repair")
    payload.setdefault("asr_history", []).append(
        {
            "status": prior_asr.get("status"),
            "model": prior_asr.get("model"),
            "model_sha256": prior_asr.get("model_sha256"),
            "prompt_sha256": prior_asr.get("prompt_sha256"),
            "reports": prior_asr.get("reports"),
            "preserved_before_reverify": True,
        }
    )
    payload["asr"] = repaired_asr
    payload["runtime_evidence"] = runtime
    payload["safety"].update(
        {
            "audio_generated": True,
            "asr_run": True,
            "asr_reverify_existing_performed": True,
            "resynthesis_performed": False,
            "provider_calls": 0,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "paid_tts_lock": lock_after,
            "paid_tts_lock_unchanged": True,
            "audio_hashes_unchanged": True,
        }
    )
    payload["blockers_to_release"] = [
        blocker
        for blocker in payload["blockers_to_release"]
        if blocker
        not in {
            "REPRESENTATIVE_ASR_OBJECTIVE_QA_FAIL",
            "ASR_ONLY_REPAIR_FAILED",
            "COP_REPRESENTATIVE_LANE_CLOSED",
        }
    ]
    if repaired_asr["status"] == "PASS":
        payload["status"] = (
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        )
        return 0, payload
    payload["status"] = "PRIVATE_REPRESENTATIVE_ASR_ONLY_REPAIR_FAIL_CLOSED"
    payload["blockers_to_release"][:0] = [
        "ASR_ONLY_REPAIR_FAILED",
        "COP_REPRESENTATIVE_LANE_CLOSED",
    ]
    return 2, payload


def execute_private_representative(
    *,
    payload: dict[str, Any],
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_output_dir: Path,
    whisper_cache_dir: Path,
    paid_lock: Path,
) -> tuple[int, dict[str, Any]]:
    lock_before = lock_snapshot(paid_lock)
    samples = synthesize(passages, artifacts, assert_private_audio_path(private_output_dir))
    asr = run_asr(samples, passages, whisper_cache_dir)
    lock_after = lock_snapshot(paid_lock)
    if lock_after != lock_before:
        raise CopKokoroPilotError("paid_tts.lock changed during local execution")
    payload["samples"] = samples
    payload["asr"] = asr
    payload["safety"].update(
        {
            "audio_generated": True,
            "asr_run": True,
            "paid_tts_lock_unchanged": True,
            "provider_calls": 0,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        }
    )
    payload["blockers_to_release"] = [
        blocker
        for blocker in payload["blockers_to_release"]
        if blocker not in {"REPRESENTATIVE_AUDIO_NOT_GENERATED", "REPRESENTATIVE_ASR_NOT_RUN"}
    ]
    if asr["status"] == "PASS" and all(item["objective_format_pass"] for item in samples):
        payload["status"] = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        return 0, payload
    payload["status"] = "PRIVATE_REPRESENTATIVE_OBJECTIVE_QA_FAIL"
    payload["blockers_to_release"].insert(0, "REPRESENTATIVE_ASR_OBJECTIVE_QA_FAIL")
    return 2, payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--asr-reverify-existing", action="store_true")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--whisper-cache-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paid-lock", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.slug != ALLOWED_SLUG:
            raise CopKokoroPilotError(f"slug is not allowed: {args.slug}")
        if args.profile != PROFILE_ID:
            raise CopKokoroPilotError(f"unsupported profile: {args.profile}")
        if args.asr_reverify_existing:
            payload = read_json(args.output)
            code, payload = asr_reverify_existing(
                payload=payload,
                asset_root=args.asset_root.resolve(),
                whisper_cache_dir=args.whisper_cache_dir,
                paid_lock=args.paid_lock,
            )
            atomic_write_json(args.output, payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return code
        if args.artifact_dir is None or args.private_output_dir is None:
            raise CopKokoroPilotError(
                "--artifact-dir and --private-output-dir are required for preflight or execute"
            )
        payload, passages, artifacts = preflight(
            asset_root=args.asset_root.resolve(),
            slug=args.slug,
            profile=args.profile,
            artifact_dir=args.artifact_dir,
            whisper_cache_dir=args.whisper_cache_dir,
            private_output_dir=args.private_output_dir,
            output=args.output,
            paid_lock=args.paid_lock,
        )
        code = 0
        if args.execute:
            code, payload = execute_private_representative(
                payload=payload,
                passages=passages,
                artifacts=artifacts,
                private_output_dir=args.private_output_dir,
                whisper_cache_dir=args.whisper_cache_dir,
                paid_lock=args.paid_lock,
            )
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code
    except CopKokoroPilotError as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
