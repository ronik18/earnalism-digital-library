#!/usr/bin/env python3
"""Normalize completed release-factory evidence for the Sprint 1 packet builder.

This adapter is deliberately local and read-only apart from its output
directory.  It performs no provider, network, upload, metadata, publication,
deployment, or paid-lock operation.  A factory PASS label is never sufficient:
the underlying raw ASR, listening, sync, checksum, metadata, and browser
evidence must each be explicit and mutually bound.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


try:
    import sprint1_release_packet_builder as packet_builder
except ModuleNotFoundError:
    _BUILDER_PATH = Path(__file__).with_name("sprint1_release_packet_builder.py")
    _BUILDER_SPEC = importlib.util.spec_from_file_location(
        "sprint1_release_packet_builder",
        _BUILDER_PATH,
    )
    if not _BUILDER_SPEC or not _BUILDER_SPEC.loader:
        raise RuntimeError(f"cannot load release packet builder: {_BUILDER_PATH}")
    packet_builder = importlib.util.module_from_spec(_BUILDER_SPEC)
    _BUILDER_SPEC.loader.exec_module(packet_builder)


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_FILENAMES = (
    "normalized_release_qa.json",
    "normalized_upload_manifest.json",
    "endpoint_proof.json",
)
FACTORY_STAGES = (
    "cover_queue",
    "manuscript_queue",
    "rights_metadata_preflight_queue",
    "tts_queue",
    "asr_sync_queue",
    "upload_queue",
    "metadata_publish_queue",
    "browser_gate_queue",
)
FATAL_LISTENING_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
)
NO_FATAL_HARD_FLAGS = (
    "no_robotic_cadence",
    "no_mechanical_texture",
    "no_list_reading_rhythm",
    "no_choppy_joins",
    "no_placeholder_audio",
)
CONTENT_EXACTNESS_MIN = 0.999
CONTENT_SCORE_PERFECT = 10.0
CONTENT_SCORE_TOLERANCE = 1e-9
CONTENT_RANGE_RE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", re.IGNORECASE)


class NormalizationBlocked(RuntimeError):
    """Raised before output is written when factory evidence is incomplete."""

    def __init__(self, blockers: str | Sequence[str]):
        values = [blockers] if isinstance(blockers, str) else list(blockers)
        self.blockers = tuple(dict.fromkeys(str(value) for value in values if str(value)))
        super().__init__("; ".join(self.blockers) or "factory evidence normalization blocked")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "FACTORY_EVIDENCE_NORMALIZATION_BLOCKED",
            "blockers": list(self.blockers),
            "provider_calls_performed": False,
            "network_calls_performed": False,
            "upload_performed": False,
            "publication_performed": False,
            "paid_lock_touched": False,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dig(payload: Mapping[str, Any], *path: str) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _first(payload: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> Any:
    for path in paths:
        value = _dig(payload, *path)
        if value not in (None, ""):
            return value
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _https_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    parsed = urlparse(candidate)
    return candidate if parsed.scheme == "https" and bool(parsed.netloc) else ""


def _sha256(value: Any) -> str:
    return packet_builder.normalized_sha256(value)


def _empty_list(payload: Mapping[str, Any], key: str, label: str, blockers: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        blockers.append(f"{label} must include an explicit {key} list")
    elif value:
        blockers.append(f"{label} {key} must be empty")


def _stage(
    stage_results: Mapping[str, Any],
    name: str,
    blockers: list[str],
) -> Mapping[str, Any]:
    value = stage_results.get(name)
    if not isinstance(value, Mapping):
        blockers.append(f"factory QA is missing {name} evidence")
        return {}
    if value.get("status") != "PASS":
        blockers.append(f"factory stage {name} did not explicitly PASS")
    stage_blockers = value.get("blockers")
    if stage_blockers not in (None, []):
        blockers.append(f"factory stage {name} contains blockers")
    if value.get("ready_for_next_stage") is False:
        blockers.append(f"factory stage {name} is not ready for the next stage")
    return value


def _resolve_reference(
    value: Any,
    *,
    label: str,
    evidence_dir: Path,
    source_root: Path,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise NormalizationBlocked(f"{label} path is missing")
    path = Path(value.strip()).expanduser()
    candidates = [path] if path.is_absolute() else [evidence_dir / path, source_root / path]
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if candidate.is_symlink() or resolved.is_symlink():
            raise NormalizationBlocked(f"{label} must not be a symlink: {candidate}")
        if resolved.is_file():
            return resolved
    raise NormalizationBlocked(f"{label} is missing: {value}")


def _read_reference(
    value: Any,
    *,
    label: str,
    evidence_dir: Path,
    source_root: Path,
) -> tuple[Path, dict[str, Any]]:
    path = _resolve_reference(
        value,
        label=label,
        evidence_dir=evidence_dir,
        source_root=source_root,
    )
    return path, packet_builder.read_json_object(path, label)


def _artifact_reference(stage: Mapping[str, Any], key: str) -> Any:
    return _first(
        stage,
        (
            ("artifacts", key),
            ("metrics", key),
            ("updated_fields", key),
            (key,),
        ),
    )


def _headers(payload: Mapping[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in payload.items()}


def _response_size(headers: Mapping[str, Any]) -> int | None:
    normalized = _headers(headers)
    content_range = normalized.get("content-range", "").strip()
    match = CONTENT_RANGE_RE.fullmatch(content_range)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        if end >= start:
            return end - start + 1
    content_length = _integer(normalized.get("content-length"))
    return content_length if content_length and content_length > 0 else None


def _source_input_hashes(paths: Mapping[str, Path]) -> dict[str, str]:
    return {name: packet_builder.sha256_file(path) for name, path in paths.items()}


def _validate_output_dir(output_dir: Path, source_root: Path, input_paths: Sequence[Path]) -> Path:
    resolved = output_dir.expanduser().resolve(strict=False)
    blockers: list[str] = []
    if resolved == Path(resolved.anchor):
        blockers.append("normalization output cannot be a filesystem root")
    if output_dir.is_symlink():
        blockers.append("normalization output directory must not be a symlink")
    if resolved.exists() and not resolved.is_dir():
        blockers.append("normalization output exists and is not a directory")
    if resolved.is_dir() and any(resolved.iterdir()):
        blockers.append("normalization output directory must be empty")
    source = source_root.expanduser().resolve(strict=False)
    try:
        resolved.relative_to(source)
    except ValueError:
        pass
    else:
        blockers.append("generated normalization artifacts must remain outside the source tree")
    for path in input_paths:
        candidate = path.expanduser().resolve(strict=False)
        if candidate == resolved:
            blockers.append("normalization output must not overwrite input evidence")
    if blockers:
        raise NormalizationBlocked(blockers)
    return resolved


def _validate_upload(
    upload: Mapping[str, Any],
    slug: str,
    blockers: list[str],
) -> dict[str, Any]:
    if upload.get("slug") != slug:
        blockers.append("upload manifest slug does not match factory QA")
    if upload.get("status") != "PASS":
        blockers.append("upload manifest status must be PASS")
    storage_backend = str(upload.get("storage_backend") or "").strip()
    if not storage_backend:
        blockers.append("upload manifest storage_backend is missing")
    urls = _mapping(upload.get("urls"))
    checksums = _mapping(upload.get("checksums"))
    normalized_urls: dict[str, str] = {}
    normalized_checks: dict[str, dict[str, Any]] = {}
    for key in packet_builder.REQUIRED_ASSET_KEYS:
        url = _https_url(urls.get(key))
        check = _mapping(checksums.get(key))
        if not url:
            blockers.append(f"upload manifest {key} URL must be HTTPS")
        if not check:
            blockers.append(f"upload manifest is missing {key} checksum proof")
            continue
        local_hash = _sha256(check.get("local_sha256"))
        remote_hash = _sha256(check.get("remote_sha256"))
        local_size = _integer(check.get("local_size"))
        remote_size = _integer(check.get("remote_size"))
        status = _integer(check.get("status"))
        if not local_hash or not remote_hash:
            blockers.append(f"upload manifest {key} requires valid local and remote SHA-256")
        elif local_hash != remote_hash:
            blockers.append(f"upload manifest {key} local and remote SHA-256 differ")
        if check.get("match") is not True or check.get("resolves") is not True:
            blockers.append(f"upload manifest {key} checksum/resolve proof did not pass")
        if status not in {200, 206}:
            blockers.append(f"upload manifest {key} HTTP status must be 200 or 206")
        if local_size is None or remote_size is None or local_size <= 0 or local_size != remote_size:
            blockers.append(f"upload manifest {key} local/remote sizes must be equal and positive")
        check_url = check.get("url")
        if check_url not in (None, "", url):
            blockers.append(f"upload manifest {key} checksum URL differs from urls.{key}")
        if url and local_hash and local_size and status in {200, 206}:
            normalized_urls[key] = url
            normalized_checks[key] = {
                "url": url,
                "status": status,
                "resolves": True,
                "local_sha256": local_hash,
                "remote_sha256": remote_hash,
                "match": True,
                "local_size": local_size,
                "remote_size": remote_size,
            }
    return {
        "storage_backend": storage_backend,
        "urls": normalized_urls,
        "checksums": normalized_checks,
        "audio_sha256": _dig(normalized_checks, "mp3", "local_sha256"),
        "audio_size_bytes": _dig(normalized_checks, "mp3", "local_size"),
    }


def _normalize_release_qa(
    qa: Mapping[str, Any],
    upload_values: Mapping[str, Any],
    *,
    qa_path: Path,
    source_root: Path,
    input_hashes: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    slug = str(qa.get("slug") or "").strip()
    if not packet_builder.SLUG_RE.fullmatch(slug):
        blockers.append("factory QA slug is missing or invalid")
    if qa.get("auto_approval_decision") is not True:
        blockers.append("factory QA auto_approval_decision must be true")
    _empty_list(qa, "blocker_list", "factory QA", blockers)
    if qa.get("lock_restored") is not True:
        blockers.append("factory QA must include explicit lock_restored=true")
    if qa.get("phase") not in (None, "final"):
        blockers.append("factory QA must be final, not pre-upload")

    stage_results = _mapping(qa.get("stage_results"))
    stages = {name: _stage(stage_results, name, blockers) for name in FACTORY_STAGES}
    cover = stages["cover_queue"]
    manuscript = stages["manuscript_queue"]
    rights = stages["rights_metadata_preflight_queue"]
    tts = stages["tts_queue"]
    asr = stages["asr_sync_queue"]
    metadata = stages["metadata_publish_queue"]
    browser = stages["browser_gate_queue"]

    if _dig(cover, "cover_status", "status") != "PASS":
        blockers.append("factory cover evidence must explicitly be PASS")
    if manuscript.get("content_integrity_status") != "PASS":
        blockers.append("factory manuscript content_integrity_status must be PASS")
    if rights.get("production_metadata_ready") is not True:
        blockers.append("factory rights metadata must be production-ready")

    provider = str(_first(tts, (("metrics", "provider"), ("updated_fields", "tts_provider"))) or "").strip()
    model = str(_first(tts, (("metrics", "model"), ("updated_fields", "tts_model"))) or "").strip()
    voice = str(_first(tts, (("metrics", "voice"), ("updated_fields", "tts_voice"))) or "").strip()
    style = str(
        _first(
            tts,
            (
                ("metrics", "style"),
                ("metrics", "profile"),
                ("updated_fields", "tts_style"),
            ),
        )
        or ""
    ).strip()
    for name, value in (("provider", provider), ("model", model), ("voice", voice), ("style", style)):
        if not value:
            blockers.append(f"factory TTS evidence is missing {name}")
    fallback_tts_used = _first(
        tts,
        (
            ("fallback_tts_used",),
            ("metrics", "fallback_tts_used"),
            ("updated_fields", "fallback_tts_used"),
        ),
    )
    if fallback_tts_used is not False:
        blockers.append("factory TTS evidence must explicitly confirm fallback_tts_used=false")
    duration = _number(
        _first(
            tts,
            (
                ("metrics", "duration_seconds"),
                ("metrics", "audio_duration_seconds"),
                ("updated_fields", "audio_duration_seconds"),
            ),
        )
    )
    if duration is None or duration <= 0:
        blockers.append("factory TTS evidence requires a positive audio duration")

    evidence_dir = qa_path.parent
    try:
        diagnosis_path, diagnosis = _read_reference(
            _artifact_reference(asr, "asr_alignment_diagnosis"),
            label="raw ASR diagnosis",
            evidence_dir=evidence_dir,
            source_root=source_root,
        )
        timestamps_path, timestamps = _read_reference(
            _artifact_reference(asr, "timestamps"),
            label="measured sync timestamps",
            evidence_dir=evidence_dir,
            source_root=source_root,
        )
        listening_path, listening = _read_reference(
            _artifact_reference(asr, "listening_quality_report"),
            label="full-title listening report",
            evidence_dir=evidence_dir,
            source_root=source_root,
        )
    except (NormalizationBlocked, packet_builder.ReleasePacketBlocked) as exc:
        blockers.extend(getattr(exc, "blockers", (str(exc),)))
        diagnosis_path = timestamps_path = listening_path = Path()
        diagnosis = timestamps = listening = {}

    raw_asr_score = _number(
        _first(
            diagnosis,
            (
                ("raw_asr_score",),
                ("asr_transcript_match_score",),
                ("score",),
            ),
        )
    )
    if str(diagnosis.get("asr_release_status") or "").upper() == "SUPPORTING_DIAGNOSTIC_WEAK":
        blockers.append("diagnostic/projection-only ASR cannot satisfy the release gate")
    if raw_asr_score is None or raw_asr_score < 9.7:
        blockers.append(f"raw audio-derived ASR score must be >= 9.7, got {raw_asr_score}")
    first_words = diagnosis.get("first_words_match")
    last_words = diagnosis.get("last_words_match")
    if first_words is not True or last_words is not True:
        blockers.append("raw ASR diagnosis must explicitly pass first and last words")
    if diagnosis.get("frontmatter_absent") is not True:
        blockers.append("raw ASR diagnosis must explicitly confirm frontmatter_absent=true")

    scores = _mapping(qa.get("scores"))
    coverage = _number(diagnosis.get("coverage"))
    token_order = _number(diagnosis.get("token_order_similarity"))
    truncation_score = _number(scores.get("truncation_score"))
    duplicate_score = _number(scores.get("duplicate_segment_score"))
    no_missing = diagnosis.get("no_missing_content") is True or bool(
        coverage is not None
        and coverage >= CONTENT_EXACTNESS_MIN
        and truncation_score is not None
        and truncation_score >= CONTENT_SCORE_PERFECT - CONTENT_SCORE_TOLERANCE
    )
    no_duplicate = diagnosis.get("no_duplicate_content") is True or bool(
        duplicate_score is not None
        and duplicate_score >= CONTENT_SCORE_PERFECT - CONTENT_SCORE_TOLERANCE
    )
    no_reordered = diagnosis.get("no_reordered_content") is True or bool(
        token_order is not None and token_order >= CONTENT_EXACTNESS_MIN
    )
    if not no_missing:
        blockers.append("factory evidence does not prove no missing narrated content")
    if not no_duplicate:
        blockers.append("factory evidence does not prove no duplicated narrated content")
    if not no_reordered:
        blockers.append("factory evidence does not prove no reordered narrated content")

    audio_hash = str(upload_values.get("audio_sha256") or "")
    audio_size = _integer(upload_values.get("audio_size_bytes"))
    timestamp_audio_hash = _sha256(timestamps.get("audio_hash"))
    manuscript_hash = _sha256(
        _first(
            timestamps,
            (
                ("source_text_hash",),
                ("manuscript_sha256",),
            ),
        )
    )
    if not audio_hash or timestamp_audio_hash != audio_hash:
        blockers.append("measured sync audio hash must match the uploaded MP3")
    if not manuscript_hash:
        blockers.append("measured sync evidence is missing a valid manuscript/source hash")
    timestamp_slug = timestamps.get("slug")
    if timestamp_slug not in (None, slug):
        blockers.append("measured sync slug does not match factory QA")
    timestamp_items = timestamps.get("words")
    if not isinstance(timestamp_items, list) or not timestamp_items:
        timestamp_items = timestamps.get("cues")
    if not isinstance(timestamp_items, list) or not timestamp_items:
        blockers.append("measured sync evidence has no word/phrase/paragraph cues")
    auto_estimated_sync = _first(
        timestamps,
        (
            ("auto_estimated_sync",),
        ),
    )
    asr_auto_estimated = _first(
        asr,
        (
            ("auto_estimated_sync",),
            ("metrics", "auto_estimated_sync"),
            ("updated_fields", "auto_estimated_sync"),
        ),
    )
    if auto_estimated_sync is not False or asr_auto_estimated is not False:
        blockers.append("factory sync evidence must explicitly confirm auto_estimated_sync=false")
    alignment_method = str(
        _first(
            timestamps,
            (
                ("alignment_method",),
                ("sync_method",),
            ),
        )
        or ""
    ).strip()
    sync_tier = str(
        _first(
            timestamps,
            (
                ("sync_release_tier",),
            ),
        )
        or _first(
            asr,
            (
                ("metrics", "sync_release_tier"),
                ("updated_fields", "sync_release_tier"),
            ),
        )
        or ""
    ).strip().upper()
    if not sync_tier and alignment_method == "openai_verbose_json_word_timestamps":
        sync_tier = "WORD_OR_PHRASE_SYNC_FLAGSHIP"
    if sync_tier not in packet_builder.ALLOWED_SYNC_TIERS:
        blockers.append("factory sync evidence lacks an allowed measured sync tier")
    if alignment_method not in {
        "openai_verbose_json_word_timestamps",
        "measured_group_audio_duration",
    }:
        blockers.append("factory sync alignment method is not explicitly measured/provider-derived")

    listening_quality = _mapping(listening.get("listening_quality"))
    if listening.get("slug") != slug:
        blockers.append("listening report slug does not match factory QA")
    if listening_quality.get("status") != "PASS":
        blockers.append("full-title listening report status must be PASS")
    _empty_list(listening_quality, "blockers", "full-title listening report", blockers)
    samples = listening_quality.get("samples")
    sample_count = len(samples) if isinstance(samples, list) else 0
    if sample_count < 6:
        blockers.append("full-title listening report must contain at least six samples")
    aggregate = _mapping(listening_quality.get("aggregate"))
    listening_score = _number(aggregate.get("overall_listening_score"))
    listening_confidence = _number(aggregate.get("confidence_score"))
    language = str(qa.get("language") or listening.get("language") or "").strip().lower()
    listening_minimum = 9.2 if language in {"ben", "bn", "bengali", "বাংলা"} else 9.3
    if listening_score is None or listening_score < listening_minimum:
        blockers.append(
            f"full-title listening score must be >= {listening_minimum}, got {listening_score}"
        )
    if listening_confidence is None or listening_confidence < 0.90:
        blockers.append(
            f"full-title listening confidence must be >= 0.90, got {listening_confidence}"
        )
    fatal_flags: list[str] = []
    for flag in FATAL_LISTENING_FLAGS:
        value = listening_quality.get(flag)
        if value is not False:
            blockers.append(f"full-title listening report must explicitly confirm {flag}=false")
        if value is True:
            fatal_flags.append(flag)
    hard_flags = _mapping(qa.get("hard_flags"))
    if hard_flags.get("fallback_tts_used_false") is not True:
        blockers.append("factory QA hard flags do not prove no fallback TTS")
    if hard_flags.get("auto_estimated_sync_false") is not True:
        blockers.append("factory QA hard flags do not prove measured sync")
    for flag in NO_FATAL_HARD_FLAGS:
        if hard_flags.get(flag) is not True:
            blockers.append(f"factory QA hard flag {flag} must be true")

    metadata_updated = _mapping(metadata.get("updated_fields"))
    if metadata_updated.get("production_approval_succeeded") is not True:
        blockers.append("factory metadata evidence must confirm production approval succeeded")
    if metadata_updated.get("audiobook_release_gate") != "APPROVED":
        blockers.append("factory metadata audiobook_release_gate must be APPROVED")
    if metadata_updated.get("rights_metadata_status") != "PASS":
        blockers.append("factory metadata rights status must be PASS")
    browser_updated = _mapping(browser.get("updated_fields"))
    if browser_updated.get("browser_gate_status") != "PASS":
        blockers.append("factory browser gate must explicitly confirm PASS")

    if blockers:
        raise NormalizationBlocked(blockers)

    reference_hashes = {
        "raw_asr_diagnosis": packet_builder.sha256_file(diagnosis_path),
        "measured_sync_timestamps": packet_builder.sha256_file(timestamps_path),
        "full_title_listening_report": packet_builder.sha256_file(listening_path),
    }
    normalized = {
        "schema_version": 1,
        "slug": slug,
        "status": "FULL_RELEASE_QA_PASS",
        "language": language,
        "provider": provider,
        "model": model,
        "voice": voice,
        "style": style,
        "audio_hash": audio_hash,
        "source_sha256": manuscript_hash,
        "audio_size_bytes": audio_size,
        "audio_duration_seconds": duration,
        "asr_source_score": raw_asr_score,
        "first_words_match": True,
        "last_words_match": True,
        "owner_listening_gate": {
            "passes": True,
            "sample_count": sample_count,
            "minimum_overall_score": listening_score,
            "minimum_confidence": listening_confidence,
            "fatal_flags": fatal_flags,
        },
        "sync_tier": sync_tier,
        "auto_estimated_sync": False,
        "release_gates": {
            "source_content_toc_integrity_pass": True,
            "rights_metadata_pass": True,
            "covers_pass": True,
            "asr_manuscript_match_pass": True,
            "first_and_last_spans_match": True,
            "no_missing_duplicated_reordered_content": True,
            "no_fallback_audio": True,
            "no_placeholder_audio": True,
        },
        "blockers": [],
        "hook_blockers": [],
        "failure_reasons": [],
        "lock_restored": True,
        "lock_evidence": "COPIED_FROM_EXPLICIT_FACTORY_QA_PROOF",
        "normalization_provider_calls_performed": False,
        "normalization_paid_lock_touched": False,
        "normalization_input_sha256": dict(input_hashes),
        "normalization_reference_sha256": reference_hashes,
        "finished_at": str(qa.get("timestamp") or packet_builder.iso_now()),
    }
    context = {
        "slug": slug,
        "audio_sha256": audio_hash,
        "manuscript_sha256": manuscript_hash,
        "metadata_stage": metadata,
        "browser_stage": browser,
        "language": language,
    }
    return normalized, context


def _normalize_upload(
    upload: Mapping[str, Any],
    upload_values: Mapping[str, Any],
    context: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "slug": context["slug"],
        "status": "PASS",
        "storage_backend": upload_values["storage_backend"],
        "audio_sha256": context["audio_sha256"],
        "source_sha256": context["manuscript_sha256"],
        "urls": dict(upload_values["urls"]),
        "checksums": dict(upload_values["checksums"]),
        "release_gates": {"upload_checksum_pass": True},
        "blockers": [],
        "normalization_provider_calls_performed": False,
        "normalization_input_sha256": dict(input_hashes),
        "uploaded_at": str(upload.get("uploaded_at") or packet_builder.iso_now()),
    }


def _normalize_endpoint(
    endpoint: Mapping[str, Any],
    upload_values: Mapping[str, Any],
    context: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    blockers: list[str] = []
    slug = str(context["slug"])
    if endpoint.get("slug") != slug:
        blockers.append("endpoint/browser evidence slug does not match factory QA")
    if endpoint.get("status") != "PASS":
        blockers.append("endpoint/browser evidence status must be PASS")
    _empty_list(endpoint, "blockers", "endpoint/browser evidence", blockers)

    metrics = _mapping(endpoint.get("metrics"))
    routes = _mapping(metrics.get("routes"))
    assets = _mapping(metrics.get("assets"))
    browser = _mapping(metrics.get("browser"))
    endpoint_updated = _mapping(endpoint.get("updated_fields"))
    if endpoint_updated.get("browser_gate_status") != "PASS":
        blockers.append("endpoint/browser evidence must explicitly confirm browser_gate_status=PASS")
    if browser.get("audio_control_visible") is not True:
        blockers.append("endpoint/browser evidence must prove a visible audio control")
    browser_latency = _number(browser.get("audio_start_latency_ms"))
    if browser_latency is None or browser_latency < 0 or browser_latency >= 1000:
        blockers.append("endpoint/browser evidence must prove audio start latency below 1000ms")
    audio_probe = _mapping(browser.get("audio_probe"))
    if audio_probe.get("audio_found") is not True or audio_probe.get("playback_advanced") is not True:
        blockers.append("endpoint/browser evidence must prove actual playback advanced")
    console_errors = browser.get("console_errors")
    if not isinstance(console_errors, list) or console_errors:
        blockers.append("endpoint/browser evidence must include an empty console_errors list")
    for name in ("detail", "reader", "audiobook"):
        route = _mapping(routes.get(name))
        if route.get("ok") is not True:
            blockers.append(f"endpoint/browser evidence route {name} did not pass")
    audio_route = _mapping(routes.get("audiobook"))
    endpoint_url = _https_url(audio_route.get("url"))
    status = _integer(audio_route.get("status"))
    headers = _headers(_mapping(audio_route.get("headers")))
    response_size = _response_size(headers)
    if not endpoint_url:
        blockers.append("endpoint/browser evidence audiobook route must be HTTPS")
    if status != 206:
        blockers.append("endpoint/browser evidence must prove ranged HTTP 206")
    if headers.get("accept-ranges", "").lower() != "bytes":
        blockers.append("endpoint/browser evidence must prove Accept-Ranges: bytes")
    if not headers.get("content-range", "").lower().startswith("bytes 0-"):
        blockers.append("endpoint/browser evidence must prove a range beginning at byte 0")
    if response_size is None or response_size <= 0:
        blockers.append("endpoint/browser evidence lacks a positive ranged response size")

    upload_urls = _mapping(upload_values.get("urls"))
    for key in packet_builder.REQUIRED_ASSET_KEYS:
        asset = _mapping(assets.get(key))
        if asset.get("ok") is not True or _integer(asset.get("status")) not in {200, 206}:
            blockers.append(f"endpoint/browser evidence asset {key} did not resolve")
        if asset.get("url") != upload_urls.get(key):
            blockers.append(f"endpoint/browser evidence asset {key} URL differs from upload manifest")

    private_origins = metrics.get("private_origin_checks")
    if isinstance(private_origins, Mapping):
        for key, proof in private_origins.items():
            if not isinstance(proof, Mapping) or proof.get("anonymous_access_denied") is not True:
                blockers.append(f"private origin proof did not deny anonymous access for {key}")

    metadata = _mapping(context.get("metadata_stage"))
    metadata_artifacts = _mapping(metadata.get("artifacts"))
    metadata_endpoint = _mapping(metadata_artifacts.get("audiobook_endpoint"))
    if metadata_endpoint.get("url") != endpoint_url:
        blockers.append("metadata and browser evidence refer to different audiobook endpoints")
    if _integer(metadata_endpoint.get("status")) not in {200, 206}:
        blockers.append("metadata evidence audiobook endpoint did not return 200/206")
    if metadata_endpoint.get("ok") is not True:
        blockers.append("metadata evidence audiobook endpoint is not explicitly OK")

    browser_stage = _mapping(context.get("browser_stage"))
    if browser_stage.get("status") != "PASS":
        blockers.append("factory final browser stage did not PASS")
    if blockers:
        raise NormalizationBlocked(blockers)
    return {
        "schema_version": 1,
        "slug": slug,
        "status": "PASS",
        "endpoint_url": endpoint_url,
        "http_status": status,
        "response_size_bytes": response_size,
        "range_request_pass": True,
        "audio_sha256": context["audio_sha256"],
        "source_sha256": context["manuscript_sha256"],
        "release_gates": {
            "no_stale_or_404_audio": True,
            "metadata_approval_pass": True,
            "browser_gate_pass": True,
        },
        "blockers": [],
        "normalization_network_calls_performed": False,
        "normalization_input_sha256": dict(input_hashes),
        "checked_at": str(endpoint.get("finished_at") or packet_builder.iso_now()),
    }


def _write_outputs(output_dir: Path, payloads: Mapping[str, Mapping[str, Any]]) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.normalizing-",
            dir=str(output_dir.parent),
        )
    )
    try:
        for filename in OUTPUT_FILENAMES:
            payload = payloads[filename]
            (temporary / filename).write_bytes(packet_builder.json_bytes(payload))
        if output_dir.exists():
            if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
                raise NormalizationBlocked(
                    "normalization output changed or became non-empty during staging"
                )
            output_dir.rmdir()
        os.replace(temporary, output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def normalize_factory_evidence(
    factory_qa_path: str | Path,
    upload_manifest_path: str | Path,
    endpoint_evidence_path: str | Path,
    output_dir: str | Path,
    source_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Normalize a completed factory evidence set without external operations."""

    qa_path = Path(factory_qa_path).expanduser()
    upload_path = Path(upload_manifest_path).expanduser()
    endpoint_path = Path(endpoint_evidence_path).expanduser()
    source_path = Path(source_root).expanduser().resolve(strict=False)
    output_path = _validate_output_dir(
        Path(output_dir),
        source_path,
        (qa_path, upload_path, endpoint_path),
    )
    qa = packet_builder.read_json_object(qa_path, "factory final QA")
    upload = packet_builder.read_json_object(upload_path, "factory upload manifest")
    endpoint = packet_builder.read_json_object(endpoint_path, "factory endpoint/browser evidence")
    input_paths = {
        "factory_qa": qa_path.resolve(),
        "upload_manifest": upload_path.resolve(),
        "endpoint_evidence": endpoint_path.resolve(),
    }
    input_hashes = _source_input_hashes(input_paths)
    slug = str(qa.get("slug") or "").strip()
    upload_blockers: list[str] = []
    upload_values = _validate_upload(upload, slug, upload_blockers)
    if upload_blockers:
        raise NormalizationBlocked(upload_blockers)
    normalized_qa, context = _normalize_release_qa(
        qa,
        upload_values,
        qa_path=qa_path.resolve(),
        source_root=source_path,
        input_hashes=input_hashes,
    )
    normalized_upload = _normalize_upload(
        upload,
        upload_values,
        context,
        input_hashes,
    )
    normalized_endpoint = _normalize_endpoint(
        endpoint,
        upload_values,
        context,
        input_hashes,
    )
    payloads = {
        "normalized_release_qa.json": normalized_qa,
        "normalized_upload_manifest.json": normalized_upload,
        "endpoint_proof.json": normalized_endpoint,
    }
    _write_outputs(output_path, payloads)
    return {
        "status": "NORMALIZED_FACTORY_EVIDENCE_READY",
        "slug": context["slug"],
        "output_dir": str(output_path),
        "outputs": {
            name: {
                "path": str(output_path / name),
                "sha256": packet_builder.sha256_file(output_path / name),
            }
            for name in OUTPUT_FILENAMES
        },
        "provider_calls_performed": False,
        "network_calls_performed": False,
        "upload_performed": False,
        "publication_performed": False,
        "paid_lock_touched": False,
        "next_command": (
            "python3 internal/audiobook_lab/scripts/sprint1_release_packet_builder.py "
            f"--qa-evidence {output_path / 'normalized_release_qa.json'} "
            f"--upload-manifest {output_path / 'normalized_upload_manifest.json'} "
            f"--endpoint-proof {output_path / 'endpoint_proof.json'} "
            "--output-dir <outside-repo-empty-release-packet-dir>"
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory-qa", required=True, type=Path)
    parser.add_argument("--upload-manifest", required=True, type=Path)
    parser.add_argument("--endpoint-evidence", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-root", default=ROOT, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = normalize_factory_evidence(
            args.factory_qa,
            args.upload_manifest,
            args.endpoint_evidence,
            args.output_dir,
            args.source_root,
        )
    except (NormalizationBlocked, packet_builder.ReleasePacketBlocked) as exc:
        blockers = getattr(exc, "blockers", (str(exc),))
        print(
            json.dumps(
                NormalizationBlocked(blockers).as_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed on local I/O errors.
        print(
            json.dumps(
                {
                    "status": "FACTORY_EVIDENCE_NORMALIZATION_ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                    "provider_calls_performed": False,
                    "network_calls_performed": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "paid_lock_touched": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
