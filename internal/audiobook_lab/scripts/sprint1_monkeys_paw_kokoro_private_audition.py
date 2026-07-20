#!/usr/bin/env python3
"""Run one source-bound private Kokoro pilot for The Monkey's Paw.

The contract pins the canonical three-chapter manuscript, four representative
passages, the local Kokoro model/voice, American fallback-free G2P, and local
Whisper.  It cannot call a provider, inspect or mutate ``paid_tts.lock``,
upload media, publish, or change release truth.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - installation guard
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_module(
    "earnalism_kokoro_title_base",
    SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py",
)

SLUG = "the-monkeys-paw"
TITLE = "The Monkey's Paw"
AUTHOR = "W.W. Jacobs"
LANGUAGE = "en"
PROFILE = "monkeys-paw-af-bella-gothic-v1"

ORIGIN_SOURCE_SHA256 = "e435de0511bd61d2373a445b0c5e054b747072357b5373e27b7a4b8a5b40cd01"
AGGREGATE_SOURCE_SHA256 = "993ea84df5163bddcb4d4579a78ee5fb4b5ad9002a9659f9ac2e2f73198ec6b7"
AGGREGATE_SOURCE_CHARACTERS = 22_075
NORMALIZED_SOURCE_SHA256 = "a3fb946efdc410958f47fab3a6ec613d7f2280cee06e1f60b079a5d908af29bd"
NORMALIZED_SOURCE_CHARACTERS = 21_700

CHAPTER_SPECS = (
    {
        "filename": "chapter-001.json",
        "id": "chapter-001",
        "title": "I",
        "sha256": "1184a3e5b2d86508fc2c6bceac7519235581387e02e31a2c2dbfab03628ac942",
        "characters": 9_629,
        "word_count": 1_770,
    },
    {
        "filename": "chapter-002.json",
        "id": "chapter-002",
        "title": "II",
        "sha256": "d0eafaa9c6af9c96bd56ce956a8f59ba94da1ec9e19b3e6cf38b4f8b206cc9ee",
        "characters": 5_330,
        "word_count": 957,
    },
    {
        "filename": "chapter-003.json",
        "id": "chapter-003",
        "title": "III",
        "sha256": "7ad74f2ca75e5d2e5f1dbc0a43c440f9fb510cbcc32e739ec634b0cc21b30758",
        "characters": 7_112,
        "word_count": 1_306,
    },
)

PASSAGE_SPECS = (
    {
        "passage_id": "opening_domestic_tension",
        "chapter": "chapter-001.json",
        "start": "“Hark at the wind,” said Mr. White",
        "end": "“Mate,” replied the son.",
        "characters": 378,
        "sha256": "1505ffdc29416106677ad7c3ef7ea0a3db602c1069e1d72b81327721c1fe5765",
        "risk": "period dialogue, domestic understatement, and abrupt chess beats",
    },
    {
        "passage_id": "paw_warning_and_fate",
        "chapter": "chapter-001.json",
        "start": "“It had a spell put on it by an old fakir,”",
        "end": "His tones were so grave that a hush fell upon the group.",
        "characters": 1_023,
        "sha256": "a3ec2e40908f432cca118c418e743329bccc9f411908bc16da2f725e8e43007d",
        "risk": "mythic exposition, ominous restraint, and multi-speaker dialogue",
    },
    {
        "passage_id": "factory_news_and_grief",
        "chapter": "chapter-002.json",
        "start": "“I—was asked to call,” he said at last",
        "end": "There was a long silence.",
        "characters": 988,
        "sha256": "6877bbcbea4fdfd7729b41ff27dc422b18dd6d44b7b0e4893555ba5e109cf0aa",
        "risk": "interrupted speech, shock, grief, and a required meaningful silence",
    },
    {
        "passage_id": "final_knocking_and_third_wish",
        "chapter": "chapter-003.json",
        "start": "There was another knock, and another.",
        "end": "quiet and deserted road.",
        "characters": 1_250,
        "sha256": "9198f815c21620148cfab038af5bdaadedd7397567c9a9010c1d1bc340148fb4",
        "risk": "suspense crescendo, physical action, final wish, and desolate release",
    },
)
PASSAGE_CHARACTERS = 3_639

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "af_bella"
VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
WHISPER_MODEL = "medium.en"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"
SPEED = 0.96
RANDOM_SEED = 2026072002
SAMPLE_RATE = 24_000
ASR_SOURCE_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
PRONUNCIATION_OVERRIDES = {
    "Herbert": "hˈɜɹbɚt",
    "Meggins": "mˈɛɡɪnz",
}
AMERICAN_LANG_CODE = "a"
AMERICAN_G2P = False
G2P_FALLBACK = None
G2P_UNKNOWN_TOKEN_OUTPUT = ""
PHONEME_HASHES = {
    "opening_domestic_tension": "9be297db46ae7cbdf4280115ce2ae28a089fd5d14b2f252bee1c8543ad3f2614",
    "paw_warning_and_fate": "15cc934d2726bfa75b00545720c79f7ce0b7085047298c478fb376a74e24458b",
    "factory_news_and_grief": "f43d99ee98cb361e32777735f406afd0b2d9a061ee185cb793b497ba891772f5",
    "final_knocking_and_third_wish": "93e65e675a0ca6ec44f401d69e79a11240ac9d164c1157df86bb47cc0962d53a",
}

EXPECTED_ATTEMPT_FINGERPRINT = (
    "26175ed9126e6221858801187d16879984736a7f72f00e51943b54940babf7b5"
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
    "internal/audiobook_lab/private_runs/kokoro/the-monkeys-paw/"
    "f3ff3571-af-bella-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_af_bella_representative_v1.json"
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/the-monkeys-paw_release_gate_evidence.json",
)


class MonkeysPawPilotError(RuntimeError):
    """Raised when the immutable private-pilot contract cannot be preserved."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        raise MonkeysPawPilotError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MonkeysPawPilotError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _expect(mapping: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    for key, value in expected.items():
        if mapping.get(key) != value:
            raise MonkeysPawPilotError(
                f"{label} changed for {key}: expected {value!r}, observed {mapping.get(key)!r}"
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


def assert_private_path(path: Path) -> Path:
    try:
        return BASE.assert_private_audio_path(path)
    except BASE.KokoroTitlePilotError as exc:
        raise MonkeysPawPilotError(str(exc)) from exc


def controlled_source(asset_root: Path, slug: str) -> tuple[list[Path], list[dict[str, Any]]]:
    if slug != SLUG:
        raise MonkeysPawPilotError(f"only {SLUG} is permitted; observed {slug}")
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
            "rights_basis": "Author died 1943. Published 1902. Pre-1928 publication supports U.S. public-domain status.",
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

    chapters: dict[str, str] = {}
    chapter_paths: list[Path] = []
    raw_parts: list[str] = []
    normalized_parts: list[str] = []
    for spec in CHAPTER_SPECS:
        chapter_path = publication / "chapters" / str(spec["filename"])
        chapter = read_json(chapter_path)
        _expect(
            chapter,
            {
                "id": spec["id"],
                "bookSlug": SLUG,
                "title": spec["title"],
                "language": LANGUAGE,
                "content_hash": spec["sha256"],
                "sourceSha256": ORIGIN_SOURCE_SHA256,
                "sanitizedSha256": spec["sha256"],
                "word_count": spec["word_count"],
                "processing_status": "ready",
                "processing_warnings": [],
            },
            f"controlled chapter {spec['id']}",
        )
        manuscript = chapter.get("content")
        if not isinstance(manuscript, str):
            raise MonkeysPawPilotError(f"controlled manuscript is missing: {spec['id']}")
        if len(manuscript) != spec["characters"] or sha256_text(manuscript) != spec["sha256"]:
            raise MonkeysPawPilotError(f"controlled manuscript bytes changed: {spec['id']}")
        normalized = re.sub(r"\s+", " ", manuscript).strip()
        chapters[str(spec["filename"])] = normalized
        chapter_paths.append(chapter_path)
        raw_parts.append(manuscript)
        normalized_parts.append(normalized)

    aggregate = "\n\n".join(raw_parts)
    normalized_aggregate = "\n\n".join(normalized_parts)
    if (
        len(aggregate) != AGGREGATE_SOURCE_CHARACTERS
        or sha256_text(aggregate) != AGGREGATE_SOURCE_SHA256
    ):
        raise MonkeysPawPilotError("aggregate source binding changed")
    if (
        len(normalized_aggregate) != NORMALIZED_SOURCE_CHARACTERS
        or sha256_text(normalized_aggregate) != NORMALIZED_SOURCE_SHA256
    ):
        raise MonkeysPawPilotError("normalized aggregate source binding changed")

    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        normalized = chapters[str(spec["chapter"])]
        start = normalized.find(str(spec["start"]))
        end_start = normalized.find(str(spec["end"]), start)
        if start < 0 or end_start < 0:
            raise MonkeysPawPilotError(f"passage markers changed: {spec['passage_id']}")
        text = normalized[start : end_start + len(str(spec["end"]))]
        if len(text) != spec["characters"] or sha256_text(text) != spec["sha256"]:
            raise MonkeysPawPilotError(f"passage binding changed: {spec['passage_id']}")
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "chapter": spec["chapter"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
                "risk": spec["risk"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise MonkeysPawPilotError("representative passage total changed")
    return chapter_paths, passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.kokoro_monkeys_paw_private_audition.v1",
        "slug": SLUG,
        "profile": PROFILE,
        "chapter_sha256": [item["sha256"] for item in CHAPTER_SPECS],
        "aggregate_source_sha256": AGGREGATE_SOURCE_SHA256,
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
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "scope": "four_passage_private_representative_pilot",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    for evidence in NO_REPEAT_FILES:
        if evidence.is_file() and fingerprint in set(_fingerprints(read_json(evidence))):
            raise MonkeysPawPilotError(f"attempt fingerprint already exists in {evidence}")
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        if prior_fingerprint == fingerprint and bool((prior.get("safety") or {}).get("audio_generated")):
            raise MonkeysPawPilotError("this exact fingerprint already generated audio")


def validate_prior_attempts(asset_root: Path) -> dict[str, Any]:
    path = (
        asset_root
        / "internal/audiobook_lab/sprint1_publication/title_runs/"
        "the-monkeys-paw_release_gate_evidence.json"
    )
    evidence = read_json(path)
    _expect(
        evidence,
        {
            "slug": SLUG,
            "title": TITLE,
            "author": "W. W. Jacobs",
            "publicly_available_audiobook": "No",
            "release_gate_state": "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED_FAIL_CLOSED",
            "public_audio_approved_this_sprint": False,
            "upload_performed": False,
        },
        "prior release evidence",
    )
    auditions = evidence.get("representative_auditions")
    if not isinstance(auditions, list) or len(auditions) != 2:
        raise MonkeysPawPilotError("prior representative audition count changed")
    observed = {(item.get("provider"), item.get("voice"), item.get("fingerprint")) for item in auditions}
    expected = {
        ("google", "en-GB-Studio-C", "8b671c0f3c569295"),
        ("google", "en-GB-Chirp3-HD-Achird", "14b9ef3e3465b1b0"),
    }
    if observed != expected:
        raise MonkeysPawPilotError("prior provider/voice fingerprints changed")
    return {
        "evidence_path": str(path),
        "closed_google_fingerprints": sorted(item[2] for item in expected),
        "full_candidate_fingerprint": (evidence.get("full_candidate") or {}).get(
            "private_manifest_fingerprint"
        ),
        "repaired_candidate_binding": (evidence.get("repaired_full_candidate") or {}).get(
            "candidate_binding_sha256"
        ),
        "new_provider_family": "kokoro",
        "materially_distinct": True,
    }


def validate_artifacts(
    artifact_dir: Path, whisper_cache_dir: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    root = artifact_dir.expanduser().resolve()
    paths = {
        "model": root / "kokoro-v1_0.pth",
        "config": root / "config.json",
        "voice": root / f"voices/{VOICE}.pt",
        "whisper": whisper_cache_dir.expanduser().resolve() / "medium.en.pt",
    }
    expected = {
        "model": MODEL_SHA256,
        "config": CONFIG_SHA256,
        "voice": VOICE_SHA256,
        "whisper": WHISPER_SHA256,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise MonkeysPawPilotError(f"{name} artifact is missing: {path}")
        observed = sha256_file(path)
        if observed != expected[name]:
            raise MonkeysPawPilotError(
                f"{name} SHA-256 mismatch: expected {expected[name]}, observed {observed}"
            )
    read_json(paths["config"])
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
    pinned = bool(
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
            raise MonkeysPawPilotError(
                f"pinned runtime package mismatch for {package}: expected {expected}, observed {observed}"
            )
    return {
        "status": (
            "PINNED_EXECUTION_RUNTIME_VERIFIED"
            if pinned
            else "SYSTEM_TEST_RUNTIME_NOT_EXECUTION_READY"
        ),
        "pinned_execution_runtime_verified": pinned,
        "python_version": platform.python_version(),
        "python_executable": str(executable),
        "python_executable_sha256": executable_hash,
        "expected_python_version": PINNED_PYTHON_VERSION,
        "expected_python_executable_sha256": PINNED_PYTHON_SHA256,
        "package_versions": packages,
        "expected_package_versions": RUNTIME_VERSIONS,
    }


def validate_g2p(passages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        from misaki import en as misaki_en  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - pinned runtime guard
        raise MonkeysPawPilotError("pinned misaki runtime is unavailable") from exc
    g2p = misaki_en.G2P(
        trf=False,
        british=AMERICAN_G2P,
        fallback=G2P_FALLBACK,
        unk=G2P_UNKNOWN_TOKEN_OUTPUT,
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
        observed_hash = sha256_text(phonemes)
        if unresolved:
            raise MonkeysPawPilotError(
                f"fallback-free G2P has unresolved tokens in {passage_id}: {', '.join(unresolved)}"
            )
        if observed_hash != PHONEME_HASHES[passage_id]:
            raise MonkeysPawPilotError(f"phoneme binding changed: {passage_id}")
        reports.append(
            {
                "passage_id": passage_id,
                "phoneme_sha256": observed_hash,
                "token_count": len(tokens),
                "unresolved_tokens": [],
            }
        )
    return {
        "status": "PASS",
        "lang_code": AMERICAN_LANG_CODE,
        "british": AMERICAN_G2P,
        "fallback": None,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "reports": reports,
    }


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = AGGREGATE_SOURCE_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = AGGREGATE_SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(item["sha256"] for item in PASSAGE_SPECS)
    BASE.EXPECTED_PASSAGE_CHARACTERS = PASSAGE_CHARACTERS
    BASE.MODEL_REVISION = MODEL_REVISION
    BASE.MODEL_SHA256 = MODEL_SHA256
    BASE.CONFIG_SHA256 = CONFIG_SHA256
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = f"voices/{VOICE}.pt"
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.WHISPER_MODEL = WHISPER_MODEL
    BASE.WHISPER_SHA256 = WHISPER_SHA256
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.SAMPLE_RATE = SAMPLE_RATE
    BASE.ASR_SCORE_MIN = ASR_SOURCE_SCORE_MIN
    BASE.ASR_COVERAGE_MIN = ASR_COVERAGE_MIN
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ""
    BASE.ASR_PROMPT_POLICY = {item["passage_id"]: "no_prompt" for item in PASSAGE_SPECS}
    BASE.SOURCE_EQUIVALENCE_POLICY = {item["passage_id"]: () for item in PASSAGE_SPECS}


def exact_execute_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/sprint1_monkeys_paw_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} --output {DEFAULT_EVIDENCE}"
    )


def preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    artifact_dir: Path,
    whisper_cache_dir: Path,
    private_output_dir: Path,
    output: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    if profile != PROFILE:
        raise MonkeysPawPilotError(f"unsupported profile: {profile}")
    private_dir = assert_private_path(private_output_dir)
    chapter_paths, passages = controlled_source(asset_root, slug)
    fingerprint = attempt_fingerprint(passages)
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise MonkeysPawPilotError(
            f"attempt fingerprint changed: expected {EXPECTED_ATTEMPT_FINGERPRINT}, observed {fingerprint}"
        )
    ensure_not_repeated(fingerprint, output)
    prior = validate_prior_attempts(asset_root)
    artifacts, artifact_evidence = validate_artifacts(artifact_dir, whisper_cache_dir)
    runtime = runtime_evidence()
    g2p = validate_g2p(passages)
    runtime_ready = runtime["pinned_execution_runtime_verified"] is True
    payload = {
        "schema": "earnalism.kokoro.monkeys_paw_private_audition.v1",
        "generated_at": utc_now(),
        "status": (
            "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION"
            if runtime_ready
            else "CONTRACT_VALID_PINNED_EXECUTION_RUNTIME_REQUIRED"
        ),
        "go_no_go": (
            "GO_PRIVATE_REPRESENTATIVE_ONLY"
            if runtime_ready
            else "NO_GO_UNDER_CURRENT_INTERPRETER"
        ),
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "language": LANGUAGE,
            "profile": PROFILE,
            "chapter_count": len(chapter_paths),
            "passage_count": len(passages),
            "characters": PASSAGE_CHARACTERS,
            "representative_only": True,
            "full_title_generated": False,
        },
        "source": {
            "chapter_paths": [str(path) for path in chapter_paths],
            "origin_source_sha256": ORIGIN_SOURCE_SHA256,
            "aggregate_source_sha256": AGGREGATE_SOURCE_SHA256,
            "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
            "rights_basis": "Author died 1943. Published 1902. Pre-1928 publication supports U.S. public-domain status.",
            "passages": [
                {
                    "passage_id": item["passage_id"],
                    "chapter": item["chapter"],
                    "characters": item["characters"],
                    "text_sha256": item["text_sha256"],
                    "risk": item["risk"],
                }
                for item in passages
            ],
        },
        "prior_attempt_audit": prior,
        "engine": {
            "family": "open_weight_local_tts",
            "package": "kokoro",
            "package_version": "0.9.4",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256,
            "config_sha256": CONFIG_SHA256,
            "voice": VOICE,
            "voice_language": "American English",
            "voice_sha256": VOICE_SHA256,
            "speed": SPEED,
            "random_seed": RANDOM_SEED,
            "g2p_language_code": AMERICAN_LANG_CODE,
            "g2p_fallback_enabled": False,
            "attempt_fingerprint": fingerprint,
        },
        "voice_selection": {
            "selected_voice": VOICE,
            "evidence_basis": (
                "af_bella has the strongest retained local record: exact 4/4 objective "
                "passes on multiple titles and release-quality listening evidence on "
                "The Gift of the Magi and The Open Window. The Monkey's Paw has no "
                "prior Kokoro fingerprint, so this is a new provider family for the title."
            ),
            "same_title_prior_provider": "google",
            "new_provider_family": "kokoro",
            "checksum_distinct_from_same_title_attempts": True,
        },
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "g2p_audit": g2p,
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
            "source_equivalence_rules": [],
            "estimated_sync_allowed": False,
        },
        "next_stage_contract": {
            "status": "EXECUTOR_CODE_REVIEWED_NOT_EXECUTED",
            "exact_execute_command": exact_execute_command(asset_root),
            "scope": "these four exact source-bound passages only",
            "full_title_generation_allowed": False,
            "listening_qa_allowed_by_this_command": False,
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
            "OWNER_10_TARGET_NOT_VERIFIED",
        ],
    }
    return payload, passages, artifacts


def execute(
    *,
    payload: dict[str, Any],
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
    whisper_cache_dir: Path,
) -> tuple[int, dict[str, Any]]:
    if payload["runtime_evidence"]["pinned_execution_runtime_verified"] is not True:
        raise MonkeysPawPilotError("execution requires the exact pinned interpreter")
    if payload["engine"]["attempt_fingerprint"] != EXPECTED_ATTEMPT_FINGERPRINT:
        raise MonkeysPawPilotError("execution fingerprint changed")
    before = {name: sha256_file(path) for name, path in artifacts.items()}
    configure_base()
    samples = BASE.synthesize(passages, artifacts, assert_private_path(private_dir))
    if all(item.get("objective_format_pass") is True for item in samples):
        asr = BASE.run_asr(samples, passages, whisper_cache_dir)
    else:
        asr = {"status": "NOT_RUN_OBJECTIVE_AUDIO_FAILED", "reports": []}
    after = {name: sha256_file(path) for name, path in artifacts.items()}
    if before != after:
        raise MonkeysPawPilotError("local model, voice, or ASR artifact changed")

    expected_ids = [str(item["passage_id"]) for item in passages]
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    passed = bool(
        len(samples) == len(expected_ids) == 4
        and [str(item.get("passage_id") or "") for item in samples] == expected_ids
        and all(item.get("objective_format_pass") is True for item in samples)
        and asr.get("status") == "PASS"
        and len(reports) == len(expected_ids)
        and [str(item.get("passage_id") or "") for item in reports] == expected_ids
        and all(item.get("pass") is True for item in reports)
    )
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "CANONICAL_FRONT_COVER_MISSING",
        "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
        "PRODUCTION_ENDPOINT_NOT_RUN",
        "BROWSER_PLAYBACK_GATE_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not passed:
        blockers.insert(0, "REPRESENTATIVE_OBJECTIVE_OR_ASR_GATE_FAILED")
    updated = {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA"
            if passed
            else "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
        ),
        "go_no_go": (
            "GO_PRIVATE_LISTENING_QA_ONLY"
            if passed
            else "NO_GO_REPRESENTATIVE_OBJECTIVE_GATE_FAILED"
        ),
        "next_stage_contract": {
            **payload["next_stage_contract"],
            "status": (
                "EXECUTOR_COMPLETED_OBJECTIVE_PASS"
                if passed
                else "EXECUTOR_COMPLETED_OBJECTIVE_FAIL_CLOSED"
            ),
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
        },
        "samples": samples,
        "asr": asr,
        "safety": {
            **payload["safety"],
            "audio_generated": True,
            "asr_run": asr.get("status") != "NOT_RUN_OBJECTIVE_AUDIO_FAILED",
            "artifact_hashes_before": before,
            "artifact_hashes_after": after,
            "artifact_hashes_unchanged": True,
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": blockers,
    }
    return (0 if passed else 4), updated


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
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
    output = args.output.expanduser().resolve()
    try:
        payload, passages, artifacts = preflight(
            asset_root=args.asset_root.expanduser().resolve(),
            slug=args.slug,
            profile=args.profile,
            artifact_dir=args.artifact_dir,
            whisper_cache_dir=args.whisper_cache_dir,
            private_output_dir=args.private_output_dir,
            output=output,
        )
        if args.execute:
            code, payload = execute(
                payload=payload,
                passages=passages,
                artifacts=artifacts,
                private_dir=args.private_output_dir.expanduser().resolve(),
                whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
            )
        else:
            code = 0
        atomic_write_json(output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "output": str(output),
                    "attempt_fingerprint": payload["engine"]["attempt_fingerprint"],
                    "voice": payload["engine"]["voice"],
                    "provider_calls": 0,
                    "audio_generated": payload["safety"]["audio_generated"],
                    "paid_tts_lock_touched": False,
                    "publication_performed": False,
                    "blockers_to_release": payload["blockers_to_release"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return code
    except (MonkeysPawPilotError, BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure_base()


if __name__ == "__main__":
    raise SystemExit(main())
