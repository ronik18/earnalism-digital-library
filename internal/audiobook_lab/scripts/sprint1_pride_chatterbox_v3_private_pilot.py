#!/usr/bin/env python3
"""Preflight or run one private, source-bound Pride Chatterbox V3 sample.

This title-specific runner has no upload, publication, catalog-write, or
release-gate code path.  It only accepts the pinned local Chatterbox bundle,
uses its bundled ``conds.pt`` without external reference audio, writes under
the system temporary directory, and runs source-blind local ASR immediately
after synthesis.  An objective pass authorizes listening review only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_gift_kokoro_full_title_private_qa as asr_common  # noqa: E402
import sprint1_kokoro_title_private_audition as whisper_common  # noqa: E402


SCHEMA = "earnalism.pride_chatterbox_v3_private_pilot.v1"
SLUG = "pride-and-prejudice"
TITLE = "Pride and Prejudice"
AUTHOR = "Jane Austen"
POLICY_PATH = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "pride-and-prejudice_chatterbox_v3_private_pilot_policy.json"
)
POLICY_SHA256 = "f1cb28a41004bc49e9796bc91cbc584f94fb361837afbd9d74b277ab73e38540"
CHAPTER_PATH = ROOT / (
    "data/controlled_publications/pride-and-prejudice/chapters/chapter-001.json"
)
CHAPTER_FILE_SHA256 = "e85732d1acfa4e879992bf65d7244a6e0faa3b29f2ad2958d0c0dedb2cb72fba"
SOURCE_SHA256 = "fcf234e0476cc6af8b3f604399bf3d7c4b72931bdf2af276ab4cc78caf938d5c"
SANITIZED_SHA256 = "3e19fb75e8ba915bad01d7edde9938d666fe7195c8d62fea8e72cda2baa9a3c0"
PASSAGE_ID = "chapter-001-dialogue-01"
PASSAGE_TEXT = (
    "“My dear Mr. Bennet,” said his lady to him one day, “have you heard that "
    "Netherfield Park is let at last?” Mr. Bennet replied that he had not. "
    "“But it is,” returned she; “for Mrs. Long has just been here, and she "
    "told me all about it.”"
)
PASSAGE_SHA256 = "e51782a522b817e8c1e116fdbffd2841a3327e44ad7c16dd655e5ae2b235680b"

MODEL_ID = "ResembleAI/chatterbox"
MODEL_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
RUNTIME_PACKAGE = "chatterbox-tts"
RUNTIME_VERSION = "0.1.7"
MODEL_FILE_HASHES = {
    "t3_mtl23ls_v3.safetensors": (
        "5abca8321ede76f8e61f1cc0d19aea6c946b28871017ce8726f8a69203f05953"
    ),
    "conds.pt": "6552d70568833628ba019c6b03459e77fe71ca197d5c560cef9411bee9d87f4e",
    "s3gen.pt": "9b9ff07e60b20c136e2b1b3d7563a24604e8d2c4c267888d1ee929dd0151d2a3",
    "ve.pt": "4b16d836bc598509860f6fa068165a8bb5e9ac84f05582dfcf278a5a372879f1",
    "grapheme_mtl_merged_expanded_v1.json": (
        "69632f47220a788a52ce2661d096453c5655e9bf25289d89a8d832c46ee07dbf"
    ),
    "Cangjie5_TC.json": (
        "7073fd9de919443ae88e0bd2449917a65fe54898a4413ed1edcc4b67f28bce8c"
    ),
}
GENERATION_SETTINGS = {
    "language_id": "en",
    "exaggeration": 0.5,
    "cfg_weight": 0.5,
    "temperature": 0.8,
    "repetition_penalty": 1.2,
    "min_p": 0.05,
    "top_p": 1.0,
}
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
WHISPER_MODEL = whisper_common.WHISPER_MODEL
WHISPER_FILENAME = whisper_common.WHISPER_FILENAME
WHISPER_SHA256 = whisper_common.WHISPER_SHA256
ASR_SETTINGS = asr_common.ASR_SETTINGS
DEFAULT_MODEL_DIR = Path(
    "/Users/ronikbasak/Library/Caches/huggingface/hub/"
    "models--ResembleAI--chatterbox/snapshots/"
    f"{MODEL_REVISION}"
)
DEFAULT_PRIVATE_ROOT = Path(tempfile.gettempdir()) / (
    "earnalism-pride-chatterbox-v3-private"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
PUBLIC_FORBIDDEN_ROOTS = (
    ROOT / "frontend/public",
    ROOT / "frontend/build",
)
NO_REPEAT_PATHS = (
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/provider_voice_memory.json",
    ROOT / "internal/audiobook_lab/sprint1_publication/title_runs",
)


class PrideChatterboxPilotError(RuntimeError):
    """Raised whenever the exact private pilot contract is not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrideChatterboxPilotError(message)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
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


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(payload)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def verify_file(path: Path, expected_sha256: str, label: str) -> None:
    require(path.is_file(), f"{label} is missing: {path}")
    observed = sha256_file(path)
    require(
        observed == expected_sha256,
        f"{label} SHA-256 mismatch: expected {expected_sha256}, observed {observed}",
    )


