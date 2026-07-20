#!/usr/bin/env python3
"""Build The Tell-Tale Heart's private, source-bound Kokoro preflight.

This module is intentionally preflight-only.  It validates canonical catalog,
rights, manuscript, prior-attempt, runtime, and local artifact evidence, then
emits a deterministic contract for one future four-passage private audition.
It contains no synthesis, ASR, listening, upload, publication, or paid-lock
code path.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SLUG = "the-tell-tale-heart"
TITLE = "The Tell-Tale Heart"
AUTHOR = "Edgar Allan Poe"
LANGUAGE = "en"
PROFILE = "tell-tale-bf-emma-controlled-gothic-v1"

ORIGIN_SOURCE_SHA256 = "f5d856baf4abec894c1fdc82f8676a416dc96efd3708162c04bcde0ff0a4579b"
RAW_SOURCE_SHA256 = "be8259855845762a7a1c6e5e1bd45d43bbd04c7d769427b25132e2bf514af1f8"
NORMALIZED_SOURCE_SHA256 = "6aa43cf6dcf4c6fba097237c01938ab5269a7edda16e4006db05b5a56c7e164e"
RAW_SOURCE_CHARACTERS = 11_486
NORMALIZED_SOURCE_CHARACTERS = 11_135
WORD_COUNT = 2_155

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "bf_emma"
VOICE_SHA256 = "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
WHISPER_MODEL = "medium.en"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

PREVIOUS_VOICES = {
    "af_bella": {
        "sha256": "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        "cosine_similarity_to_selected": 0.6428000927,
    },
    "af_sarah": {
        "sha256": "49bd364ea3be9eb3e9685e8f9a15448c4883112a7c0ff7ab139fa4088b08cef9",
        "cosine_similarity_to_selected": 0.6364917159,
    },
}

SPEED = 0.96
RANDOM_SEED = 2026072001
ASR_SOURCE_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98

PASSAGE_SPECS = (
    {
        "passage_id": "opening_unreliable_sanity",
        "start": None,
        "end": "observe how healthily—how calmly I can tell you the whole story.",
        "characters": 386,
        "sha256": "1bd845cd383b10550ac7fe03ccfafc01d3059c7ae9f473a4a371c20782f6a524",
        "risk": "fractured punctuation, repeated emphasis, and calm-versus-agitated contrast",
    },
    {
        "passage_id": "bedroom_suspense_dialogue",
        "start": "I fairly chuckled at the idea;",
        "end": "and the old man sprang up in bed, crying out—“Who’s there?”",
        "characters": 534,
        "sha256": "7b2efa882aed81bb447c8d00fee89dfc011d48ffb2c2ba0f1d2b202918125029",
        "risk": "stealth pacing, parentheses, repetition, and a sudden dialogue transition",
    },
    {
        "passage_id": "heartbeat_crescendo",
        "start": "Meantime the hellish tattoo of the heart increased.",
        "end": "the sound would be heard by a neighbour!",
        "characters": 619,
        "sha256": "90686993699298d204d639da36bf779b3ae52397e99e2d6e1b5fdb5a316ab639",
        "risk": "accelerating repetitions that must intensify without rushing or mechanical cadence",
    },
    {
        "passage_id": "final_confession",
        "start": "It grew louder—louder—louder!",
        "end": "It is the beating of his hideous heart!”",
        "characters": 610,
        "sha256": "3e0f8c27ceca25a940b8d411c6bf015a46ba188a513273748c9666f7a7695745",
        "risk": "sustained emotional escalation, italicized emphasis, and the shouted confession",
    },
)
PASSAGE_CHARACTERS = 2_149

PRIOR_GOOGLE_ATTEMPTS = (
    {
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "scope": "contextual_representative_audition",
        "attempt_fingerprint": "4f7b571d8625924e82cb32ab3e1e3d33ae5123fc61c05a548dd0c4f2e9b304c4",
        "scores": [9.5, 8.4, 9.4, 9.6],
        "minimum_score": 8.4,
        "status": "BLOCKED_LISTENING_QA",
    },
    {
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "scope": "final_slow_contextual_representative_audition",
        "attempt_fingerprint": "fd54248900cc4c9cc174fe327635781ac7749625e1bfd3635c897fb126ab632b",
        "scores": [9.4, 8.5, 9.4, 8.8],
        "minimum_score": 8.5,
        "status": "BLOCKED_LISTENING_QA",
    },
)

PINNED_PYTHON_VERSION = "3.11.15"
PINNED_PYTHON_SHA256 = "50de159a94723fa71090030ac642b101e27f8d29488ec4bdae91edfa1e86dbbd"
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
    "internal/audiobook_lab/private_runs/kokoro/the-tell-tale-heart/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-tell-tale-heart_kokoro_bf_emma_representative_preflight_v1.json"
)

NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/the-tell-tale-heart_release_gate_evidence.json",
)


class TellTalePreflightError(RuntimeError):
    """Raised when any immutable preflight binding changes."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


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
        raise TellTalePreflightError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TellTalePreflightError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temp, path)


def verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise TellTalePreflightError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise TellTalePreflightError(
            f"{label} SHA-256 mismatch: expected {expected}, observed {observed}"
        )


def assert_private_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"{resolved.as_posix().lower()}/"
    forbidden = ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/")
    if any(item in rendered for item in forbidden):
        raise TellTalePreflightError(f"public audio path is forbidden: {resolved}")
    private_marker = "/internal/audiobook_lab/private_runs/"
    temp_root = Path(tempfile.gettempdir()).resolve()
    if private_marker not in rendered and not (
        resolved == temp_root or temp_root in resolved.parents
    ):
        raise TellTalePreflightError(
            "future audio output must stay under the private run root or OS temp root"
        )
    return resolved


def _expect(mapping: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    for key, value in expected.items():
        if mapping.get(key) != value:
            raise TellTalePreflightError(
                f"{label} changed for {key}: expected {value!r}, observed {mapping.get(key)!r}"
            )


def controlled_source(asset_root: Path, slug: str) -> tuple[Path, list[dict[str, Any]]]:
    if slug != SLUG:
        raise TellTalePreflightError(f"only {SLUG} is permitted; observed {slug}")
    publication = asset_root / "data/controlled_publications" / SLUG
    book = read_json(publication / "public_book.json")
    _expect(
        book,
        {
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
            "source_hash": ORIGIN_SOURCE_SHA256,
            "rights_tier": "A",
            "verification_status": "approved",
        },
        "controlled catalog truth",
    )
    source_evidence = read_json(publication / "source_evidence.json")
    _expect(
        source_evidence,
        {
            "slug": SLUG,
            "source_hash": ORIGIN_SOURCE_SHA256,
            "rights_basis": "Edgar Allan Poe died 1849; first published 1843. Public domain in India and the U.S.",
            "reader_facing_boilerplate_removed": True,
        },
        "source rights evidence",
    )
    approval = read_json(publication / "approval_evidence.json")
    _expect(
        approval,
        {
            "slug": SLUG,
            "approved_to_publish": True,
            "rights_tier": "A",
            "verification_status": "approved",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        },
        "approval evidence",
    )
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    _expect(
        chapter,
        {
            "id": "chapter-001",
            "bookSlug": SLUG,
            "title": TITLE,
            "language": LANGUAGE,
            "content_hash": RAW_SOURCE_SHA256,
            "sourceSha256": ORIGIN_SOURCE_SHA256,
            "sanitizedSha256": RAW_SOURCE_SHA256,
            "word_count": WORD_COUNT,
            "processing_status": "ready",
            "processing_warnings": [],
        },
        "controlled chapter truth",
    )
    manuscript = chapter.get("content")
    if not isinstance(manuscript, str):
        raise TellTalePreflightError("controlled manuscript is missing")
    if len(manuscript) != RAW_SOURCE_CHARACTERS or sha256_text(manuscript) != RAW_SOURCE_SHA256:
        raise TellTalePreflightError("controlled manuscript bytes changed")
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    if (
        len(normalized) != NORMALIZED_SOURCE_CHARACTERS
        or sha256_text(normalized) != NORMALIZED_SOURCE_SHA256
    ):
        raise TellTalePreflightError("normalized manuscript binding changed")
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start_marker = spec["start"]
        start = 0 if start_marker is None else normalized.find(str(start_marker))
        end_start = normalized.find(str(spec["end"]), start)
        if start < 0 or end_start < 0:
            raise TellTalePreflightError(
                f"canonical passage markers changed: {spec['passage_id']}"
            )
        text = normalized[start : end_start + len(str(spec["end"]))]
        if len(text) != spec["characters"] or sha256_text(text) != spec["sha256"]:
            raise TellTalePreflightError(
                f"canonical passage binding changed: {spec['passage_id']}"
            )
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "characters": len(text),
                "text": text,
                "text_sha256": spec["sha256"],
                "risk": spec["risk"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise TellTalePreflightError("representative passage total changed")
    return chapter_path, passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.kokoro_tell_tale_private_preflight.v1",
        "slug": SLUG,
        "profile": PROFILE,
        "source_sha256": RAW_SOURCE_SHA256,
        "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
        "passage_hashes": [item["text_sha256"] for item in passages],
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "config_sha256": CONFIG_SHA256,
        "voice": VOICE,
        "voice_sha256": VOICE_SHA256,
        "whisper_model": WHISPER_MODEL,
        "whisper_sha256": WHISPER_SHA256,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "scope": "four_passage_private_representative_preflight_only",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


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
    historical = {item["attempt_fingerprint"] for item in PRIOR_GOOGLE_ATTEMPTS}
    if fingerprint in historical:
        raise TellTalePreflightError("new preflight repeats a closed Google fingerprint")
    for evidence in NO_REPEAT_FILES:
        if evidence.is_file() and fingerprint in set(_fingerprints(read_json(evidence))):
            raise TellTalePreflightError(f"attempt fingerprint already exists in {evidence}")
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        if prior_fingerprint == fingerprint and bool((prior.get("safety") or {}).get("audio_generated")):
            raise TellTalePreflightError("this exact fingerprint already generated audio")


def validate_prior_attempts(asset_root: Path) -> None:
    evidence = read_json(
        asset_root
        / "internal/audiobook_lab/sprint1_publication/title_runs/"
        "the-tell-tale-heart_release_gate_evidence.json"
    )
    observed = evidence.get("provider_attempts")
    if not isinstance(observed, list) or len(observed) != len(PRIOR_GOOGLE_ATTEMPTS):
        raise TellTalePreflightError("prior Tell-Tale attempt count changed")
    for expected, item in zip(PRIOR_GOOGLE_ATTEMPTS, observed):
        if not isinstance(item, dict):
            raise TellTalePreflightError("invalid prior Tell-Tale attempt record")
        _expect(item, expected, "prior Tell-Tale attempt")


def validate_artifacts(
    artifact_dir: Path, whisper_cache_dir: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    root = artifact_dir.expanduser().resolve()
    paths = {
        "model": root / "kokoro-v1_0.pth",
        "config": root / "config.json",
        "voice": root / "voices/bf_emma.pt",
        "whisper": whisper_cache_dir.expanduser().resolve() / "medium.en.pt",
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
    for name, prior in PREVIOUS_VOICES.items():
        prior_path = root / f"voices/{name}.pt"
        verify_hash(prior_path, str(prior["sha256"]), f"prior voice {name}")
        if expected["voice"] == prior["sha256"]:
            raise TellTalePreflightError(f"selected voice is not new relative to {name}")
    return paths, {
        name: {
            "path": str(path),
            "sha256": expected[name],
            "size_bytes": path.stat().st_size,
        }
        for name, path in paths.items()
    }


def runtime_evidence() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    executable_hash = sha256_file(executable)
    pinned = (
        platform.python_version() == PINNED_PYTHON_VERSION
        and platform.python_implementation() == "CPython"
        and executable_hash == PINNED_PYTHON_SHA256
    )
    packages: dict[str, str | None] = {}
    for package, expected in RUNTIME_VERSIONS.items():
        try:
            observed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            observed = None
        packages[package] = observed
        if pinned and observed != expected:
            raise TellTalePreflightError(
                f"pinned runtime package mismatch for {package}: expected {expected}, observed {observed}"
            )
    return {
        "status": "PINNED_EXECUTION_RUNTIME_VERIFIED" if pinned else "SYSTEM_TEST_RUNTIME_NOT_EXECUTION_READY",
        "pinned_execution_runtime_verified": pinned,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": str(executable),
        "python_executable_sha256": executable_hash,
        "expected_python_version": PINNED_PYTHON_VERSION,
        "expected_python_executable_sha256": PINNED_PYTHON_SHA256,
        "package_versions": packages,
        "expected_package_versions": RUNTIME_VERSIONS,
    }


def build_preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    artifact_dir: Path,
    whisper_cache_dir: Path,
    private_output_dir: Path,
    output: Path,
) -> dict[str, Any]:
    if profile != PROFILE:
        raise TellTalePreflightError(f"unsupported profile: {profile}")
    private_dir = assert_private_path(private_output_dir)
    chapter_path, passages = controlled_source(asset_root, slug)
    validate_prior_attempts(asset_root)
    fingerprint = attempt_fingerprint(passages)
    ensure_not_repeated(fingerprint, output)
    _paths, artifacts = validate_artifacts(artifact_dir, whisper_cache_dir)
    runtime = runtime_evidence()
    return {
        "schema": "earnalism.kokoro.tell_tale_private_preflight.v1",
        "generated_at": utc_now(),
        "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
        "go_no_go": "GO_PRIVATE_REPRESENTATIVE_ONLY",
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "language": LANGUAGE,
            "profile": PROFILE,
            "passage_count": len(passages),
            "characters": PASSAGE_CHARACTERS,
            "representative_only": True,
            "full_title_generated": False,
        },
        "source": {
            "chapter_path": str(chapter_path),
            "origin_source_sha256": ORIGIN_SOURCE_SHA256,
            "raw_source_sha256": RAW_SOURCE_SHA256,
            "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
            "word_count": WORD_COUNT,
            "rights_basis": "Edgar Allan Poe died 1849; first published 1843. Public domain in India and the U.S.",
            "passages": [
                {
                    "passage_id": item["passage_id"],
                    "characters": item["characters"],
                    "text_sha256": item["text_sha256"],
                    "risk": item["risk"],
                }
                for item in passages
            ],
        },
        "prior_attempt_audit": {
            "closed_attempts": list(PRIOR_GOOGLE_ATTEMPTS),
            "closed_attempt_count": len(PRIOR_GOOGLE_ATTEMPTS),
            "new_attempt_is_materially_different_provider_and_voice": True,
        },
        "engine": {
            "family": "open_weight_local_tts",
            "package": "kokoro",
            "package_version": "0.9.4",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256,
            "config_sha256": CONFIG_SHA256,
            "voice": VOICE,
            "voice_language": "British English",
            "voice_sha256": VOICE_SHA256,
            "speed": SPEED,
            "random_seed": RANDOM_SEED,
            "g2p_language_code_required_for_future_execution": "b",
            "g2p_british_required_for_future_execution": True,
            "g2p_fallback_enabled": False,
            "attempt_fingerprint": fingerprint,
        },
        "voice_selection": {
            "selected_voice": VOICE,
            "selected_voice_sha256": VOICE_SHA256,
            "official_voice_catalog_grade": "B-",
            "official_voice_catalog_training_hours": "HH",
            "title_suitability_rationale": (
                "The nameless first-person narrator does not impose a canonical gender. "
                "bf_emma is the only unused exact local British voice and is suited to "
                "Poe's controlled Gothic tension, whispered stealth, and escalating confession."
            ),
            "previous_voice_comparison": PREVIOUS_VOICES,
            "selected_voice_is_checksum_distinct_from_closed_local_voices": True,
        },
        "artifact_evidence": artifacts,
        "runtime_evidence": runtime,
        "rights": {
            "model_and_voicepack_license": "Apache-2.0",
            "official_model_card_url": f"https://huggingface.co/{MODEL_REPO}/tree/{MODEL_REVISION}",
            "official_voice_file_url": f"https://huggingface.co/{MODEL_REPO}/blob/{MODEL_REVISION}/voices/{VOICE}.pt",
            "private_audition_allowed": True,
            "commercial_use_allowed_under_recorded_license": True,
            "apache_notice_obligations_still_apply": True,
            "title_scoped_production_risk_acceptance_bound": False,
            "production_release_approved": False,
            "public_disclosure_required_if_later_approved": "AI voice",
        },
        "asr_contract": {
            "model": WHISPER_MODEL,
            "model_sha256": WHISPER_SHA256,
            "source_score_min": ASR_SOURCE_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "first_words_required": True,
            "last_words_required": True,
            "ordered_content_integrity_required": True,
            "estimated_sync_allowed": False,
        },
        "next_stage_contract": {
            "status": "CODE_REVIEWED_BRITISH_G2P_EXECUTOR_REQUIRED_BEFORE_SYNTHESIS",
            "scope": "these four exact source-bound passages only",
            "future_executor_requirements": [
                "pin this exact fingerprint and all artifact hashes",
                "use Kokoro language code b with British G2P",
                "disable every G2P fallback and refuse unresolved tokens",
                "write only beneath the recorded private output directory",
                "run local ASR before any paid listening QA",
            ],
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
        },
        "safety": {
            "private_output_dir": str(private_dir),
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "audio_generated": False,
            "asr_run": False,
            "listening_qa_run": False,
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
            "CANONICAL_FRONT_COVER_MISSING",
            "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
            "PRODUCTION_ENDPOINT_NOT_RUN",
            "BROWSER_PLAYBACK_GATE_NOT_RUN",
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="required safety mode")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--whisper-cache-dir", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--private-output-dir", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.preflight:
        raise TellTalePreflightError("--preflight is required; this script cannot execute audio")
    payload = build_preflight(
        asset_root=args.asset_root.resolve(),
        slug=args.slug,
        profile=args.profile,
        artifact_dir=args.artifact_dir,
        whisper_cache_dir=args.whisper_cache_dir,
        private_output_dir=args.private_output_dir,
        output=args.output,
    )
    atomic_write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
