#!/usr/bin/env python3
"""Build a local, review-only Sprint 1 audiobook release packet.

The builder performs no network, API, deployment, or live-publication action. It
accepts already-produced QA, upload, and endpoint proof, validates every active
publication gate, and stages mirrored controlled-publication artifacts beneath
an output directory that must be disjoint from the source tree.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[3]
ROOT_CONTROLLED_PUBLICATIONS = Path("data/controlled_publications")
BACKEND_CONTROLLED_PUBLICATIONS = Path("backend/data/controlled_publications")
ROOT_CONTROLLED_LAUNCH = Path("data/controlled_launch.json")
BACKEND_CONTROLLED_LAUNCH = Path("backend/data/controlled_launch.json")

REQUIRED_ASSET_KEYS = ("mp3", "timestamps", "vtt", "chapters", "meta")
REQUIRED_ARTIFACT_FILES = (
    "public_book.json",
    "reader_manifest.json",
    "approval_evidence.json",
    "source_evidence.json",
    "checksum_manifest.json",
)
TRACEABILITY_HASH_KEYS = ("source_hash", "content_hash", "provenance_hash")
ALLOWED_SYNC_TIERS = {
    "WORD_OR_PHRASE_SYNC_FLAGSHIP",
    "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
}
FATAL_FLAGS = {
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
}

QA_REQUIRED_GATES = (
    "source_content_toc_integrity_pass",
    "rights_metadata_pass",
    "covers_pass",
    "asr_manuscript_match_pass",
    "first_and_last_spans_match",
    "no_missing_duplicated_reordered_content",
    "no_fallback_audio",
    "no_placeholder_audio",
)
UPLOAD_REQUIRED_GATES = ("upload_checksum_pass",)
ENDPOINT_REQUIRED_GATES = (
    "no_stale_or_404_audio",
    "metadata_approval_pass",
    "browser_gate_pass",
)
REQUIRED_PUBLICATION_GATES = (
    *QA_REQUIRED_GATES,
    *ENDPOINT_REQUIRED_GATES[:1],
    *UPLOAD_REQUIRED_GATES,
    *ENDPOINT_REQUIRED_GATES[1:],
)

GATE_ALIASES: dict[str, tuple[str, ...]] = {
    "source_content_toc_integrity_pass": (
        "source_content_toc_integrity_pass",
        "source_content_toc",
        "content_toc_integrity",
    ),
    "rights_metadata_pass": ("rights_metadata_pass", "rights", "source_rights"),
    "covers_pass": ("covers_pass", "covers", "cover", "cover_gate_pass"),
    "asr_manuscript_match_pass": (
        "asr_manuscript_match_pass",
        "asr_manuscript",
        "asr_source_alignment",
    ),
    "first_and_last_spans_match": (
        "first_and_last_spans_match",
        "first_last_words_match",
        "first_and_last_words_match",
    ),
    "no_missing_duplicated_reordered_content": (
        "no_missing_duplicated_reordered_content",
        "content_complete_unique_ordered",
    ),
    "no_fallback_audio": ("no_fallback_audio", "fallback_tts_false"),
    "no_placeholder_audio": ("no_placeholder_audio", "placeholder_audio_false"),
    "no_stale_or_404_audio": (
        "no_stale_or_404_audio",
        "no_broken_endpoint",
        "endpoint_validation",
    ),
    "upload_checksum_pass": (
        "upload_checksum_pass",
        "remote_upload_checksum",
        "upload_checksum",
    ),
    "metadata_approval_pass": (
        "metadata_approval_pass",
        "metadata_approval",
        "metadata_api_status",
    ),
    "browser_gate_pass": ("browser_gate_pass", "browser_gate", "browser_status"),
}

PASS_STATUSES = {
    "APPROVED",
    "AUTO_APPROVED",
    "BENGALI_AUDIO_RELEASE_APPROVED",
    "FULL_RELEASE_QA_PASS",
    "PASS",
    "PASSED",
    "PUBLIC_AUDIO_RELEASE_APPROVED",
    "QA_PASSED",
    "UPLOADED_CHECKSUM_VERIFIED",
    "VERIFIED",
}
FAIL_STATUS_MARKERS = (
    "BLOCK",
    "FAIL",
    "HOLD",
    "MISSING",
    "NOT_RUN",
    "PENDING",
    "REQUIRED",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?$")


class ReleasePacketBlocked(RuntimeError):
    """Raised before any output write when release evidence is incomplete."""

    def __init__(self, blockers: str | Iterable[str]):
        if isinstance(blockers, str):
            values = [blockers]
        else:
            values = [str(item) for item in blockers]
        self.blockers = tuple(dict.fromkeys(item for item in values if item))
        super().__init__("; ".join(self.blockers) or "release packet blocked")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "RELEASE_PACKET_BLOCKED",
            "blockers": list(self.blockers),
            "api_calls_performed": False,
            "live_state_mutated": False,
            "public_paths_mutated": False,
        }


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ReleasePacketBlocked(f"{label} must not be a symlink: {path}")
    if not path.is_file():
        raise ReleasePacketBlocked(f"{label} is missing or not a file: {path}")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object_no_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReleasePacketBlocked(f"{label} is not valid strict JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleasePacketBlocked(f"{label} must contain a JSON object")
    return payload


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value.strip().lower()) is not None


def normalized_sha256(value: Any) -> str:
    return value.strip().lower() if valid_sha256(value) else ""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_output_boundary(
    output_dir: Path,
    source_root: Path,
    input_paths: Sequence[Path],
) -> tuple[Path, Path]:
    resolved_source = source_root.expanduser().resolve()
    resolved_output = output_dir.expanduser().resolve(strict=False)
    blockers: list[str] = []
    if not resolved_source.is_dir():
        blockers.append(f"source root is missing or not a directory: {resolved_source}")
    if resolved_output == Path(resolved_output.anchor):
        blockers.append("output directory cannot be a filesystem root")
    if _is_relative_to(resolved_output, resolved_source):
        blockers.append("output directory must be outside the source tree")
    if _is_relative_to(resolved_source, resolved_output):
        blockers.append("output directory must not contain the source tree")
    if output_dir.is_symlink():
        blockers.append("output directory must not be a symlink")
    if resolved_output.exists() and not resolved_output.is_dir():
        blockers.append("output path exists and is not a directory")
    if resolved_output.is_dir() and any(resolved_output.iterdir()):
        blockers.append("output directory must be empty")
    for path in input_paths:
        resolved_input = path.expanduser().resolve(strict=False)
        if resolved_input == resolved_output or _is_relative_to(resolved_input, resolved_output):
            blockers.append(f"output directory must not contain input evidence: {path}")
    if blockers:
        raise ReleasePacketBlocked(blockers)
    return resolved_output, resolved_source


def _dig(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _first_value(payload: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> Any:
    for path in paths:
        value = _dig(payload, path)
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


def status_passes(value: Any) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    if not normalized or any(marker in normalized for marker in FAIL_STATUS_MARKERS):
        return False
    return normalized in PASS_STATUSES or normalized.startswith("PASS_")


def gate_passes(value: Any) -> bool:
    if isinstance(value, Mapping):
        checks: list[bool] = []
        if "passed" in value:
            checks.append(value.get("passed") is True)
        for key in ("status", "decision", "result"):
            if key in value:
                checks.append(status_passes(value.get(key)))
        return bool(checks) and all(checks)
    return status_passes(value)


def _gate_maps(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = []
    for key in ("publication_gates", "release_gates", "objective_gates", "gates"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            maps.append(value)
    return maps


def validate_required_gates(
    payload: Mapping[str, Any],
    required: Sequence[str],
    label: str,
) -> tuple[dict[str, str], list[str]]:
    maps = _gate_maps(payload)
    results: dict[str, str] = {}
    blockers: list[str] = []
    for name in required:
        values: list[Any] = []
        for gate_map in maps:
            for alias in GATE_ALIASES[name]:
                if alias in gate_map:
                    values.append(gate_map[alias])
        if not values:
            blockers.append(f"{label} is missing required publication gate: {name}")
            results[name] = "MISSING"
        elif not all(gate_passes(value) for value in values):
            blockers.append(f"{label} publication gate did not pass: {name}")
            results[name] = "BLOCKED"
        else:
            results[name] = "PASS"
    return results, blockers


def _explicit_empty_blockers(
    payload: Mapping[str, Any],
    label: str,
    *,
    required: bool,
) -> list[str]:
    if "blockers" not in payload:
        return [f"{label} must include an explicit empty blockers list"] if required else []
    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        return [f"{label} blockers must be a list"]
    if blockers:
        return [f"{label} contains blockers: {', '.join(str(item) for item in blockers)}"]
    return []


def _true_fatal_flags(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FATAL_FLAGS and child is True:
                found.add(key)
            found.update(_true_fatal_flags(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_true_fatal_flags(child))
    return found


def _safe_relative_file(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _validate_checksum_manifest(title_dir: Path, payload: Mapping[str, Any], label: str) -> list[str]:
    blockers: list[str] = []
    entries = payload.get("files")
    if not isinstance(entries, list) or not entries:
        return [f"{label} checksum manifest must contain a non-empty files list"]
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            blockers.append(f"{label} checksum manifest contains a non-object entry")
            continue
        relative = _safe_relative_file(entry.get("file"))
        expected = normalized_sha256(entry.get("sha256"))
        if relative is None:
            blockers.append(f"{label} checksum manifest contains an unsafe file path")
            continue
        relative_text = relative.as_posix()
        if relative_text in seen:
            blockers.append(f"{label} checksum manifest repeats {relative_text}")
            continue
        seen.add(relative_text)
        if not expected:
            blockers.append(f"{label} checksum manifest has an invalid hash for {relative_text}")
            continue
        # Older manifests attempted to hash themselves. That recursive value is
        # not authoritative; the newly staged manifest deliberately omits it.
        if relative == Path("checksum_manifest.json"):
            continue
        target = title_dir / relative
        if not target.is_file() or target.is_symlink():
            blockers.append(f"{label} checksum target is missing or unsafe: {relative_text}")
            continue
        if sha256_file(target) != expected:
            blockers.append(f"{label} checksum mismatch for {relative_text}")
    return blockers


def _load_title_baseline(source_root: Path, slug: str) -> dict[str, Any]:
    root_dir = source_root / ROOT_CONTROLLED_PUBLICATIONS / slug
    backend_dir = source_root / BACKEND_CONTROLLED_PUBLICATIONS / slug
    blockers: list[str] = []
    if not SLUG_RE.fullmatch(slug):
        raise ReleasePacketBlocked(f"invalid controlled-publication slug: {slug}")

    documents: dict[str, dict[str, Any]] = {}
    backend_documents: dict[str, dict[str, Any]] = {}
    for filename in REQUIRED_ARTIFACT_FILES:
        try:
            documents[filename] = read_json_object(root_dir / filename, f"root {filename}")
            backend_documents[filename] = read_json_object(
                backend_dir / filename,
                f"backend {filename}",
            )
        except ReleasePacketBlocked as exc:
            blockers.extend(exc.blockers)
    if blockers:
        raise ReleasePacketBlocked(blockers)

    for filename in REQUIRED_ARTIFACT_FILES[:-1]:
        if documents[filename] != backend_documents[filename]:
            blockers.append(f"root/backend controlled-publication drift: {filename}")

    root_chapter_dir = root_dir / "chapters"
    backend_chapter_dir = backend_dir / "chapters"
    root_chapter_paths = sorted(root_chapter_dir.glob("chapter-*.json"))
    backend_chapter_paths = sorted(backend_chapter_dir.glob("chapter-*.json"))
    if not root_chapter_paths:
        blockers.append("controlled publication has no chapter JSON files")
    if [path.name for path in root_chapter_paths] != [path.name for path in backend_chapter_paths]:
        blockers.append("root/backend controlled-publication chapter file sets differ")

    chapters: dict[str, dict[str, Any]] = {}
    for root_path in root_chapter_paths:
        backend_path = backend_chapter_dir / root_path.name
        try:
            root_payload = read_json_object(root_path, f"root chapter {root_path.name}")
            backend_payload = read_json_object(backend_path, f"backend chapter {root_path.name}")
        except ReleasePacketBlocked as exc:
            blockers.extend(exc.blockers)
            continue
        if root_payload != backend_payload:
            blockers.append(f"root/backend controlled-publication drift: chapters/{root_path.name}")
        chapters[root_path.name] = root_payload

    public_book = documents["public_book.json"]
    reader_manifest = documents["reader_manifest.json"]
    approval = documents["approval_evidence.json"]
    source = documents["source_evidence.json"]

    for name, payload in (
        ("public_book.json", public_book),
        ("reader_manifest.json", reader_manifest),
        ("approval_evidence.json", approval),
        ("source_evidence.json", source),
    ):
        if payload.get("slug") != slug:
            blockers.append(f"{name} slug does not match {slug}")

    if public_book.get("approved_to_publish") is not True:
        blockers.append("public_book.json approved_to_publish must be true")
    if public_book.get("is_published") is not True:
        blockers.append("public_book.json is_published must be true")
    if public_book.get("isPublic") is not True or public_book.get("isLive") is not True:
        blockers.append("public_book.json public/live reader flags must be true")
    if str(public_book.get("rights_tier") or "").upper() != "A":
        blockers.append("public_book.json rights_tier must be A")
    if str(public_book.get("verification_status") or "").lower() not in {"approved", "verified"}:
        blockers.append("public_book.json verification_status must be approved")
    if str(public_book.get("qa_status") or "").upper() not in {"QA_PASSED", "PASS", "PASSED"}:
        blockers.append("public_book.json qa_status must pass")
    if public_book.get("allowCheckout") is not False or public_book.get("allowPayment") is not False:
        blockers.append("public_book.json checkout/payment flags must remain false")
    cover = next(
        (
            public_book.get(key)
            for key in ("cover_image_url", "cover_url", "coverImage", "cover_image")
            if isinstance(public_book.get(key), str) and public_book.get(key).strip()
        ),
        "",
    )
    if not cover:
        blockers.append("public_book.json is missing a front cover")

    for key in TRACEABILITY_HASH_KEYS:
        source_hash = normalized_sha256(source.get(key))
        public_hash = normalized_sha256(public_book.get(key))
        if not source_hash:
            blockers.append(f"source_evidence.json is missing valid {key}")
        if not public_hash:
            blockers.append(f"public_book.json is missing valid {key}")
        if source_hash and public_hash and source_hash != public_hash:
            blockers.append(f"public_book/source_evidence {key} mismatch")
    for key in ("source_url", "source_name", "source_license", "rights_basis"):
        if not isinstance(source.get(key), str) or not source.get(key).strip():
            blockers.append(f"source_evidence.json is missing {key}")
    if source.get("reader_facing_boilerplate_removed") is not True:
        blockers.append("source_evidence.json must confirm reader-facing boilerplate removal")

    if approval.get("approved_to_publish") is not True:
        blockers.append("approval_evidence.json approved_to_publish must be true")
    if str(approval.get("rights_tier") or "").upper() != "A":
        blockers.append("approval_evidence.json rights_tier must be A")
    if str(approval.get("verification_status") or "").lower() not in {"approved", "verified"}:
        blockers.append("approval_evidence.json verification_status must be approved")

    manifest_chapters = reader_manifest.get("chapters")
    chapter_count = _integer(reader_manifest.get("chapter_count"))
    if not isinstance(manifest_chapters, list) or not manifest_chapters:
        blockers.append("reader_manifest.json chapters must be a non-empty list")
    elif chapter_count != len(manifest_chapters):
        blockers.append("reader_manifest.json chapter_count does not match chapters")
    if reader_manifest.get("audio_enabled") is not False:
        blockers.append("reader_manifest.json audio_enabled must remain false")
    if reader_manifest.get("audiobook_enabled") is not False:
        blockers.append("reader_manifest.json audiobook_enabled must remain false")

    manifest_ids = {
        str(item.get("id") or "")
        for item in manifest_chapters or []
        if isinstance(item, Mapping)
    }
    for filename, chapter in chapters.items():
        expected_id = Path(filename).stem
        if chapter.get("id") != expected_id:
            blockers.append(f"{filename} id does not match its filename")
        if expected_id not in manifest_ids:
            blockers.append(f"reader_manifest.json is missing {expected_id}")
        content = chapter.get("content")
        content_hash = normalized_sha256(chapter.get("content_hash"))
        if not isinstance(content, str) or not content.strip():
            blockers.append(f"{filename} content is missing")
        elif not content_hash:
            blockers.append(f"{filename} content_hash is missing or invalid")
        elif sha256_bytes(content.encode("utf-8")) != content_hash:
            blockers.append(f"{filename} content_hash does not match content")

    blockers.extend(
        _validate_checksum_manifest(
            root_dir,
            documents["checksum_manifest.json"],
            "root controlled publication",
        )
    )
    blockers.extend(
        _validate_checksum_manifest(
            backend_dir,
            backend_documents["checksum_manifest.json"],
            "backend controlled publication",
        )
    )

    launch_documents: dict[str, dict[str, Any]] = {}
    for label, relative in (
        ("root", ROOT_CONTROLLED_LAUNCH),
        ("backend", BACKEND_CONTROLLED_LAUNCH),
    ):
        try:
            launch = read_json_object(source_root / relative, f"{label} controlled launch")
        except ReleasePacketBlocked as exc:
            blockers.extend(exc.blockers)
            continue
        for key in ("live_approved_slugs", "pipeline_slugs", "audio_enabled_slugs"):
            values = launch.get(key)
            if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
                blockers.append(f"{label} controlled launch {key} must be a string list")
            elif len(values) != len(set(values)):
                blockers.append(f"{label} controlled launch {key} contains duplicates")
        if slug not in (launch.get("live_approved_slugs") or []):
            blockers.append(f"{label} controlled launch does not approve the reader for {slug}")
        if slug in (launch.get("pipeline_slugs") or []):
            blockers.append(f"{label} controlled launch still marks {slug} as a pipeline title")
        launch_documents[label] = launch

    if blockers:
        raise ReleasePacketBlocked(blockers)
    return {
        "source_root": source_root,
        "root_dir": root_dir,
        "backend_dir": backend_dir,
        "documents": documents,
        "chapters": chapters,
        "launch": launch_documents,
        "traceability_hashes": {key: normalized_sha256(source[key]) for key in TRACEABILITY_HASH_KEYS},
    }


def _extract_hash(payload: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> str:
    return normalized_sha256(_first_value(payload, paths))


def _extract_qa_hashes(payload: Mapping[str, Any]) -> tuple[str, str]:
    audio = _extract_hash(
        payload,
        (
            ("hashes", "audio_sha256"),
            ("audio", "sha256"),
            ("audio_sha256",),
            ("audio_hash",),
            ("release_evidence", "audio_hash"),
            ("measured_quality", "audio_sha256"),
        ),
    )
    manuscript = _extract_hash(
        payload,
        (
            ("hashes", "manuscript_sha256"),
            ("hashes", "source_text_sha256"),
            ("manuscript_sha256",),
            ("source_sha256",),
            ("prepared_text_sha256",),
            ("source_hash",),
            ("release_evidence", "source_hash"),
            ("measured_evidence", "source_hash"),
        ),
    )
    return audio, manuscript


def _extract_binding_hashes(payload: Mapping[str, Any]) -> tuple[str, str]:
    audio = _extract_hash(
        payload,
        (
            ("hashes", "audio_sha256"),
            ("audio_sha256",),
            ("audio_hash",),
            ("release_evidence", "audio_hash"),
            ("endpoint", "audio_sha256"),
        ),
    )
    manuscript = _extract_hash(
        payload,
        (
            ("hashes", "manuscript_sha256"),
            ("hashes", "source_text_sha256"),
            ("manuscript_sha256",),
            ("source_sha256",),
            ("source_hash",),
            ("release_evidence", "source_hash"),
            ("endpoint", "source_sha256"),
        ),
    )
    return audio, manuscript


def _https_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme == "https" and bool(parsed.netloc) else ""


def _validate_evidence(
    qa: Mapping[str, Any],
    upload: Mapping[str, Any],
    endpoint: Mapping[str, Any],
    baseline: Mapping[str, Any],
    slug: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate_results: dict[str, str] = {}
    for payload, required, label in (
        (qa, QA_REQUIRED_GATES, "QA evidence"),
        (upload, UPLOAD_REQUIRED_GATES, "upload manifest"),
        (endpoint, ENDPOINT_REQUIRED_GATES, "endpoint proof"),
    ):
        results, gate_blockers = validate_required_gates(payload, required, label)
        gate_results.update(results)
        blockers.extend(gate_blockers)

    blockers.extend(_explicit_empty_blockers(qa, "QA evidence", required=True))
    blockers.extend(_explicit_empty_blockers(upload, "upload manifest", required=False))
    blockers.extend(_explicit_empty_blockers(endpoint, "endpoint proof", required=True))
    for label, payload in (("QA evidence", qa), ("upload manifest", upload), ("endpoint proof", endpoint)):
        if payload.get("slug") != slug:
            blockers.append(f"{label} slug does not match {slug}")

    if not status_passes(qa.get("status") or qa.get("decision")):
        blockers.append("QA evidence status is not an explicit release pass")
    if qa.get("auto_approval_decision") is False:
        blockers.append("QA evidence auto_approval_decision is false")
    if qa.get("can_publish_audio_now") is False:
        blockers.append("QA evidence can_publish_audio_now is false")
    if qa.get("lock_restored") is not True:
        blockers.append("QA evidence must confirm lock_restored=true")
    if qa.get("publication_performed") is True:
        blockers.append("QA evidence says publication was already performed")
    for key in ("hook_blockers", "failure_reasons"):
        value = qa.get(key)
        if value not in (None, []):
            blockers.append(f"QA evidence {key} must be empty when present")

    qa_audio_hash, qa_manuscript_hash = _extract_qa_hashes(qa)
    if not qa_audio_hash:
        blockers.append("QA evidence is missing a valid audio SHA-256")
    if not qa_manuscript_hash:
        blockers.append("QA evidence is missing a valid manuscript SHA-256")

    asr_score = _number(
        _first_value(
            qa,
            (
                ("asr_manuscript_score",),
                ("asr_source_score",),
                ("source_match_score",),
                ("measured_quality", "asr_source_score"),
                ("scores", "transcript_match_score"),
            ),
        )
    )
    if asr_score is None or asr_score < 9.7:
        blockers.append(f"ASR/manuscript score must be >= 9.7, got {asr_score}")
    first_words = _first_value(
        qa,
        (("first_words_match",), ("measured_quality", "first_words_match")),
    )
    last_words = _first_value(
        qa,
        (("last_words_match",), ("measured_quality", "last_words_match")),
    )
    if first_words is not True or last_words is not True:
        blockers.append("QA evidence must explicitly pass first and last word matching")

    listening = _first_value(qa, (("owner_listening_gate",), ("listening_gate",)))
    listening = listening if isinstance(listening, Mapping) else {}
    listening_score = _number(
        _first_value(
            qa,
            (
                ("owner_listening_gate", "minimum_overall_score"),
                ("listening_gate", "minimum_overall_score"),
                ("overall_listening_score",),
                ("scores", "overall_listening_score"),
                ("measured_quality", "listening_minimum_score"),
            ),
        )
    )
    listening_confidence = _number(
        _first_value(
            qa,
            (
                ("owner_listening_gate", "minimum_confidence"),
                ("listening_gate", "minimum_confidence"),
                ("confidence_score",),
                ("scores", "confidence_score"),
                ("measured_quality", "listening_minimum_confidence"),
            ),
        )
    )
    language = str(
        _first_value(qa, (("language",),))
        or baseline["documents"]["reader_manifest.json"].get("language")
        or ""
    ).strip().lower()
    listening_minimum = 9.2 if language in {"ben", "bn", "bengali", "বাংলা"} else 9.3
    if listening.get("passes") is not True:
        blockers.append("QA evidence owner/full-book listening gate must explicitly pass")
    if listening_score is None or listening_score < listening_minimum:
        blockers.append(
            f"listening score must be >= {listening_minimum}, got {listening_score}"
        )
    if listening_confidence is None or listening_confidence < 0.90:
        blockers.append(f"listening confidence must be >= 0.90, got {listening_confidence}")
    sample_count = _integer(listening.get("sample_count"))
    if sample_count is None or sample_count < 4:
        blockers.append("full-title listening evidence must contain at least four samples")
    fatal_list = listening.get("fatal_flags")
    if not isinstance(fatal_list, list):
        blockers.append("listening evidence must include an explicit fatal_flags list")
        fatal_list = []
    listed_fatal = {str(item) for item in fatal_list if str(item)}
    true_fatal = _true_fatal_flags(qa)
    fatal = sorted(listed_fatal | true_fatal)
    if fatal:
        blockers.append(f"fatal listening flags are present: {', '.join(fatal)}")

    sync_tier = str(
        _first_value(
            qa,
            (("sync_tier",), ("measured_quality", "sync_tier"), ("sync", "tier")),
        )
        or ""
    ).strip().upper()
    auto_estimated_sync = _first_value(
        qa,
        (
            ("auto_estimated_sync",),
            ("measured_quality", "auto_estimated_sync"),
            ("sync", "auto_estimated_sync"),
        ),
    )
    if sync_tier not in ALLOWED_SYNC_TIERS:
        blockers.append("sync_tier must be measured paragraph/stanza or word/phrase sync")
    if auto_estimated_sync is not False:
        blockers.append("auto_estimated_sync must be explicitly false")

    provider = str(
        _first_value(qa, (("provider",), ("selected_arm", "provider"), ("tts", "provider")))
        or ""
    ).strip()
    voice = str(
        _first_value(qa, (("voice",), ("selected_arm", "voice"), ("tts", "voice")))
        or ""
    ).strip()
    model = str(
        _first_value(qa, (("model",), ("selected_arm", "model"), ("tts", "model")))
        or ""
    ).strip()
    style = str(
        _first_value(
            qa,
            (
                ("style",),
                ("prosody",),
                ("style_profile",),
                ("selected_arm", "style"),
                ("tts", "style"),
            ),
        )
        or ""
    ).strip()
    for key, value in (("provider", provider), ("voice", voice), ("model", model), ("style", style)):
        if not value:
            blockers.append(f"QA evidence is missing audiobook {key}")

    audio_size = _integer(
        _first_value(qa, (("audio_size_bytes",), ("audio", "size_bytes")))
    )
    audio_duration = _number(
        _first_value(qa, (("audio_duration_seconds",), ("audio", "duration_seconds")))
    )
    if audio_size is None or audio_size <= 0:
        blockers.append("QA evidence audio_size_bytes must be positive")
    if audio_duration is None or audio_duration <= 0:
        blockers.append("QA evidence audio_duration_seconds must be positive")

    if not status_passes(upload.get("status")):
        blockers.append("upload manifest status is not PASS")
    storage_backend = str(upload.get("storage_backend") or "").strip()
    if not storage_backend:
        blockers.append("upload manifest is missing storage_backend")
    upload_audio_binding, upload_manuscript_hash = _extract_binding_hashes(upload)
    if upload_audio_binding and qa_audio_hash and upload_audio_binding != qa_audio_hash:
        blockers.append("upload manifest audio hash does not match QA audio hash")
    if not upload_manuscript_hash:
        blockers.append("upload manifest is missing a manuscript SHA-256 binding")
    elif qa_manuscript_hash and upload_manuscript_hash != qa_manuscript_hash:
        blockers.append("upload manifest manuscript hash does not match QA evidence")

    urls = upload.get("urls")
    checksums = upload.get("checksums")
    if not isinstance(urls, Mapping):
        blockers.append("upload manifest urls must be an object")
        urls = {}
    if not isinstance(checksums, Mapping):
        blockers.append("upload manifest checksums must be an object")
        checksums = {}
    artifact_hashes: dict[str, str] = {}
    artifact_sizes: dict[str, int] = {}
    normalized_urls: dict[str, str] = {}
    for key in REQUIRED_ASSET_KEYS:
        url = _https_url(urls.get(key))
        check = checksums.get(key)
        if not url:
            blockers.append(f"upload manifest {key} URL must be HTTPS")
        else:
            normalized_urls[key] = url
        if not isinstance(check, Mapping):
            blockers.append(f"upload manifest is missing {key} checksum proof")
            continue
        local_hash = normalized_sha256(check.get("local_sha256"))
        remote_hash = normalized_sha256(check.get("remote_sha256"))
        if not local_hash:
            blockers.append(f"upload manifest {key} local_sha256 is missing or invalid")
        if not remote_hash:
            blockers.append(f"upload manifest {key} remote_sha256 is missing or invalid")
        if local_hash and remote_hash and local_hash != remote_hash:
            blockers.append(f"upload manifest {key} local/remote hashes differ")
        if check.get("match") is not True or check.get("resolves") is not True:
            blockers.append(f"upload manifest {key} checksum/resolve proof did not pass")
        check_status = _integer(check.get("status"))
        if check_status not in {200, 206}:
            blockers.append(f"upload manifest {key} HTTP status must be 200 or 206")
        local_size = _integer(check.get("local_size"))
        remote_size = _integer(check.get("remote_size"))
        if local_size is None or local_size <= 0 or remote_size is None or remote_size <= 0:
            blockers.append(f"upload manifest {key} sizes must be positive")
        elif local_size != remote_size:
            blockers.append(f"upload manifest {key} local/remote sizes differ")
        check_url = check.get("url")
        if check_url not in (None, "") and check_url != url:
            blockers.append(f"upload manifest {key} checksum URL does not match urls entry")
        if local_hash:
            artifact_hashes[key] = local_hash
        if local_size:
            artifact_sizes[key] = local_size
    if qa_audio_hash and artifact_hashes.get("mp3") != qa_audio_hash:
        blockers.append("uploaded mp3 hash does not match QA audio hash")
    if audio_size and artifact_sizes.get("mp3") != audio_size:
        blockers.append("uploaded mp3 size does not match QA audio_size_bytes")

    if not status_passes(endpoint.get("status") or endpoint.get("decision")):
        blockers.append("endpoint proof status is not PASS")
    endpoint_url = _https_url(
        _first_value(
            endpoint,
            (("endpoint_url",), ("audiobook_endpoint_url",), ("url",), ("endpoint", "url")),
        )
    )
    endpoint_status = _integer(
        _first_value(
            endpoint,
            (("http_status",), ("status_code",), ("audio_proxy_http",), ("endpoint", "http_status")),
        )
    )
    response_size = _integer(
        _first_value(
            endpoint,
            (
                ("response_size_bytes",),
                ("audio_proxy_range_bytes",),
                ("size_bytes",),
                ("endpoint", "response_size_bytes"),
            ),
        )
    )
    if not endpoint_url:
        blockers.append("endpoint proof must include an HTTPS audiobook endpoint URL")
    if endpoint_status not in {200, 206}:
        blockers.append("endpoint proof HTTP status must be 200 or 206")
    if response_size is None or response_size <= 0:
        blockers.append("endpoint proof response size must be positive")
    if endpoint.get("range_request_pass") is False:
        blockers.append("endpoint proof range_request_pass is false")
    endpoint_audio_hash, endpoint_manuscript_hash = _extract_binding_hashes(endpoint)
    if not endpoint_audio_hash:
        blockers.append("endpoint proof is missing a valid audio SHA-256 binding")
    elif qa_audio_hash and endpoint_audio_hash != qa_audio_hash:
        blockers.append("endpoint proof audio hash does not match QA/upload evidence")
    if not endpoint_manuscript_hash:
        blockers.append("endpoint proof is missing a valid manuscript SHA-256 binding")
    elif qa_manuscript_hash and endpoint_manuscript_hash != qa_manuscript_hash:
        blockers.append("endpoint proof manuscript hash does not match QA/upload evidence")

    if blockers:
        raise ReleasePacketBlocked(blockers)
    return {
        "gate_results": gate_results,
        "audio_sha256": qa_audio_hash,
        "manuscript_sha256": qa_manuscript_hash,
        "artifact_sha256": artifact_hashes,
        "artifact_sizes": artifact_sizes,
        "urls": normalized_urls,
        "storage_backend": storage_backend,
        "provider": provider,
        "voice": voice,
        "model": model,
        "style": style,
        "asr_manuscript_score": asr_score,
        "first_words_match": first_words,
        "last_words_match": last_words,
        "listening_score": listening_score,
        "listening_confidence": listening_confidence,
        "listening_sample_count": sample_count,
        "sync_tier": sync_tier,
        "auto_estimated_sync": auto_estimated_sync,
        "audio_size_bytes": audio_size,
        "audio_duration_seconds": audio_duration,
        "endpoint_url": endpoint_url,
        "endpoint_http_status": endpoint_status,
        "endpoint_response_size_bytes": response_size,
        "language": language,
    }


def _timestamp_for_packet(
    qa: Mapping[str, Any],
    upload: Mapping[str, Any],
    endpoint: Mapping[str, Any],
) -> str:
    value = _first_value(
        endpoint,
        (("checked_at",), ("validated_at",), ("generated_at",), ("timestamp",)),
    ) or _first_value(upload, (("uploaded_at",), ("generated_at",))) or _first_value(
        qa,
        (("finished_at",), ("generated_at",), ("timestamp",)),
    )
    return str(value).strip() if value else iso_now()


def _build_public_book(
    source: Mapping[str, Any],
    slug: str,
    evidence: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    payload = copy.deepcopy(dict(source))
    assets = dict(evidence["urls"])
    sync_tier = str(evidence["sync_tier"])
    sync_mode = "word_or_phrase" if sync_tier == "WORD_OR_PHRASE_SYNC_FLAGSHIP" else "section_following"
    payload.update(
        {
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": True,
            "audiobook_provider": evidence["provider"],
            "audiobook_voice": evidence["voice"],
            "audiobook_model": evidence["model"],
            "audiobook_style_profile": evidence["style"],
            "audio_asset_slug": slug,
            "audiobook_assets": assets,
            "audiobook_assets_updated_at": generated_at,
            "audiobook": {
                "url": assets["mp3"],
                "provider": evidence["provider"],
                "voice": evidence["voice"],
                "model": evidence["model"],
                "style": evidence["style"],
                "size": evidence["audio_size_bytes"],
                "duration_ms": round(float(evidence["audio_duration_seconds"]) * 1000),
                "sync_mode": sync_mode,
                "sync_tier": sync_tier,
                "highlight_sync_enabled": sync_tier == "WORD_OR_PHRASE_SYNC_FLAGSHIP",
                "audio_sha256": evidence["audio_sha256"],
                "source_sha256": evidence["manuscript_sha256"],
                "asset_sha256": dict(evidence["artifact_sha256"]),
                "assets": assets,
                "release_gate": "APPROVED",
                "qa_status": "QA_PASSED",
                "updated_at": generated_at,
            },
            "updated_at": generated_at,
        }
    )
    formats = payload.get("formats")
    if isinstance(formats, list) and "Audiobook" not in formats:
        payload["formats"] = [*formats, "Audiobook"]
    return payload


def _build_reader_manifest(source: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(source))
    payload["audio_enabled"] = False
    payload["audiobook_enabled"] = False
    for key in ("audiobook", "audiobook_assets", "audio_assets", "audio_url", "audiobook_url"):
        payload.pop(key, None)
    if "audio" in payload:
        payload["audio"] = {
            "enabled": False,
            "provider": "",
            "voice": "",
            "url": "",
            "assets": {},
        }
    return payload


def _build_approval_evidence(
    source: Mapping[str, Any],
    slug: str,
    evidence: Mapping[str, Any],
    generated_at: str,
    input_hashes: Mapping[str, str],
    traceability_hashes: Mapping[str, str],
) -> dict[str, Any]:
    payload = copy.deepcopy(dict(source))
    payload.update(
        {
            "slug": slug,
            "approved_to_publish": True,
            "qa_status": "QA_PASSED",
            "approval_scope": "sprint1_local_release_packet_all_gates_passed",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_enabled": True,
            "asr_manuscript_score": evidence["asr_manuscript_score"],
            "first_words_match": True,
            "last_words_match": True,
            "no_missing_duplicated_reordered_content": True,
            "listening_qa_minimum_score": evidence["listening_score"],
            "listening_qa_minimum_confidence": evidence["listening_confidence"],
            "listening_qa_sample_count": evidence["listening_sample_count"],
            "listening_qa_fatal_flags": [],
            "sync_tier": evidence["sync_tier"],
            "auto_estimated_sync": False,
            "audio_sha256": evidence["audio_sha256"],
            "source_sha256": evidence["manuscript_sha256"],
            "publication_traceability_hashes": dict(traceability_hashes),
            "uploaded_artifact_sha256": dict(evidence["artifact_sha256"]),
            "upload_status": "UPLOADED_CHECKSUM_VERIFIED",
            "storage_backend": evidence["storage_backend"],
            "endpoint_url": evidence["endpoint_url"],
            "endpoint_http_status": evidence["endpoint_http_status"],
            "metadata_approval_status": "PASS",
            "browser_gate_status": "PASS",
            "quality_claim": "MEASURED_RELEASE_MINIMUM_PASS_NO_10_OF_10_CLAIM",
            "release_packet_input_sha256": dict(input_hashes),
            "release_blockers": [],
            "approved_at": generated_at,
        }
    )
    return payload


def _build_checksum_manifest(
    slug: str,
    generated_at: str,
    title_files: Mapping[str, bytes],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "slug": slug,
        "generated_at": generated_at,
        "files": [
            {"file": name, "sha256": sha256_bytes(payload)}
            for name, payload in sorted(title_files.items())
        ],
        "uploaded_artifacts": [
            {
                "artifact": key,
                "url": evidence["urls"][key],
                "sha256": evidence["artifact_sha256"][key],
                "size_bytes": evidence["artifact_sizes"][key],
            }
            for key in REQUIRED_ASSET_KEYS
        ],
    }


def _build_launch(source: Mapping[str, Any], slug: str) -> dict[str, Any]:
    payload = copy.deepcopy(dict(source))
    audio_slugs = list(payload["audio_enabled_slugs"])
    if slug not in audio_slugs:
        audio_slugs.append(slug)
    payload["audio_enabled_slugs"] = audio_slugs
    return payload


def _prepare_staged_files(
    baseline: Mapping[str, Any],
    evidence: Mapping[str, Any],
    qa: Mapping[str, Any],
    upload: Mapping[str, Any],
    endpoint: Mapping[str, Any],
    input_paths: Mapping[str, Path],
    slug: str,
) -> tuple[dict[Path, bytes], dict[str, Any]]:
    generated_at = _timestamp_for_packet(qa, upload, endpoint)
    input_hashes = {name: sha256_file(path) for name, path in input_paths.items()}
    documents = baseline["documents"]
    public_book = _build_public_book(documents["public_book.json"], slug, evidence, generated_at)
    reader_manifest = _build_reader_manifest(documents["reader_manifest.json"])
    approval = _build_approval_evidence(
        documents["approval_evidence.json"],
        slug,
        evidence,
        generated_at,
        input_hashes,
        baseline["traceability_hashes"],
    )

    title_files: dict[str, bytes] = {
        "approval_evidence.json": json_bytes(approval),
        "public_book.json": json_bytes(public_book),
        "reader_manifest.json": json_bytes(reader_manifest),
        "source_evidence.json": json_bytes(documents["source_evidence.json"]),
    }
    for filename, chapter in baseline["chapters"].items():
        title_files[f"chapters/{filename}"] = json_bytes(chapter)
    checksum_manifest = _build_checksum_manifest(slug, generated_at, title_files, evidence)
    title_files["checksum_manifest.json"] = json_bytes(checksum_manifest)

    staged: dict[Path, bytes] = {}
    for relative_root in (ROOT_CONTROLLED_PUBLICATIONS, BACKEND_CONTROLLED_PUBLICATIONS):
        for relative_name, payload in title_files.items():
            staged[relative_root / slug / relative_name] = payload
    staged[ROOT_CONTROLLED_LAUNCH] = json_bytes(_build_launch(baseline["launch"]["root"], slug))
    staged[BACKEND_CONTROLLED_LAUNCH] = json_bytes(
        _build_launch(baseline["launch"]["backend"], slug)
    )

    staged_hashes = {
        relative.as_posix(): sha256_bytes(payload)
        for relative, payload in sorted(staged.items(), key=lambda item: item[0].as_posix())
    }
    source_hashes: dict[str, str] = {}
    for relative in (
        ROOT_CONTROLLED_LAUNCH,
        BACKEND_CONTROLLED_LAUNCH,
        *(
            ROOT_CONTROLLED_PUBLICATIONS / slug / name
            for name in REQUIRED_ARTIFACT_FILES
        ),
        *(
            BACKEND_CONTROLLED_PUBLICATIONS / slug / name
            for name in REQUIRED_ARTIFACT_FILES
        ),
    ):
        source_path = baseline["source_root"] / relative
        if source_path.is_file():
            source_hashes[relative.as_posix()] = sha256_file(source_path)

    report = {
        "schema_version": 1,
        "status": "STAGED_RELEASE_PACKET_READY",
        "generated_at": generated_at,
        "slug": slug,
        "mode": "LOCAL_REVIEW_ONLY",
        "publication_performed": False,
        "api_calls_performed": False,
        "provider_calls_performed": False,
        "deployment_performed": False,
        "live_state_mutated": False,
        "public_paths_mutated": False,
        "mirrored_controlled_publication_artifacts": True,
        "reader_manifest_audio_flags": "DISABLED_BY_CONTROLLED_TRUTH_CONTRACT",
        "validated_publication_gates": dict(evidence["gate_results"]),
        "quality_thresholds": {
            "asr_manuscript_min": 9.7,
            "listening_min": 9.2 if evidence["language"] in {"ben", "bn", "bengali", "বাংলা"} else 9.3,
            "listening_confidence_min": 0.90,
            "auto_estimated_sync_required": False,
        },
        "hash_bindings": {
            "audio_sha256": evidence["audio_sha256"],
            "manuscript_sha256": evidence["manuscript_sha256"],
            "publication_traceability": dict(baseline["traceability_hashes"]),
            "uploaded_artifacts": dict(evidence["artifact_sha256"]),
        },
        "input_evidence": {
            name: {"path": str(path), "sha256": input_hashes[name]}
            for name, path in input_paths.items()
        },
        "source_snapshot_sha256": source_hashes,
        "staged_file_sha256": staged_hashes,
        "release_blockers": [],
        "next_action": "Review and validate the staged diff; this packet does not publish or deploy.",
    }
    staged[Path("release_packet.json")] = json_bytes(report)
    return staged, report


def _write_staged_files(output_dir: Path, staged: Mapping[Path, bytes]) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.staging-",
            dir=str(output_dir.parent),
        )
    )
    try:
        for relative, payload in staged.items():
            if relative.is_absolute() or ".." in relative.parts:
                raise ReleasePacketBlocked(f"unsafe staged output path: {relative}")
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        if output_dir.exists():
            if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
                raise ReleasePacketBlocked("output directory changed or became non-empty during staging")
            output_dir.rmdir()
        os.replace(temporary, output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_release_packet(
    qa_evidence_path: str | Path,
    upload_manifest_path: str | Path,
    endpoint_proof_path: str | Path,
    output_dir: str | Path,
    source_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Validate release evidence and atomically stage a review-only packet."""

    qa_path = Path(qa_evidence_path).expanduser()
    upload_path = Path(upload_manifest_path).expanduser()
    endpoint_path = Path(endpoint_proof_path).expanduser()
    output_path, source_path = validate_output_boundary(
        Path(output_dir),
        Path(source_root),
        (qa_path, upload_path, endpoint_path),
    )
    qa = read_json_object(qa_path, "QA evidence")
    upload = read_json_object(upload_path, "upload manifest")
    endpoint = read_json_object(endpoint_path, "endpoint proof")
    slug = str(qa.get("slug") or "").strip()
    if not SLUG_RE.fullmatch(slug):
        raise ReleasePacketBlocked("QA evidence has a missing or invalid slug")
    baseline = _load_title_baseline(source_path, slug)
    evidence = _validate_evidence(qa, upload, endpoint, baseline, slug)
    staged, report = _prepare_staged_files(
        baseline,
        evidence,
        qa,
        upload,
        endpoint,
        {
            "qa_evidence": qa_path.resolve(),
            "upload_manifest": upload_path.resolve(),
            "endpoint_proof": endpoint_path.resolve(),
        },
        slug,
    )
    _write_staged_files(output_path, staged)
    return {**report, "output_dir": str(output_path)}


build_packet = build_release_packet


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qa-evidence",
        "--title-qa-evidence",
        "--qa",
        dest="qa_evidence",
        required=True,
        type=Path,
    )
    parser.add_argument("--upload-manifest", required=True, type=Path)
    parser.add_argument("--endpoint-proof", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_release_packet(
            args.qa_evidence,
            args.upload_manifest,
            args.endpoint_proof,
            args.output_dir,
            args.source_root,
        )
    except ReleasePacketBlocked as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2))
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed on local I/O errors.
        print(
            json.dumps(
                {
                    "status": "RELEASE_PACKET_ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                    "api_calls_performed": False,
                    "live_state_mutated": False,
                    "public_paths_mutated": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