def load_json(path: Path, label: str) -> dict[str, Any]:
    require(path.is_file(), f"{label} is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrideChatterboxPilotError(f"{label} is invalid JSON: {path}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def ensure_private_path(path: Path, *, private_root: Path) -> Path:
    resolved = path.expanduser().resolve()
    system_temp = Path(tempfile.gettempdir()).resolve()
    allowed_root = private_root.expanduser().resolve()
    require(
        resolved == allowed_root or allowed_root in resolved.parents,
        f"output must stay under the configured private root: {allowed_root}",
    )
    require(
        resolved == system_temp or system_temp in resolved.parents,
        f"output must stay under the system temporary directory: {system_temp}",
    )
    require(
        not (resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents),
        "output may not be written inside the repository",
    )
    for forbidden in PUBLIC_FORBIDDEN_ROOTS:
        forbidden = forbidden.resolve()
        require(
            not (resolved == forbidden or forbidden in resolved.parents),
            f"output may not be written under public assets: {forbidden}",
        )
    return resolved


def validate_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    verify_file(path, POLICY_SHA256, "private pilot policy")
    policy = load_json(path, "private pilot policy")
    require(
        policy.get("decision")
        == "AUTHORIZE_ONE_PRIVATE_CHATTERBOX_V3_BUILTIN_CONDS_SAMPLE",
        "private pilot decision changed",
    )
    scope = policy.get("scope") or {}
    require(scope.get("sample_count") == 1, "policy must authorize exactly one sample")
    require(scope.get("private_only") is True, "policy must remain private")
    for key in (
        "full_title_generation_allowed",
        "upload_allowed",
        "publication_allowed",
        "release_gate_mutation_allowed",
        "catalog_mutation_allowed",
        "public_asset_write_allowed",
    ):
        require(scope.get(key) is False, f"policy unexpectedly permits {key}")
    voice = policy.get("voice_contract") or {}
    require(
        voice.get("kind") == "MODEL_BUILTIN_CONDITIONAL_NO_EXTERNAL_REFERENCE",
        "voice contract must use built-in conditionals",
    )
    require(
        voice.get("audio_prompt_path_allowed") is False,
        "audio_prompt_path must remain prohibited",
    )
    require(
        (policy.get("model_contract") or {}).get("files") == MODEL_FILE_HASHES,
        "policy model file contract changed",
    )
    return policy


def validate_source() -> dict[str, Any]:
    verify_file(CHAPTER_PATH, CHAPTER_FILE_SHA256, "controlled chapter")
    chapter = load_json(CHAPTER_PATH, "controlled chapter")
    require(chapter.get("bookSlug") == SLUG, "controlled chapter slug changed")
    require(chapter.get("title") == "Chapter I", "controlled chapter title changed")
    require(chapter.get("sourceSha256") == SOURCE_SHA256, "source hash changed")
    require(
        chapter.get("sanitizedSha256") == SANITIZED_SHA256,
        "sanitized chapter hash changed",
    )
    require(sha256_text(PASSAGE_TEXT) == PASSAGE_SHA256, "passage hash changed")
    normalized = normalize_whitespace(str(chapter.get("content") or ""))
    require(
        normalized.count(PASSAGE_TEXT) == 1,
        "exact normalized passage must occur once in the controlled chapter",
    )
    return {
        "chapter_path": str(CHAPTER_PATH),
        "chapter_file_sha256": CHAPTER_FILE_SHA256,
        "source_sha256": SOURCE_SHA256,
        "sanitized_sha256": SANITIZED_SHA256,
        "passage_id": PASSAGE_ID,
        "passage_text_sha256": PASSAGE_SHA256,
        "passage_characters": len(PASSAGE_TEXT),
    }


def validate_catalog_truth() -> dict[str, Any]:
    base = ROOT / "data/controlled_publications" / SLUG
    public_book = load_json(base / "public_book.json", "controlled public book")
    approval = load_json(base / "approval_evidence.json", "approval evidence")
    source = load_json(base / "source_evidence.json", "source evidence")
    require(public_book.get("slug") == SLUG, "public book slug changed")
    require(public_book.get("title") == TITLE, "public book title changed")
    require(public_book.get("author") == AUTHOR, "public book author changed")
    require(bool(public_book.get("cover_url")), "front cover is missing")
    require(bool(public_book.get("back_cover_url")), "back cover is missing")
    require(public_book.get("source_hash") == SOURCE_SHA256, "public source changed")
    require(source.get("source_hash") == SOURCE_SHA256, "rights source changed")
    source_license = str(source.get("source_license") or "")
    require(
        source_license.casefold().startswith("public domain"),
        "text rights changed",
    )
    require(approval.get("audiobook_use_approved") is True, "audio use not approved")
    require(
        approval.get("audio_public_release") == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "public audio state must remain not approved",
    )
    require(public_book.get("audio_enabled") is False, "public audio became enabled")
    require(
        public_book.get("audiobook_enabled") is False,
        "public audiobook became enabled",
    )
    return {
        "front_cover_url": public_book["cover_url"],
        "back_cover_url": public_book["back_cover_url"],
        "text_rights": source_license,
        "audiobook_use_approved": True,
        "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
    }


def validate_model_bundle(model_dir: Path) -> dict[str, str]:
    resolved = model_dir.expanduser().resolve()
    observed: dict[str, str] = {}
    for filename, expected in MODEL_FILE_HASHES.items():
        path = resolved / filename
        verify_file(path, expected, f"pinned Chatterbox file {filename}")
        observed[filename] = expected
    return observed


def validate_runtime(
    version_getter: Callable[[str], str] = metadata.version,
) -> str:
    try:
        observed = version_getter(RUNTIME_PACKAGE)
    except metadata.PackageNotFoundError as exc:
        raise PrideChatterboxPilotError(
            f"{RUNTIME_PACKAGE}=={RUNTIME_VERSION} is not installed"
        ) from exc
    require(
        observed == RUNTIME_VERSION,
        f"{RUNTIME_PACKAGE} must be exactly {RUNTIME_VERSION}; found {observed}",
    )
    return observed


def read_and_validate_paid_lock(path: Path) -> tuple[bytes, dict[str, Any]]:
    require(path.is_file(), f"paid_tts.lock is missing: {path}")
    before = path.read_bytes()
    try:
        lock = json.loads(before)
    except json.JSONDecodeError as exc:
        raise PrideChatterboxPilotError("paid_tts.lock is invalid JSON") from exc
    require(lock.get("status") == "active", "paid_tts.lock is not active")
    require(lock.get("current_holder") == "none", "paid_tts.lock is held")
    require(
        lock.get("allowed_next_holders") == [],
        "paid_tts.lock has a scheduled holder",
    )
    require(SLUG in (lock.get("allowed_slugs") or []), f"{SLUG} is not lock-allowed")
    return before, lock


def assert_paid_lock_unchanged(path: Path, before: bytes) -> None:
    require(path.read_bytes() == before, "paid_tts.lock changed during the pilot")


def attempt_payload(
    *,
    model_dir: Path,
    policy_sha256: str = POLICY_SHA256,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "slug": SLUG,
        "source_sha256": SOURCE_SHA256,
        "passage_id": PASSAGE_ID,
        "passage_text_sha256": PASSAGE_SHA256,
        "policy_sha256": policy_sha256,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_files": MODEL_FILE_HASHES,
        "model_dir": str(model_dir.expanduser().resolve()),
        "runtime_package": RUNTIME_PACKAGE,
        "runtime_version": RUNTIME_VERSION,
        "voice_kind": "MODEL_BUILTIN_CONDITIONAL_NO_EXTERNAL_REFERENCE",
        "external_reference_audio": None,
        "audio_prompt_path": None,
        "generation_settings": GENERATION_SETTINGS,
        "asr_model": WHISPER_MODEL,
        "asr_model_sha256": WHISPER_SHA256,
        "asr_settings": ASR_SETTINGS,
        "scope": "one_private_sample_no_upload_publication_or_release_mutation",
    }


def assert_not_repeated(
    fingerprint: str,
    *,
    paths: tuple[Path, ...] = NO_REPEAT_PATHS,
) -> None:
    for path in paths:
        candidates = sorted(path.rglob("*.json")) if path.is_dir() else [path]
        for candidate in candidates:
            if candidate == POLICY_PATH or not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
            if fingerprint in text:
                raise PrideChatterboxPilotError(
                    f"attempt fingerprint already exists: {candidate}"
                )


def select_device() -> str:
    try:
        import torch  # noqa: PLC0415
    except ImportError as exc:
        raise PrideChatterboxPilotError("torch is required for synthesis") from exc
    if bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def synthesize(
    *,
    model_dir: Path,
    output_path: Path,
    device: str,
    model_factory: Callable[..., Any] | None = None,
    audio_saver: Callable[[Path, Any, int], None] | None = None,
) -> dict[str, Any]:
    """Generate exactly the bound passage without any reference-audio argument."""
    if model_factory is None:
        try:
            from chatterbox.mtl_tts import (  # noqa: PLC0415
                ChatterboxMultilingualTTS,
            )
        except ImportError as exc:
            raise PrideChatterboxPilotError(
                f"{RUNTIME_PACKAGE}=={RUNTIME_VERSION} is required"
            ) from exc
        model_factory = ChatterboxMultilingualTTS.from_local

    model = model_factory(
        str(model_dir.expanduser().resolve()),
        device,
        t3_model="t3_mtl23ls_v3.safetensors",
    )
    require(getattr(model, "conds", None) is not None, "bundled conds.pt was not loaded")
    audio = model.generate(PASSAGE_TEXT, **GENERATION_SETTINGS)
    sample_rate = int(getattr(model, "sr", 0))
    require(sample_rate > 0, "model returned an invalid sample rate")

    if audio_saver is None:
        try:
            import torchaudio  # noqa: PLC0415
        except ImportError as exc:
            raise PrideChatterboxPilotError("torchaudio is required") from exc

        def save(path: Path, waveform: Any, rate: int) -> None:
            tensor = waveform.detach().cpu()
            if getattr(tensor, "ndim", 0) == 1:
                tensor = tensor.unsqueeze(0)
            torchaudio.save(str(path), tensor, rate, format="wav")

        audio_saver = save

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio_saver(output_path, audio, sample_rate)
    require(output_path.is_file(), "synthesis did not create the private WAV")
    return {
        "audio_path": str(output_path),
        "audio_sha256": sha256_file(output_path),
        "audio_size_bytes": output_path.stat().st_size,
        "sample_rate_hz": sample_rate,
        "voice_kind": "MODEL_BUILTIN_CONDITIONAL_NO_EXTERNAL_REFERENCE",
        "audio_prompt_path_used": False,
    }


def wav_metrics(path: Path) -> dict[str, Any]:
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
    except ImportError as exc:
        raise PrideChatterboxPilotError("numpy and soundfile are required") from exc
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    require(data.shape[0] > 0, "private WAV is empty")
    require(data.shape[1] == 1, "private WAV must be mono")
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(data))))
    duration = float(data.shape[0] / rate)
    clipped_fraction = float(np.count_nonzero(np.abs(data) >= 0.999) / data.shape[0])
    passed = bool(duration > 0 and peak > 0 and rms >= 0.001 and clipped_fraction == 0)
    return {
        "sample_rate_hz": int(rate),
        "channels": int(info.channels),
        "duration_seconds": round(duration, 6),
        "peak_fraction": round(peak, 6),
        "rms_fraction": round(rms, 6),
        "clipped_sample_fraction": round(clipped_fraction, 8),
        "objective_format_pass": passed,
    }


