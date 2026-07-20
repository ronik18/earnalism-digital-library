#!/usr/bin/env python3
"""Run the one allowed, source-bound Sprint 1 Kokoro representative pilot.

The initial contract deliberately allows only ``the-gift-of-the-magi``.  It
uses four exact passages from the controlled publication, checksum-pinned
local Kokoro/Whisper artifacts, deterministic local synthesis, and local ASR.
It cannot upload, publish, mutate release truth, or write audio to a public
path.  Adding another title requires a code-reviewed profile and new hashes.
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
HOOK_DIR = Path(__file__).resolve().parent / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

ALLOWED_SLUG = "the-gift-of-the-magi"
PROFILE_ID = "gift-v1"
TITLE = "The Gift of the Magi"
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

EXPECTED_SOURCE_SHA256 = "be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e"
EXPECTED_SOURCE_CHARACTERS = 11_298
PASSAGE_SPECS = (
    {
        "passage_id": "opening_money",
        "start": None,
        "end": "And the next day would be Christmas.",
        "characters": 386,
        "sha256": "302ec156c140104af1e3b20507baf0605913116950b6a9de768e6e91e646a834",
    },
    {
        "passage_id": "hair_sale_dialogue",
        "start": "Madame, large, too white",
        "end": "“Give it to me quick,” said Della.",
        "characters": 327,
        "sha256": "033d48a6a7b89a0341ad37b7abe0d3495a8ddd1c3dfa1b1cd03c20d3ef4db61d",
    },
    {
        "passage_id": "sacrifice_dialogue",
        "start": "“Jim, darling,” she cried",
        "end": "nice gift I’ve got for you.”",
        "characters": 381,
        "sha256": "6a5f6a372c472a7b43e4fa56178e53a74861c3847f7043469dd3958892bceeac",
    },
    {
        "passage_id": "magi_ending",
        "start": "The magi, as you know",
        "end": "They are the magi.",
        "characters": 671,
        "sha256": "93594c51c10e250f5075169ebeb57e75ad10a9c10ee0af225338ddb4ba67db83",
    },
)
EXPECTED_PASSAGE_HASHES = tuple(str(item["sha256"]) for item in PASSAGE_SPECS)
EXPECTED_PASSAGE_CHARACTERS = 1_765

SAMPLE_RATE = 24_000
SPEED = 1.0
RANDOM_SEED = 20260719
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
PRONUNCIATION_OVERRIDES = {
    "Della": "dˈɛlə",
    "Sofronie": "səfɹˈoʊni",
    "Jim": "dʒˈɪm",
    "magi": "mˈeɪdʒaɪ",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical names and spellings: Della; Jim; Madame Sofronie; magi; "
    "parsimony; practised. Preserve the complete source wording."
)
ASR_PROMPT_POLICY = {
    "opening_money": "canonical_vocabulary_prompt",
    "hair_sale_dialogue": "canonical_vocabulary_prompt",
    "sacrifice_dialogue": "no_prompt",
    "magi_ending": "canonical_vocabulary_prompt",
}
SOURCE_EQUIVALENCE_POLICY = {
    "opening_money": (
        {
            "pattern": r"\$1\.87\b",
            "replacement": "one dollar and eighty-seven cents",
            "reason": "ASR currency notation for the exact spoken source amount",
        },
    ),
    "hair_sale_dialogue": (
        {
            "pattern": r"\byour\b",
            "replacement": "yer",
            "reason": "ASR standard spelling for the source dialect spelling yer",
        },
    ),
    "sacrifice_dialogue": (),
    "magi_ending": (),
}
EXPECTED_EXISTING_AUDIO_HASHES = {
    "opening_money": "5f2c6c4e571eb41bc7a974eb6ba9fcbcb782f374bfd15ec644c76f88adb7f6c6",
    "hair_sale_dialogue": "188da386380ac30e4aad451522869a8bc616d2d8c03ff4b08451484088bc8461",
    "sacrifice_dialogue": "ba959e59fafd7df838bde8f1330976cda98360f1a92c06a22ed43f15d582e3df",
    "magi_ending": "8124feb940e30bf675342ef9cb6d2d8ac29f885bf2cedd333853309af6a27f0a",
}

# These exact failed Gift fingerprints are retained even though their provider
# families differ.  The new fingerprint must remain materially distinct.
KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset(
    {
        "716473a1705c4aa3e6ea718f2c117668875215ac368540f6402b4dab47932f43",
        "75a6fbc43a06e181677d1f4a2afc2508416d7f0b137d325f79948df48a04fabe",
        "cda6b9c871c9751f8ade43db4ec0c71b865c9ac0ba5ab5a63a49c6fbf2b13ddd",
        "cf9b59637d5ba9180a691867ac5d6574dac6458a96344389dd4d8606867d1595",
        "018bef83ba81b9902246be7a164bdda4027dc5dafe8efad03d724272c3b09e93",
    }
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json",
)


class KokoroTitlePilotError(RuntimeError):
    """Raised whenever the private pilot cannot preserve its exact contract."""


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
        raise KokoroTitlePilotError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise KokoroTitlePilotError(f"expected JSON object: {path}")
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
        raise KokoroTitlePilotError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise KokoroTitlePilotError(
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
        raise KokoroTitlePilotError(f"public audio path is forbidden: {resolved}")
    private_marker = "/internal/audiobook_lab/private_runs/"
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if private_marker not in rendered and not (
        resolved == temporary_root or temporary_root in resolved.parents
    ):
        raise KokoroTitlePilotError(
            "audio output must be under internal/audiobook_lab/private_runs or the OS temp root"
        )
    return resolved


def lock_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    payload = read_json(resolved)
    if payload.get("status") != "active":
        raise KokoroTitlePilotError("paid_tts.lock is not active")
    if payload.get("current_holder") != "none":
        raise KokoroTitlePilotError("paid_tts.lock has a current holder")
    if payload.get("allowed_next_holders") != []:
        raise KokoroTitlePilotError("paid_tts.lock allowlist is not empty")
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
        raise KokoroTitlePilotError(
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
        "audiobook_enabled": False,
        "audio_enabled": False,
    }
    for key, expected in expected_truth.items():
        if book.get(key) != expected:
            raise KokoroTitlePilotError(
                f"controlled catalog truth changed for {key}: expected {expected!r}, observed {book.get(key)!r}"
            )
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    if chapter.get("processing_status") != "ready":
        raise KokoroTitlePilotError("controlled chapter is not ready")
    if chapter.get("processing_warnings") != []:
        raise KokoroTitlePilotError("controlled chapter has processing warnings")
    manuscript = str(chapter.get("content") or "")
    if chapter.get("sanitizedSha256") != EXPECTED_SOURCE_SHA256:
        raise KokoroTitlePilotError("recorded controlled source hash changed")
    if sha256_text(manuscript) != EXPECTED_SOURCE_SHA256:
        raise KokoroTitlePilotError("controlled source bytes changed")
    if len(manuscript) != EXPECTED_SOURCE_CHARACTERS:
        raise KokoroTitlePilotError("controlled source character count changed")
    flattened = re.sub(r"\s+", " ", manuscript).strip()
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start_marker = spec["start"]
        start = 0 if start_marker is None else flattened.index(str(start_marker))
        end_marker = str(spec["end"])
        end = flattened.index(end_marker, start) + len(end_marker)
        text = flattened[start:end]
        if len(text) != spec["characters"]:
            raise KokoroTitlePilotError(
                f"passage character count changed: {spec['passage_id']}"
            )
        if sha256_text(text) != spec["sha256"]:
            raise KokoroTitlePilotError(f"passage hash changed: {spec['passage_id']}")
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != EXPECTED_PASSAGE_CHARACTERS:
        raise KokoroTitlePilotError("bounded passage character total changed")
    return chapter_path, passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.kokoro_title_representative.v1",
        "profile": PROFILE_ID,
        "slug": ALLOWED_SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
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


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    if fingerprint in KNOWN_GIFT_FAILED_FINGERPRINTS:
        raise KokoroTitlePilotError("attempt repeats a known failed Gift fingerprint")
    for evidence in NO_REPEAT_FILES:
        if evidence.is_file() and fingerprint in set(_fingerprints(read_json(evidence))):
            raise KokoroTitlePilotError(f"attempt fingerprint already exists in {evidence}")
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        audio_generated = bool((prior.get("safety") or {}).get("audio_generated"))
        if prior_fingerprint == fingerprint and audio_generated:
            raise KokoroTitlePilotError("this exact pilot already generated audio")


def validate_artifacts(artifact_dir: Path, whisper_cache_dir: Path) -> tuple[dict[str, Path], dict[str, Any]]:
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
        name: {"path": str(path), "sha256": expected[name], "size_bytes": path.stat().st_size}
        for name, path in paths.items()
    }
    return paths, evidence


def runtime_evidence() -> dict[str, Any]:
    if platform.python_version() != PYTHON_VERSION:
        raise KokoroTitlePilotError(
            f"Python version mismatch: expected {PYTHON_VERSION}, observed {platform.python_version()}"
        )
    if platform.python_implementation() != PYTHON_IMPLEMENTATION:
        raise KokoroTitlePilotError("Python implementation mismatch")
    executable_hash = sha256_file(Path(sys.executable))
    if executable_hash != PYTHON_EXECUTABLE_SHA256:
        raise KokoroTitlePilotError(
            f"Python executable hash mismatch: expected {PYTHON_EXECUTABLE_SHA256}, observed {executable_hash}"
        )
    observed: dict[str, str] = {}
    for package, expected in RUNTIME_VERSIONS.items():
        try:
            observed[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise KokoroTitlePilotError(f"pinned runtime package missing: {package}") from exc
        if observed[package] != expected:
            raise KokoroTitlePilotError(
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
        raise KokoroTitlePilotError(f"unsupported profile: {profile}")
    private_dir = assert_private_audio_path(private_output_dir)
    chapter_path, passages = controlled_source(asset_root, slug)
    fingerprint = attempt_fingerprint(passages)
    ensure_not_repeated(fingerprint, output)
    artifacts, artifact_evidence = validate_artifacts(artifact_dir, whisper_cache_dir)
    lock = lock_snapshot(paid_lock)
    runtime = runtime_evidence()
    payload = {
        "schema": "earnalism.kokoro_title_representative.v1",
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
        },
        "source": {
            "chapter_path": str(chapter_path),
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "passages": [
                {
                    "passage_id": item["passage_id"],
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
            "g2p_fallback_enabled": False,
            "attempt_fingerprint": fingerprint,
            "known_failed_fingerprint_count": len(KNOWN_GIFT_FAILED_FINGERPRINTS),
        },
        "asr_contract": {
            "model": WHISPER_MODEL,
            "model_sha256": WHISPER_SHA256,
            "source_score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "first_words_required": True,
            "last_words_required": True,
            "ordered_content_integrity_required": True,
        },
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "rights": {
            "model_and_voicepack_license": "Apache-2.0",
            "private_audition_allowed": True,
            "gift_title_scoped_production_risk_acceptance_bound": False,
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
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
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
        raise KokoroTitlePilotError(f"invalid private WAV format: {path}")
    samples = data[:, 0].astype(np.int64)
    absolute = np.abs(samples)
    peak = int(absolute.max())
    clipped = int(np.count_nonzero(absolute >= 32760))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    objective_pass = clipped == 0 and peak > 0 and rms / 32767 >= 0.001
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
        "objective_format_pass": objective_pass,
    }


def _install_local_filelock_stub() -> tuple[types.ModuleType | None, types.ModuleType]:
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
    return previous, stub


def synthesize(
    passages: Sequence[Mapping[str, Any]], artifacts: Mapping[str, Path], private_dir: Path
) -> list[dict[str, Any]]:
    previous_filelock, _stub = _install_local_filelock_stub()
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
    private_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = KModel(config=str(artifacts["config"]), model=str(artifacts["model"]))
    pipeline = KPipeline(lang_code="a", model=model, repo_id=None)
    pipeline.g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    pipeline.g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    pipeline.g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
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
            raise KokoroTitlePilotError(
                f"G2P fallback is disabled; unresolved tokens in {passage['passage_id']}: {', '.join(unresolved)}"
            )
        prepared.append((passage, tokens))
    results: list[dict[str, Any]] = []
    for passage, tokens in prepared:
        chunks: list[Any] = []
        phonemes: list[str] = []
        for item in pipeline.generate_from_tokens(tokens, voice=voice_tensor, speed=SPEED):
            if item.audio is None:
                raise KokoroTitlePilotError(f"Kokoro returned no audio: {passage['passage_id']}")
            chunks.append(item.audio.detach().cpu().numpy())
            phonemes.append(str(item.phonemes or ""))
        if not chunks:
            raise KokoroTitlePilotError(f"Kokoro returned zero chunks: {passage['passage_id']}")
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
        text.lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("—", " ")
        .replace("–", " ")
    )
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", normalized)


def apply_source_equivalences(passage_id: str, transcript: str) -> tuple[str, list[dict[str, Any]]]:
    if passage_id not in SOURCE_EQUIVALENCE_POLICY:
        raise KokoroTitlePilotError(f"no source-equivalence policy exists for {passage_id}")
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
    missing = {
        token: count - transcript_count[token]
        for token, count in source_count.items()
        if count > transcript_count[token]
    }
    unexpected = {
        token: count - source_count[token]
        for token, count in transcript_count.items()
        if count > source_count[token]
    }
    duplicate = {
        token: transcript_count[token] - count
        for token, count in source_count.items()
        if transcript_count[token] > count
    }
    available_positions: dict[str, list[int]] = {}
    for index, token in enumerate(source_tokens):
        available_positions.setdefault(token, []).append(index)
    consumed: Counter[str] = Counter()
    common_positions: list[int] = []
    for token in transcript_tokens:
        token_positions = available_positions.get(token, [])
        occurrence = consumed[token]
        if occurrence < len(token_positions):
            common_positions.append(token_positions[occurrence])
            consumed[token] += 1
    no_reordered = common_positions == sorted(common_positions)
    coverage = equal_tokens / len(source_tokens) if source_tokens else 0.0
    precision = equal_tokens / len(transcript_tokens) if transcript_tokens else 0.0
    harmonic = (
        2 * coverage * precision / (coverage + precision)
        if coverage + precision
        else 0.0
    )
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
        "no_reordered_content": no_reordered,
        "no_unexpected_content": not unexpected,
        "missing_tokens": missing,
        "duplicate_tokens": duplicate,
        "unexpected_tokens": unexpected,
        "ordered_alignment_operations": operations,
    }


def asr_config_fingerprint(samples: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.kokoro_existing_audio_asr_reverify.v1",
        "slug": ALLOWED_SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_hashes": {
            str(item["passage_id"]): str(item["audio_sha256"]) for item in samples
        },
        "prompt_policy": ASR_PROMPT_POLICY,
        "prompt_sha256": sha256_text(ASR_VOCABULARY_PROMPT),
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
    }
    return sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def run_asr(
    samples: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_cache_dir: Path,
) -> dict[str, Any]:
    import whisper  # noqa: PLC0415

    by_id = {str(item["passage_id"]): item for item in passages}
    model = whisper.load_model(WHISPER_MODEL, download_root=str(whisper_cache_dir.resolve()))
    config_fingerprint = asr_config_fingerprint(samples)
    reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        passage = by_id[passage_id]
        audio = assert_private_audio_path(Path(str(sample["audio_path"])))
        verify_hash(audio, str(sample["audio_sha256"]), f"sample {passage_id}")
        prompt_mode = ASR_PROMPT_POLICY[passage_id]
        initial_prompt = (
            ASR_VOCABULARY_PROMPT
            if prompt_mode == "canonical_vocabulary_prompt"
            else None
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
        )
        transcript = str(result.get("text") or "").strip()
        evaluated_transcript, equivalences = apply_source_equivalences(
            passage_id, transcript
        )
        metrics = ordered_token_integrity(
            str(passage["text"]), evaluated_transcript
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
        )
        segments = result.get("segments") if isinstance(result.get("segments"), list) else []
        no_speech_probabilities = [
            float(item["no_speech_prob"])
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("no_speech_prob"), (int, float))
        ]
        reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": sample["audio_sha256"],
                "source_text_sha256": passage["text_sha256"],
                "prompt_mode": prompt_mode,
                "prompt_sha256": (
                    sha256_text(ASR_VOCABULARY_PROMPT) if initial_prompt else None
                ),
                "transcript": transcript,
                "transcript_sha256": sha256_text(transcript),
                "evaluated_transcript": evaluated_transcript,
                "evaluated_transcript_sha256": sha256_text(evaluated_transcript),
                "source_equivalences_applied": equivalences,
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
        "prompt_policy": ASR_PROMPT_POLICY,
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "unexpected_speech_may_be_normalized_or_discarded": False,
        "reports": reports,
    }


def validate_existing_samples(
    payload: Mapping[str, Any], passages: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if (payload.get("scope") or {}).get("slug") != ALLOWED_SLUG:
        raise KokoroTitlePilotError("existing evidence is for the wrong slug")
    expected_attempt = attempt_fingerprint(passages)
    if (payload.get("engine") or {}).get("attempt_fingerprint") != expected_attempt:
        raise KokoroTitlePilotError("existing evidence attempt fingerprint changed")
    if (payload.get("safety") or {}).get("audio_generated") is not True:
        raise KokoroTitlePilotError("existing evidence does not prove generated audio")
    if (payload.get("safety") or {}).get("provider_calls") != 0:
        raise KokoroTitlePilotError("existing evidence records provider calls")
    if (payload.get("safety") or {}).get("upload_performed") is not False:
        raise KokoroTitlePilotError("existing evidence records an upload")
    samples_value = payload.get("samples")
    if not isinstance(samples_value, list) or len(samples_value) != len(PASSAGE_SPECS):
        raise KokoroTitlePilotError("exactly four existing sample records are required")
    passage_by_id = {str(item["passage_id"]): item for item in passages}
    sample_by_id: dict[str, dict[str, Any]] = {}
    for value in samples_value:
        if not isinstance(value, dict):
            raise KokoroTitlePilotError("existing sample record is not an object")
        passage_id = str(value.get("passage_id") or "")
        if passage_id in sample_by_id:
            raise KokoroTitlePilotError(f"duplicate existing sample: {passage_id}")
        sample_by_id[passage_id] = value
    if set(sample_by_id) != set(EXPECTED_EXISTING_AUDIO_HASHES):
        raise KokoroTitlePilotError("existing sample IDs changed")
    ordered_samples: list[dict[str, Any]] = []
    snapshot: dict[str, str] = {}
    for spec in PASSAGE_SPECS:
        passage_id = str(spec["passage_id"])
        sample = sample_by_id[passage_id]
        expected_audio_hash = EXPECTED_EXISTING_AUDIO_HASHES[passage_id]
        if sample.get("audio_sha256") != expected_audio_hash:
            raise KokoroTitlePilotError(
                f"existing evidence audio hash changed: {passage_id}"
            )
        if sample.get("source_text_sha256") != passage_by_id[passage_id]["text_sha256"]:
            raise KokoroTitlePilotError(
                f"existing evidence source binding changed: {passage_id}"
            )
        if sample.get("objective_format_pass") is not True:
            raise KokoroTitlePilotError(
                f"existing audio did not pass objective format QA: {passage_id}"
            )
        audio = assert_private_audio_path(Path(str(sample.get("audio_path") or "")))
        if audio.name != f"{passage_id}.wav":
            raise KokoroTitlePilotError(
                f"existing sample filename changed: {passage_id}"
            )
        verify_hash(audio, expected_audio_hash, f"existing sample {passage_id}")
        snapshot[passage_id] = sha256_file(audio)
        ordered_samples.append(dict(sample))
    return ordered_samples, snapshot


def asr_reverify_existing(
    *,
    payload: dict[str, Any],
    asset_root: Path,
    whisper_cache_dir: Path,
    paid_lock: Path,
) -> tuple[int, dict[str, Any]]:
    _chapter, passages = controlled_source(asset_root, ALLOWED_SLUG)
    samples, audio_before = validate_existing_samples(payload, passages)
    whisper_path = whisper_cache_dir.expanduser().resolve() / WHISPER_FILENAME
    verify_hash(whisper_path, WHISPER_SHA256, "whisper")
    runtime = runtime_evidence()
    config_fingerprint = asr_config_fingerprint(samples)
    prior_reverification = payload.get("asr_reverification")
    if (
        isinstance(prior_reverification, dict)
        and prior_reverification.get("config_fingerprint") == config_fingerprint
        and prior_reverification.get("completed") is True
    ):
        raise KokoroTitlePilotError("this exact ASR re-verification already completed")
    lock_before = lock_snapshot(paid_lock)
    asr = run_asr(samples, passages, whisper_cache_dir)
    lock_after = lock_snapshot(paid_lock)
    if lock_before != lock_after:
        raise KokoroTitlePilotError("paid_tts.lock changed during ASR-only repair")
    _samples_after, audio_after = validate_existing_samples(payload, passages)
    if audio_before != audio_after:
        raise KokoroTitlePilotError("existing audio hashes changed during ASR-only repair")
    if asr.get("config_fingerprint") != config_fingerprint:
        raise KokoroTitlePilotError("ASR report config fingerprint changed")
    passed = asr.get("status") == "PASS"
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not passed:
        blockers.insert(0, "REPRESENTATIVE_ASR_REVERIFICATION_FAILED")
    updated = {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA"
            if passed
            else "PRIVATE_REPRESENTATIVE_PILOT_REJECTED_ASR_REVERIFY"
        ),
        "asr_prior_prompted_run": payload.get("asr"),
        "asr": asr,
        "asr_reverification": {
            "completed": True,
            "mode": "ASR_ONLY_EXISTING_HASH_BOUND_AUDIO",
            "config_fingerprint": config_fingerprint,
            "audio_hashes_before": audio_before,
            "audio_hashes_after": audio_after,
            "audio_hashes_unchanged": audio_before == audio_after,
            "resynthesis_performed": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        },
        "runtime_evidence": runtime,
        "safety": {
            **payload["safety"],
            "paid_tts_lock_before_asr_reverify": lock_before,
            "paid_tts_lock_after_asr_reverify": lock_after,
            "paid_tts_lock_unchanged": True,
            "asr_only_reverification": True,
            "resynthesis_performed": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        },
        "blockers_to_release": blockers,
    }
    return (0 if passed else 5), updated


def execute(
    *,
    payload: dict[str, Any],
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
    whisper_cache_dir: Path,
    paid_lock: Path,
) -> tuple[int, dict[str, Any]]:
    lock_before = lock_snapshot(paid_lock)
    samples = synthesize(passages, artifacts, private_dir)
    lock_after_synthesis = lock_snapshot(paid_lock)
    if lock_before != lock_after_synthesis:
        raise KokoroTitlePilotError("paid_tts.lock changed during local synthesis")
    if not all(item["objective_format_pass"] for item in samples):
        asr = {"status": "NOT_RUN_OBJECTIVE_AUDIO_FAILED", "reports": []}
    else:
        asr = run_asr(samples, passages, whisper_cache_dir)
    lock_after_asr = lock_snapshot(paid_lock)
    if lock_before != lock_after_asr:
        raise KokoroTitlePilotError("paid_tts.lock changed during local ASR")
    passed = bool(
        all(item["objective_format_pass"] for item in samples)
        and asr.get("status") == "PASS"
    )
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not passed:
        blockers.insert(0, "REPRESENTATIVE_OBJECTIVE_OR_ASR_GATE_FAILED")
    result = {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA"
            if passed
            else "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
        ),
        "samples": samples,
        "asr": asr,
        "safety": {
            **payload["safety"],
            "paid_tts_lock_before": lock_before,
            "paid_tts_lock_after": lock_after_asr,
            "paid_tts_lock_unchanged": True,
            "audio_generated": True,
        },
        "blockers_to_release": blockers,
    }
    return (0 if passed else 4), result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--asr-reverify-existing", action="store_true")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--whisper-cache-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paid-lock", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.expanduser().resolve()
    try:
        if args.asr_reverify_existing:
            payload = read_json(output)
            code, payload = asr_reverify_existing(
                payload=payload,
                asset_root=args.asset_root.expanduser().resolve(),
                whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
                paid_lock=args.paid_lock,
            )
        else:
            if args.artifact_dir is None or args.private_output_dir is None:
                raise KokoroTitlePilotError(
                    "--artifact-dir and --private-output-dir are required for preflight or synthesis"
                )
            payload, passages, artifacts = preflight(
                asset_root=args.asset_root.expanduser().resolve(),
                slug=args.slug,
                profile=args.profile,
                artifact_dir=args.artifact_dir,
                whisper_cache_dir=args.whisper_cache_dir,
                private_output_dir=args.private_output_dir,
                output=output,
                paid_lock=args.paid_lock,
            )
            if args.execute:
                code, payload = execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=assert_private_audio_path(args.private_output_dir),
                    whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
                    paid_lock=args.paid_lock,
                )
            else:
                code = 0
        atomic_write_json(output, payload)
        summary = {
            "status": payload["status"],
            "output": str(output),
            "attempt_fingerprint": payload["engine"]["attempt_fingerprint"],
            "provider_calls": 0,
            "audio_generated": payload["safety"]["audio_generated"],
            "resynthesis_performed": payload["safety"].get("resynthesis_performed"),
            "publication_performed": False,
            "blockers_to_release": payload["blockers_to_release"],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return code
    except KokoroTitlePilotError as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