def evaluate_asr_result(
    result: Mapping[str, Any],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    transcript = str(result.get("text") or "").strip()
    metrics = asr_common.ordered_metrics(PASSAGE_TEXT, transcript)
    words, anomalies = asr_common.verified_words(result, duration_seconds)
    passed = bool(metrics["pass"] and words and not anomalies)
    return {
        "status": "PASS" if passed else "FAIL",
        "transcript": transcript,
        "transcript_sha256": sha256_text(transcript),
        "audio_derived_word_timestamps": words,
        "word_timestamp_anomalies": anomalies,
        "word_timestamp_evidence_valid": bool(words) and not anomalies,
        **metrics,
        "pass": passed,
    }


def run_local_asr(
    *,
    audio_path: Path,
    duration_seconds: float,
    whisper_cache: Path,
    model_loader: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    model_path = whisper_cache.expanduser().resolve() / WHISPER_FILENAME
    verify_file(model_path, WHISPER_SHA256, "pinned Whisper model")
    if model_loader is None:
        try:
            import whisper  # noqa: PLC0415
        except ImportError as exc:
            raise PrideChatterboxPilotError("openai-whisper is required") from exc
        model_loader = whisper.load_model
    model = model_loader(WHISPER_MODEL, download_root=str(whisper_cache))
    result = model.transcribe(str(audio_path), **ASR_SETTINGS)
    report = evaluate_asr_result(result, duration_seconds=duration_seconds)
    return {
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "settings": ASR_SETTINGS,
        "required_score": ASR_SCORE_MIN,
        "required_coverage": ASR_COVERAGE_MIN,
        "audio_derived": True,
        "report": report,
        "status": report["status"],
    }


def write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def preflight(
    *,
    model_dir: Path,
    private_root: Path,
    paid_lock: Path,
    version_getter: Callable[[str], str] = metadata.version,
) -> tuple[dict[str, Any], bytes]:
    private_root = ensure_private_path(private_root, private_root=private_root)
    policy = validate_policy()
    source = validate_source()
    catalog = validate_catalog_truth()
    model_files = validate_model_bundle(model_dir)
    runtime = validate_runtime(version_getter)
    lock_before, lock = read_and_validate_paid_lock(paid_lock)
    payload = attempt_payload(model_dir=model_dir)
    fingerprint = canonical_hash(payload)
    assert_not_repeated(fingerprint)
    return (
        {
            "schema_version": SCHEMA,
            "status": "PREFLIGHT_PASS",
            "generated_at": utc_now(),
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "policy_path": str(POLICY_PATH),
            "policy_sha256": POLICY_SHA256,
            "policy_decision": policy["decision"],
            "source": source,
            "catalog_truth": catalog,
            "model": {
                "id": MODEL_ID,
                "revision": MODEL_REVISION,
                "loader": "ChatterboxMultilingualTTS.from_local",
                "directory": str(model_dir.expanduser().resolve()),
                "files": model_files,
                "runtime_package": RUNTIME_PACKAGE,
                "runtime_version": runtime,
            },
            "voice": {
                "kind": "MODEL_BUILTIN_CONDITIONAL_NO_EXTERNAL_REFERENCE",
                "audio_prompt_path": None,
                "external_reference_audio": None,
            },
            "paid_tts_lock": {
                "path": str(paid_lock),
                "sha256_before": sha256_bytes(lock_before),
                "access": "READ_ONLY",
                "current_holder": lock["current_holder"],
                "touched": False,
            },
            "attempt_payload": payload,
            "attempt_fingerprint": fingerprint,
            "private_root": str(private_root),
            "scope": {
                "sample_count": 1,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
                "full_title_generation_allowed": False,
            },
            "next_transition": "PRIVATE_SYNTHESIS_AND_OBJECTIVE_QA_ONLY",
        },
        lock_before,
    )


def execute(args: argparse.Namespace) -> dict[str, Any]:
    require(
        os.environ.get("EARNALISM_APPROVE_PRIVATE_CHATTERBOX_V3_PILOT") == "true",
        "set EARNALISM_APPROVE_PRIVATE_CHATTERBOX_V3_PILOT=true to run one sample",
    )
    report, lock_before = preflight(
        model_dir=args.model_dir,
        private_root=args.private_root,
        paid_lock=args.paid_lock,
    )
    fingerprint = report["attempt_fingerprint"]
    output = ensure_private_path(
        args.private_root / f"{PASSAGE_ID}-{fingerprint[:12]}.wav",
        private_root=args.private_root,
    )
    generated = synthesize(
        model_dir=args.model_dir,
        output_path=output,
        device=args.device or select_device(),
    )
    audio_metrics = wav_metrics(output)
    require(audio_metrics["objective_format_pass"], "private WAV format gate failed")
    asr = run_local_asr(
        audio_path=output,
        duration_seconds=float(audio_metrics["duration_seconds"]),
        whisper_cache=args.whisper_cache,
    )
    assert_paid_lock_unchanged(args.paid_lock, lock_before)
    passed = asr["status"] == "PASS"
    report.update(
        {
            "status": (
                "REPRESENTATIVE_OBJECTIVE_PASS_LISTENING_REVIEW_REQUIRED"
                if passed
                else "SOURCE_BOUND_DELIVERY_REQUIRED"
            ),
            "audio": {**generated, **audio_metrics},
            "objective_asr": asr,
            "paid_tts_lock": {
                **report["paid_tts_lock"],
                "sha256_after": sha256_file(args.paid_lock),
                "unchanged": True,
            },
            "release_ready": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
            "next_transition": (
                "BOUNDED_LISTENING_REVIEW_ONLY"
                if passed
                else "SOURCE_BOUND_DELIVERY_REQUIRED"
            ),
        }
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--device", choices=("mps", "cpu"))
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_PRIVATE_ROOT / "pilot_report.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report_path = ensure_private_path(args.report, private_root=args.private_root)
        if args.preflight:
            report, lock_before = preflight(
                model_dir=args.model_dir,
                private_root=args.private_root,
                paid_lock=args.paid_lock,
            )
            assert_paid_lock_unchanged(args.paid_lock, lock_before)
            report["paid_tts_lock"]["sha256_after"] = sha256_file(args.paid_lock)
            report["paid_tts_lock"]["unchanged"] = True
        else:
            report = execute(args)
        write_private_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except PrideChatterboxPilotError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
