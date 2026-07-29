#!/usr/bin/env python3
"""Build and finalize immutable Earnalism audiobook package-v2 releases.

The first supported profile repackages the already-approved
``book-2b9853ec52`` production narration into two customer-delivery segments.
It never invokes TTS.  ``build-canary`` writes local masters, delivery files,
sidecars, a release descriptor, and a storage upload plan.  ``finalize`` binds
verified primary and DR B2 VersionIds into the canonical package manifest.

``build-approved-legacy`` is the generic release-candidate producer.  It only
accepts an already-public, checksum-bound legacy audiobook whose mirrored
controlled approval evidence passes every current content, listening, rights,
sync, upload, endpoint, and browser gate.  It preserves the exact approved
legacy assets as provenance, creates a PCM master, and encodes immutable
96-kbps mono delivery segments at measured paragraph/stanza cue boundaries.

No command in this module mutates controlled publication truth or uploads
objects.  Upload and verification are delegated to
``audiobook_package_storage_v2.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audiobook_packages import (  # noqa: E402
    PACKAGE_SCHEMA_VERSION,
    canonical_json_bytes,
    immutable_release_prefix,
    validate_audiobook_package,
    with_canonical_package_version,
)


CANARY_SLUG = "book-2b9853ec52"
CANARY_TITLE = "দুই বিঘা জমি"
CANARY_AUTHOR = "রবীন্দ্রনাথ ঠাকুর"
CANARY_EXPECTED_AUDIO_SHA256 = (
    "a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5"
)
CANARY_SPLIT_SECONDS = 138.720
CANARY_RUN_DIR = (
    Path("/Users/ronikbasak/Documents/GitHub/earnalism-digital-library")
    / "internal/audiobook_lab/release_gate"
    / "book-2b9853ec52_20260707T053510Z"
)
CANARY_AUDIO_NAME = (
    "book-2b9853ec52_sarvam_bulbul_v3_ratan_literary_warm_pacing_final.mp3"
)

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")
PACKAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
VTT_CUE_RE = re.compile(
    r"(?m)^(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
    r"\s+-->\s+"
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)
APPROVED_LEGACY_ASSETS = ("mp3", "timestamps", "vtt", "chapters", "meta")
MEASURED_SYNC_GRANULARITIES = frozenset(
    {
        "paragraph",
        "stanza",
        "paragraph_or_stanza",
    }
)
TARGET_SEGMENT_SECONDS = 10 * 60
MIN_TARGET_SEGMENT_SECONDS = 8 * 60
MAX_SEGMENT_SECONDS = 12 * 60
AUDIO_DURATION_TOLERANCE_SECONDS = 1.5
CHAPTER_BOUNDARY_TOLERANCE_SECONDS = 0.01


class PackageBuildError(RuntimeError):
    """Raised when package inputs or generated artifacts fail closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageBuildError(f"Cannot read valid JSON from {path}: {exc}") from exc


def run_checked(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageBuildError(f"Command failed: {' '.join(command)}") from exc


def ffprobe_duration_ms(path: Path) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = float(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        raise PackageBuildError(f"Cannot measure audio duration for {path}: {exc}") from exc
    duration_ms = round(duration * 1000)
    if duration_ms <= 0:
        raise PackageBuildError(f"Measured non-positive audio duration for {path}")
    return duration_ms


def format_vtt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def cue_paragraphs(cue: Mapping[str, Any]) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in str(cue.get("text") or "").split("\n\n")
        if paragraph.strip()
    ]


def cue_word_count(cue: Mapping[str, Any]) -> int:
    return len(str(cue.get("text") or "").split())


def rebased_cues(
    cues: Iterable[Mapping[str, Any]],
    *,
    segment_start_seconds: float,
) -> list[dict[str, Any]]:
    rebased: list[dict[str, Any]] = []
    for local_index, cue in enumerate(cues):
        start = round(float(cue["start"]) - segment_start_seconds, 3)
        end = round(float(cue["end"]) - segment_start_seconds, 3)
        if start < 0 or end <= start:
            raise PackageBuildError("Cue boundaries do not fit the selected segment")
        rebased.append(
            {
                "id": str(cue["id"]),
                "index": local_index,
                "start": start,
                "end": end,
                "duration_seconds": round(end - start, 3),
                "text": str(cue["text"]),
                "granularity": str(cue.get("granularity") or "paragraph_or_stanza"),
            }
        )
    return rebased


def write_vtt(path: Path, cues: Iterable[Mapping[str, Any]]) -> None:
    lines = ["WEBVTT", ""]
    for index, cue in enumerate(cues, start=1):
        lines.extend(
            [
                str(index),
                (
                    f"{format_vtt_time(float(cue['start']))} --> "
                    f"{format_vtt_time(float(cue['end']))}"
                ),
                str(cue["text"]).replace("\n\n", "\n"),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def file_asset(
    *,
    asset_id: str,
    path: Path,
    key: str,
    mime_type: str,
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "local_path": str(path.resolve()),
        "key": key,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "mime_type": mime_type,
    }


def _require_sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise PackageBuildError(f"{label} must be a lowercase SHA-256")
    return normalized


def _require_number(value: Any, label: str, minimum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise PackageBuildError(f"{label} is missing or invalid") from None
    if not math.isfinite(parsed) or parsed < minimum:
        raise PackageBuildError(f"{label} must be at least {minimum}")
    return parsed


def ffprobe_audio_profile(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name,channels,sample_rate,bit_rate",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        streams = payload.get("streams")
        profile = streams[0] if isinstance(streams, list) and streams else {}
    except (
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageBuildError(f"Cannot inspect audio profile for {path}: {exc}") from exc
    if not isinstance(profile, dict):
        raise PackageBuildError(f"Cannot inspect audio profile for {path}")
    return profile


def _validate_delivery_audio_profile(path: Path) -> None:
    profile = ffprobe_audio_profile(path)
    try:
        channels = int(profile.get("channels"))
        sample_rate = int(profile.get("sample_rate"))
        bit_rate = int(profile.get("bit_rate"))
    except (TypeError, ValueError):
        raise PackageBuildError(
            f"Delivery segment lacks a measurable MP3 profile: {path}"
        ) from None
    if (
        str(profile.get("codec_name") or "").lower() != "mp3"
        or channels != 1
        or sample_rate != 48_000
        or not 94_000 <= bit_rate <= 98_000
    ):
        raise PackageBuildError(
            "Delivery segments must be MP3, 96-kbps, mono, and 48-kHz"
        )


def _publication_dirs(repo_root: Path, slug: str) -> tuple[Path, Path]:
    if not SLUG_RE.fullmatch(slug):
        raise PackageBuildError("Approved legacy slug is invalid")
    return (
        repo_root / "backend/data/controlled_publications" / slug,
        repo_root / "data/controlled_publications" / slug,
    )


def _checksum_rows(document: Mapping[str, Any]) -> dict[str, str]:
    rows = document.get("files")
    if not isinstance(rows, list):
        raise PackageBuildError("Controlled checksum manifest lacks files")
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        filename = str(row.get("file") or "")
        digest = str(row.get("sha256") or "").lower()
        if filename and SHA256_RE.fullmatch(digest):
            result[filename] = digest
    return result


def _load_mirrored_publication(repo_root: Path, slug: str) -> dict[str, Any]:
    filenames = (
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "approval_evidence.json",
        "checksum_manifest.json",
    )
    directories = _publication_dirs(repo_root, slug)
    mirrors: list[dict[str, Any]] = []
    for directory in directories:
        if not directory.is_dir():
            raise PackageBuildError(
                f"Controlled publication mirror is missing: {directory}"
            )
        documents = {name: read_json(directory / name) for name in filenames}
        checksum_rows = _checksum_rows(documents["checksum_manifest.json"])
        for filename in filenames[:-1]:
            expected = checksum_rows.get(filename)
            if expected != sha256_file(directory / filename):
                raise PackageBuildError(
                    f"Controlled publication checksum is stale or missing: {filename}"
                )
        mirrors.append(documents)
    if mirrors[0] != mirrors[1]:
        raise PackageBuildError(
            "Backend and repository controlled-publication mirrors diverge"
        )
    documents = mirrors[0]
    return {
        "dirs": directories,
        "public_book": documents["public_book.json"],
        "reader_manifest": documents["reader_manifest.json"],
        "source_evidence": documents["source_evidence.json"],
        "approval_evidence": documents["approval_evidence.json"],
        "checksum_manifest": documents["checksum_manifest.json"],
    }


def _vtt_time_seconds(parts: tuple[str, ...]) -> float:
    hours, minutes, seconds, milliseconds = (int(value) for value in parts)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def _vtt_ranges(path: Path) -> list[tuple[float, float]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackageBuildError(f"Cannot read UTF-8 VTT from {path}: {exc}") from exc
    if not text.lstrip("\ufeff").startswith("WEBVTT"):
        raise PackageBuildError("Legacy VTT does not start with WEBVTT")
    ranges = [
        (
            _vtt_time_seconds(match.groups()[:4]),
            _vtt_time_seconds(match.groups()[4:]),
        )
        for match in VTT_CUE_RE.finditer(text)
    ]
    if not ranges:
        raise PackageBuildError("Legacy VTT has no measurable cues")
    return ranges


def _validated_cues(
    timestamps: Mapping[str, Any],
    *,
    slug: str,
    audio_sha256: str,
    manuscript_sha256: str,
    duration_seconds: float,
) -> list[dict[str, Any]]:
    if timestamps.get("slug") != slug:
        raise PackageBuildError("Timestamp sidecar slug does not match")
    if timestamps.get("audio_hash") != audio_sha256:
        raise PackageBuildError("Timestamp sidecar audio hash does not match")
    if timestamps.get("source_text_hash") != manuscript_sha256:
        raise PackageBuildError("Timestamp sidecar manuscript hash does not match")
    if timestamps.get("auto_estimated_sync") is not False:
        raise PackageBuildError("Estimated sync is forbidden for a release candidate")
    granularity = str(timestamps.get("sync_granularity") or "").lower()
    if granularity not in MEASURED_SYNC_GRANULARITIES:
        raise PackageBuildError("Timestamp sync is not paragraph/stanza measured")
    measurement = " ".join(
        str(timestamps.get(field) or "").lower()
        for field in ("alignment_method", "sync_method")
    )
    raw_cues = timestamps.get("cues")
    if not isinstance(raw_cues, list) or not raw_cues:
        raise PackageBuildError("Timestamp sidecar has no cues")
    cue_origins_are_measured = all(
        isinstance(raw, Mapping)
        and "measured" in str(raw.get("timing_origin") or "").lower()
        for raw in raw_cues
    )
    if "measured" not in measurement and not cue_origins_are_measured:
        raise PackageBuildError(
            "Timestamp sync lacks a measured document method or measured origin "
            "on every cue"
        )
    cues: list[dict[str, Any]] = []
    previous_end = 0.0
    for index, raw in enumerate(raw_cues):
        if not isinstance(raw, Mapping):
            raise PackageBuildError(f"Timestamp cue {index} is invalid")
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            raise PackageBuildError(f"Timestamp cue {index} boundary is invalid") from None
        text = str(raw.get("text") or "").strip()
        cue_granularity = str(raw.get("granularity") or granularity).lower()
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or (index > 0 and start < previous_end - 0.01)
            or not text
            or cue_granularity not in MEASURED_SYNC_GRANULARITIES
        ):
            raise PackageBuildError(f"Timestamp cue {index} is not release-safe")
        cues.append(
            {
                "id": str(raw.get("id") or f"cue-{index + 1:04d}"),
                "index": index,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "text": text,
                "granularity": cue_granularity,
            }
        )
        previous_end = end
    if abs(cues[0]["start"]) > 0.01:
        raise PackageBuildError("Measured cues do not start at the audio beginning")
    if abs(cues[-1]["end"] - duration_seconds) > AUDIO_DURATION_TOLERANCE_SECONDS:
        raise PackageBuildError("Measured cues do not cover the audio ending")
    return cues


def _validated_chapters(
    chapters_document: Mapping[str, Any],
    *,
    slug: str,
    duration_seconds: float,
    cues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if chapters_document.get("slug") != slug:
        raise PackageBuildError("Chapter sidecar slug does not match")
    raw_chapters = chapters_document.get("chapters")
    if not isinstance(raw_chapters, list) or not raw_chapters:
        raise PackageBuildError("Chapter sidecar has no chapters")
    chapters: list[dict[str, Any]] = []
    seen_chapter_ids: set[str] = set()
    previous_end = 0.0
    for index, raw in enumerate(raw_chapters):
        if not isinstance(raw, Mapping):
            raise PackageBuildError(f"Chapter {index} is invalid")
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            raise PackageBuildError(f"Chapter {index} boundary is invalid") from None
        chapter_id = str(raw.get("id") or f"chapter-{index + 1:03d}")
        if not PACKAGE_ID_RE.fullmatch(chapter_id):
            raise PackageBuildError(
                f"Chapter {index} id is not a canonical package identifier"
            )
        if chapter_id in seen_chapter_ids:
            raise PackageBuildError(f"Duplicate chapter id: {chapter_id}")
        seen_chapter_ids.add(chapter_id)
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or abs(start - previous_end) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS
        ):
            raise PackageBuildError(f"Chapter {index} boundary is not contiguous")
        chapters.append(
            {
                "id": chapter_id,
                "title": str(raw.get("title") or chapter_id),
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
        previous_end = end
    if abs(chapters[0]["start"]) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS or abs(
        chapters[-1]["end"] - duration_seconds
    ) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS:
        raise PackageBuildError("Chapters do not cover the complete audio")
    for cue in cues:
        containing = [
            chapter
            for chapter in chapters
            if cue["start"] + 0.01 >= chapter["start"]
            and cue["end"] <= chapter["end"] + 0.01
        ]
        if len(containing) != 1:
            raise PackageBuildError("A measured cue crosses or misses a chapter boundary")
        cue["chapter_id"] = containing[0]["id"]
    return chapters


def _validate_vtt_against_cues(path: Path, cues: list[dict[str, Any]]) -> None:
    ranges = _vtt_ranges(path)
    if len(ranges) != len(cues):
        raise PackageBuildError("VTT cue count does not match measured timestamps")
    for index, ((start, end), cue) in enumerate(zip(ranges, cues)):
        if abs(start - cue["start"]) > 0.01 or abs(end - cue["end"]) > 0.01:
            raise PackageBuildError(f"VTT cue {index} does not match measured timestamps")


def _validate_approved_legacy_inputs(
    *,
    repo_root: Path,
    slug: str,
    audio_path: Path,
    timestamps_path: Path,
    vtt_path: Path,
    chapters_path: Path,
    meta_path: Path,
) -> dict[str, Any]:
    inputs = {
        "mp3": audio_path.resolve(),
        "timestamps": timestamps_path.resolve(),
        "vtt": vtt_path.resolve(),
        "chapters": chapters_path.resolve(),
        "meta": meta_path.resolve(),
    }
    missing = [f"{name}:{path}" for name, path in inputs.items() if not path.is_file()]
    if missing:
        raise PackageBuildError(f"Approved legacy assets are missing: {missing}")
    if inputs["mp3"].suffix.lower() != ".mp3":
        raise PackageBuildError("Approved legacy source audio must be an MP3")

    context = _load_mirrored_publication(repo_root, slug)
    public_book = context["public_book"]
    reader_manifest = context["reader_manifest"]
    approval = context["approval_evidence"]
    source_evidence = context["source_evidence"]
    if any(
        document.get("slug") != slug
        for document in (public_book, reader_manifest, approval, source_evidence)
    ):
        raise PackageBuildError("Controlled publication slug identity conflicts")
    if (
        public_book.get("approved_to_publish") is not True
        or public_book.get("isPublic") is not True
        or public_book.get("isLive") is not True
        or public_book.get("audio_enabled") is not True
        or public_book.get("audiobook_enabled") is not True
        or reader_manifest.get("audio_enabled") is not True
        or reader_manifest.get("audiobook_enabled") is not True
        or approval.get("approved_to_publish") is not True
        or approval.get("audiobook_enabled") is not True
        or approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_APPROVED"
        or approval.get("qa_status") != "QA_PASSED"
        or approval.get("audio_qa_status") != "QA_PASSED"
    ):
        raise PackageBuildError("Controlled legacy audiobook is not currently approved")
    if (
        approval.get("rights_tier") != "A"
        or str(approval.get("verification_status") or "").lower() != "approved"
        or not str(source_evidence.get("rights_basis") or "").strip()
    ):
        raise PackageBuildError("Controlled rights are not tier A and approved")

    asr_score = _require_number(
        approval.get("asr_manuscript_score", approval.get("asr_source_score")),
        "ASR/manuscript score",
        9.7,
    )
    coverage = _require_number(
        approval.get("source_coverage"),
        "ASR/source coverage",
        0.98,
    )
    if (
        approval.get("first_words_match") is not True
        or approval.get("last_words_match") is not True
        or approval.get("no_missing_duplicated_reordered_content") is not True
    ):
        raise PackageBuildError(
            "First/last or ordered-content integrity evidence does not pass"
        )
    listening_score = _require_number(
        approval.get(
            "listening_qa_overall_score",
            approval.get("listening_qa_minimum_score"),
        ),
        "Listening score",
        9.2,
    )
    listening_confidence = _require_number(
        approval.get("listening_qa_minimum_confidence"),
        "Listening confidence",
        0.90,
    )
    fatal_flags = approval.get("listening_qa_fatal_flags")
    if fatal_flags != []:
        raise PackageBuildError("Listening QA has fatal flags or lacks an empty flag list")
    if (
        approval.get("auto_estimated_sync") is not False
        or str(approval.get("sync_tier") or "").upper()
        != "PARAGRAPH_OR_STANZA_SYNC_PREMIUM"
    ):
        raise PackageBuildError("Controlled sync is not measured paragraph/stanza sync")
    measured_sync_score = _require_number(
        approval.get("measured_paragraph_sync_score"),
        "Measured paragraph/stanza sync score",
        0.000001,
    )
    if not str(approval.get("upload_status") or "").startswith(
        "UPLOADED_CHECKSUM_VERIFIED"
    ):
        raise PackageBuildError("Legacy upload is not checksum verified")
    endpoint_http_status = _require_number(
        approval.get("endpoint_http_status"),
        "Endpoint HTTP status",
        0,
    )
    if endpoint_http_status != 206:
        raise PackageBuildError("Legacy audiobook endpoint does not have HTTP 206 proof")
    if approval.get("browser_gate_status") != "PASS":
        raise PackageBuildError("Legacy audiobook browser gate does not pass")
    blockers = approval.get("release_blockers")
    if blockers != []:
        raise PackageBuildError("Controlled approval has release blockers")

    expected_hashes = approval.get("uploaded_artifact_sha256")
    if not isinstance(expected_hashes, Mapping):
        raise PackageBuildError("Controlled approval lacks uploaded artifact hashes")
    audiobook = public_book.get("audiobook")
    public_assets = public_book.get("audiobook_assets")
    if not isinstance(audiobook, Mapping) or not isinstance(public_assets, Mapping):
        raise PackageBuildError("Controlled legacy audiobook asset identity is incomplete")
    nested_assets = audiobook.get("assets")
    if not isinstance(nested_assets, Mapping):
        raise PackageBuildError("Controlled legacy audiobook sidecars are incomplete")
    nested_hashes = audiobook.get("asset_sha256")
    if nested_hashes is not None and not isinstance(nested_hashes, Mapping):
        raise PackageBuildError("Controlled audiobook asset hashes are invalid")

    asset_facts: dict[str, dict[str, Any]] = {}
    controlled_sizes = approval.get("uploaded_artifact_size_bytes")
    if controlled_sizes is not None and not isinstance(controlled_sizes, Mapping):
        raise PackageBuildError("Controlled uploaded artifact sizes are invalid")
    for name in APPROVED_LEGACY_ASSETS:
        expected_hash = _require_sha256(
            expected_hashes.get(name),
            f"Controlled {name} hash",
        )
        actual_hash = sha256_file(inputs[name])
        actual_size = inputs[name].stat().st_size
        if actual_hash != expected_hash:
            raise PackageBuildError(f"Local {name} does not match controlled hash")
        if isinstance(controlled_sizes, Mapping):
            controlled_size = _require_number(
                controlled_sizes.get(name),
                f"Controlled {name} size",
                1,
            )
            if (
                not controlled_size.is_integer()
                or int(controlled_size) != actual_size
            ):
                raise PackageBuildError(
                    f"Local {name} does not match controlled size"
                )
        if isinstance(nested_hashes, Mapping) and nested_hashes.get(name) != expected_hash:
            raise PackageBuildError(f"Controlled {name} hash identities conflict")
        asset_url = str(public_assets.get(name) or "")
        if (
            not asset_url.startswith("https://")
            or nested_assets.get(name) != asset_url
            or f"_{expected_hash[:12]}" not in asset_url
        ):
            raise PackageBuildError(f"Controlled {name} URL identity conflicts")
        asset_facts[name] = {
            "sha256": actual_hash,
            "size_bytes": actual_size,
        }
    if audiobook.get("url") != public_assets.get("mp3"):
        raise PackageBuildError("Controlled MP3 URL identities conflict")
    if _require_sha256(approval.get("audio_sha256"), "Approved audio hash") != (
        asset_facts["mp3"]["sha256"]
    ):
        raise PackageBuildError("Approved audio hash conflicts with uploaded MP3")
    if audiobook.get("audio_sha256") not in (
        None,
        "",
        asset_facts["mp3"]["sha256"],
    ):
        raise PackageBuildError("Controlled audiobook audio hash conflicts")
    controlled_mp3_size = _require_number(
        audiobook.get("size"),
        "Controlled MP3 size",
        1,
    )
    if (
        not controlled_mp3_size.is_integer()
        or int(controlled_mp3_size) != asset_facts["mp3"]["size_bytes"]
    ):
        raise PackageBuildError("Controlled MP3 size does not match local bytes")

    controlled_source_sha256 = _require_sha256(
        source_evidence.get("source_hash"),
        "Controlled source hash",
    )
    if public_book.get("source_hash") != controlled_source_sha256:
        raise PackageBuildError("Controlled source hashes conflict")
    manuscript_sha256 = _require_sha256(
        approval.get("source_sha256"),
        "Approved narrated manuscript hash",
    )
    if audiobook.get("source_sha256") not in (None, "", manuscript_sha256):
        raise PackageBuildError("Controlled audiobook manuscript hash conflicts")

    duration_ms = ffprobe_duration_ms(inputs["mp3"])
    controlled_duration_ms = _require_number(
        audiobook.get("duration_ms"),
        "Controlled audio duration",
        1,
    )
    if (
        not controlled_duration_ms.is_integer()
        or int(controlled_duration_ms) != duration_ms
    ):
        raise PackageBuildError("Controlled audio duration does not match local bytes")
    duration_seconds = duration_ms / 1000
    timestamps = read_json(inputs["timestamps"])
    chapters_document = read_json(inputs["chapters"])
    meta = read_json(inputs["meta"])
    if not isinstance(timestamps, Mapping) or not isinstance(
        chapters_document,
        Mapping,
    ) or not isinstance(meta, Mapping):
        raise PackageBuildError("Legacy JSON sidecars must be objects")
    cues = _validated_cues(
        timestamps,
        slug=slug,
        audio_sha256=asset_facts["mp3"]["sha256"],
        manuscript_sha256=manuscript_sha256,
        duration_seconds=duration_seconds,
    )
    chapters = _validated_chapters(
        chapters_document,
        slug=slug,
        duration_seconds=duration_seconds,
        cues=cues,
    )
    _validate_vtt_against_cues(inputs["vtt"], cues)
    meta_duration_seconds = _require_number(
        meta.get("duration_seconds"),
        "Legacy metadata duration",
        0.000001,
    )
    if (
        meta.get("slug") != slug
        or meta.get("audio_hash") != asset_facts["mp3"]["sha256"]
        or meta.get("source_text_hash") != manuscript_sha256
        or meta.get("auto_estimated_sync") is not False
        or str(meta.get("sync_granularity") or "").lower()
        not in MEASURED_SYNC_GRANULARITIES
        or abs(meta_duration_seconds - duration_seconds)
        > AUDIO_DURATION_TOLERANCE_SECONDS
    ):
        raise PackageBuildError("Legacy metadata sidecar does not match release truth")
    meta_asr_score = meta.get("asr_transcript_match_score")
    if meta_asr_score is not None:
        _require_number(
            meta_asr_score,
            "Legacy metadata ASR score",
            9.7,
        )
    meta_asr_status = str(meta.get("asr_release_status") or "").upper()
    if any(flag in meta_asr_status for flag in ("WEAK", "FAIL", "BLOCK")):
        raise PackageBuildError("Legacy metadata carries a non-release ASR status")

    return {
        "context": context,
        "inputs": inputs,
        "asset_facts": asset_facts,
        "public_book": public_book,
        "approval": approval,
        "source_evidence": source_evidence,
        "timestamps": timestamps,
        "meta": meta,
        "cues": cues,
        "chapters": chapters,
        "controlled_source_sha256": controlled_source_sha256,
        "manuscript_sha256": manuscript_sha256,
        "duration_ms": duration_ms,
        "gate_summary": {
            "asr_score": asr_score,
            "coverage": coverage,
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_integrity": True,
            "listening_score": listening_score,
            "listening_confidence": listening_confidence,
            "fatal_flags": [],
            "measured_sync_score": measured_sync_score,
            "rights_tier": "A",
            "verification_status": "approved",
            "upload_status": approval["upload_status"],
            "endpoint_http_status": 206,
            "browser_gate_status": "PASS",
            "release_blockers": [],
        },
    }


def _segment_cue_groups(
    chapters: list[dict[str, Any]],
    cues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select measured cue boundaries near ten minutes without exceeding twelve."""

    groups: list[dict[str, Any]] = []
    for chapter in chapters:
        remaining = [
            cue for cue in cues if cue.get("chapter_id") == chapter["id"]
        ]
        if not remaining:
            raise PackageBuildError(f"Chapter {chapter['id']} has no measured cues")
        chapter_segment_index = 0
        segment_start = float(chapter["start"])
        while remaining:
            boundary_end_by_index = {
                index: (
                    float(chapter["end"])
                    if index == len(remaining) - 1
                    else float(remaining[index + 1]["start"])
                )
                for index in range(len(remaining))
            }
            allowed = [
                index
                for index, boundary_end in boundary_end_by_index.items()
                if boundary_end - segment_start <= MAX_SEGMENT_SECONDS + 0.001
            ]
            if not allowed:
                raise PackageBuildError(
                    "A single measured cue exceeds the 12-minute segment maximum"
                )
            choices: list[tuple[float, int]] = []
            for index in allowed:
                end = boundary_end_by_index[index]
                tail = float(chapter["end"]) - end
                if tail and tail < MIN_TARGET_SEGMENT_SECONDS:
                    continue
                choices.append(
                    (
                        abs(
                            (end - segment_start)
                            - TARGET_SEGMENT_SECONDS
                        ),
                        index,
                    )
                )
            if not choices:
                choices = [
                    (
                        abs(
                            (
                                boundary_end_by_index[index]
                                - segment_start
                            )
                            - TARGET_SEGMENT_SECONDS
                        ),
                        index,
                    )
                    for index in allowed
                ]
            selected_index = min(choices)[1]
            selected = remaining[: selected_index + 1]
            chapter_segment_index += 1
            groups.append(
                {
                    "chapter": chapter,
                    "chapter_segment_index": chapter_segment_index,
                    "start": segment_start,
                    "end": boundary_end_by_index[selected_index],
                    "cues": selected,
                }
            )
            segment_start = boundary_end_by_index[selected_index]
            remaining = remaining[selected_index + 1 :]
    return groups


def _validate_segment_source_coverage(
    groups: list[dict[str, Any]],
    *,
    duration_seconds: float,
) -> None:
    """Require segment source ranges to cover the source exactly once."""

    if not groups:
        raise PackageBuildError("No source segments were created")
    try:
        starts = [float(group["start"]) for group in groups]
        ends = [float(group["end"]) for group in groups]
    except (KeyError, TypeError, ValueError):
        raise PackageBuildError("Segment source boundaries are invalid") from None
    if abs(starts[0]) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS:
        raise PackageBuildError("Segment source coverage does not start at zero")
    for left_end, right_start in zip(ends, starts[1:]):
        if abs(left_end - right_start) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS:
            raise PackageBuildError("Segment source coverage has a gap or overlap")
    if abs(ends[-1] - duration_seconds) > CHAPTER_BOUNDARY_TOLERANCE_SECONDS:
        raise PackageBuildError("Segment source coverage does not reach the audio end")
    covered_seconds = sum(end - start for start, end in zip(starts, ends))
    if (
        not all(
            math.isfinite(start)
            and math.isfinite(end)
            and start >= 0
            and end > start
            for start, end in zip(starts, ends)
        )
        or abs(covered_seconds - duration_seconds)
        > CHAPTER_BOUNDARY_TOLERANCE_SECONDS
    ):
        raise PackageBuildError("Segment source coverage is not exact")


def _validate_final_encoded_duration(
    *,
    source_duration_ms: int,
    encoded_duration_ms: int,
) -> None:
    """Allow codec padding while rejecting cumulative encoded-duration drift."""

    if source_duration_ms <= 0 or encoded_duration_ms <= 0:
        raise PackageBuildError("Source and encoded durations must be positive")
    if abs(encoded_duration_ms - source_duration_ms) > round(
        AUDIO_DURATION_TOLERANCE_SECONDS * 1000
    ):
        raise PackageBuildError("Encoded package duration drifted from source audio")


def _copy_exact(source: Path, destination: Path, expected_sha256: str) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256_file(destination) != expected_sha256:
        raise PackageBuildError(f"Copied provenance changed: {source.name}")
    return destination


def build_approved_legacy(
    *,
    repo_root: Path,
    slug: str,
    audio_path: Path,
    timestamps_path: Path,
    vtt_path: Path,
    chapters_path: Path,
    meta_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    validated = _validate_approved_legacy_inputs(
        repo_root=repo_root.resolve(),
        slug=slug,
        audio_path=audio_path,
        timestamps_path=timestamps_path,
        vtt_path=vtt_path,
        chapters_path=chapters_path,
        meta_path=meta_path,
    )
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PackageBuildError(f"Output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = validated["inputs"]
    asset_facts = validated["asset_facts"]
    public_book = validated["public_book"]
    approval = validated["approval"]
    source_evidence = validated["source_evidence"]
    audiobook = public_book["audiobook"]
    title = str(public_book.get("title") or "").strip()
    author = str(public_book.get("author") or "").strip()
    provider = str(
        audiobook.get("provider") or public_book.get("audiobook_provider") or ""
    ).strip()
    voice = str(
        audiobook.get("voice") or public_book.get("audiobook_voice") or ""
    ).strip()
    model = str(
        audiobook.get("model") or public_book.get("audiobook_model") or ""
    ).strip()
    if not title or not author or not provider or not voice or not model:
        raise PackageBuildError(
            "Controlled title, author, provider, voice, and model are required"
        )

    masters_dir = output_dir / "masters"
    provenance_legacy_dir = output_dir / "provenance/legacy"
    provenance_controlled_dir = output_dir / "provenance/controlled"
    original_copy = _copy_exact(
        inputs["mp3"],
        masters_dir
        / f"original-approved-source-{asset_facts['mp3']['sha256']}.mp3",
        asset_facts["mp3"]["sha256"],
    )
    legacy_copies = {
        name: _copy_exact(
            inputs[name],
            provenance_legacy_dir / inputs[name].name,
            asset_facts[name]["sha256"],
        )
        for name in ("timestamps", "vtt", "chapters", "meta")
    }
    controlled_sources = {
        "approval": validated["context"]["dirs"][0] / "approval_evidence.json",
        "source": validated["context"]["dirs"][0] / "source_evidence.json",
        "checksums": validated["context"]["dirs"][0] / "checksum_manifest.json",
    }
    controlled_copies = {
        name: _copy_exact(
            path,
            provenance_controlled_dir / path.name,
            sha256_file(path),
        )
        for name, path in controlled_sources.items()
    }

    pcm_master = masters_dir / "approved-pcm-master.wav"
    run_checked(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(original_copy),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(pcm_master),
        ]
    )
    if not pcm_master.is_file() or pcm_master.stat().st_size <= 0:
        raise PackageBuildError("PCM master was not created")

    segment_groups = _segment_cue_groups(
        validated["chapters"],
        validated["cues"],
    )
    _validate_segment_source_coverage(
        segment_groups,
        duration_seconds=validated["duration_ms"] / 1000,
    )
    word_cursor = 0
    paragraph_cursor = 0
    cumulative_ms = 0
    segment_assets: list[dict[str, Any]] = []
    track_rows: list[dict[str, Any]] = []
    global_segment_index = 0
    for chapter_order, chapter in enumerate(validated["chapters"]):
        chapter_groups = [
            group for group in segment_groups if group["chapter"]["id"] == chapter["id"]
        ]
        track_start_word = word_cursor
        track_start_paragraph = paragraph_cursor
        chunks: list[dict[str, Any]] = []
        for group in chapter_groups:
            global_segment_index += 1
            segment_id = f"c{chapter_order + 1:03d}-s{group['chapter_segment_index']:03d}"
            segment_basename = f"segment-{group['chapter_segment_index']:03d}"
            delivery_dir = output_dir / "delivery" / chapter["id"]
            sidecars_dir = output_dir / "sidecars" / chapter["id"]
            delivery_dir.mkdir(parents=True, exist_ok=True)
            sidecars_dir.mkdir(parents=True, exist_ok=True)
            audio_output = delivery_dir / f"{segment_basename}.mp3"
            run_checked(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(original_copy),
                    "-map",
                    "0:a:0",
                    "-map_metadata",
                    "-1",
                    "-af",
                    (
                        f"atrim=start={group['start']:.3f}:end={group['end']:.3f},"
                        "asetpts=PTS-STARTPTS"
                    ),
                    "-ac",
                    "1",
                    "-ar",
                    "48000",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "96k",
                    str(audio_output),
                ]
            )
            duration_ms = ffprobe_duration_ms(audio_output)
            expected_duration_ms = round((group["end"] - group["start"]) * 1000)
            if abs(duration_ms - expected_duration_ms) > round(
                AUDIO_DURATION_TOLERANCE_SECONDS * 1000
            ):
                raise PackageBuildError(
                    f"Encoded segment duration drifted at {segment_id}"
                )
            _validate_delivery_audio_profile(audio_output)

            local_cues = rebased_cues(
                group["cues"],
                segment_start_seconds=group["start"],
            )
            timestamps_output = sidecars_dir / f"{segment_basename}-timestamps.json"
            vtt_output = sidecars_dir / f"{segment_basename}.vtt"
            metadata_output = sidecars_dir / f"{segment_basename}-metadata.json"
            write_json(
                timestamps_output,
                {
                    "schema_version": "audiobook_segment_timestamps.v1",
                    "slug": slug,
                    "chapter_id": chapter["id"],
                    "segment_id": segment_id,
                    "sync_granularity": "paragraph_or_stanza",
                    "sync_method": "measured_legacy_cue_boundaries",
                    "auto_estimated_sync": False,
                    "source_audio_sha256": asset_facts["mp3"]["sha256"],
                    "source_text_sha256": validated["manuscript_sha256"],
                    "cues": local_cues,
                },
            )
            write_vtt(vtt_output, local_cues)

            word_count = sum(cue_word_count(cue) for cue in group["cues"])
            paragraph_count = sum(
                len(cue_paragraphs(cue)) for cue in group["cues"]
            )
            if word_count <= 0 or paragraph_count <= 0:
                raise PackageBuildError(f"Segment {segment_id} has no narrated text")
            end_word = word_cursor + word_count - 1
            end_paragraph = paragraph_cursor + paragraph_count - 1
            write_json(
                metadata_output,
                {
                    "schema_version": "audiobook_segment_metadata.v1",
                    "slug": slug,
                    "chapter_id": chapter["id"],
                    "segment_id": segment_id,
                    "order": len(chunks),
                    "boundary_index_space": "exact_narration_text",
                    "reader_alignment_mode": "paragraph_or_stanza",
                    "highlight_sync_enabled": False,
                    "start_word": word_cursor,
                    "end_word": end_word,
                    "start_paragraph": paragraph_cursor,
                    "end_paragraph": end_paragraph,
                    "cumulative_start_ms": cumulative_ms,
                    "duration_ms": duration_ms,
                    "source_audio_sha256": asset_facts["mp3"]["sha256"],
                    "delivery_profile": "mp3-96k-mono-48khz",
                    "narration_regenerated": False,
                    "measured_source_start_seconds": round(group["start"], 3),
                    "measured_source_end_seconds": round(group["end"], 3),
                },
            )

            asset_ids = {
                "audio": f"{segment_id}.audio",
                "timestamps": f"{segment_id}.timestamps",
                "vtt": f"{segment_id}.vtt",
                "metadata": f"{segment_id}.metadata",
            }
            segment_assets.append(
                {
                    "segment_id": segment_id,
                    "chapter_id": chapter["id"],
                    "basename": segment_basename,
                    "audio": audio_output,
                    "timestamps": timestamps_output,
                    "vtt": vtt_output,
                    "metadata": metadata_output,
                    "asset_ids": asset_ids,
                }
            )
            chunks.append(
                {
                    "segment_id": segment_id,
                    "order": len(chunks),
                    "start_word": word_cursor,
                    "end_word": end_word,
                    "start_paragraph": paragraph_cursor,
                    "end_paragraph": end_paragraph,
                    "cumulative_start_ms": cumulative_ms,
                    "duration_ms": duration_ms,
                    "asset_ids": asset_ids,
                }
            )
            word_cursor = end_word + 1
            paragraph_cursor = end_paragraph + 1
            cumulative_ms += duration_ms
        track_rows.append(
            {
                "id": chapter["id"],
                "chapter_id": chapter["id"],
                "order": chapter_order,
                "title": chapter["title"],
                "start_word": track_start_word,
                "end_word": word_cursor - 1,
                "start_paragraph": track_start_paragraph,
                "end_paragraph": paragraph_cursor - 1,
                "chunks": chunks,
            }
        )

    _validate_final_encoded_duration(
        source_duration_ms=validated["duration_ms"],
        encoded_duration_ms=cumulative_ms,
    )

    evidence_paths = {
        "approval_evidence.json": controlled_copies["approval"],
        "source_evidence.json": controlled_copies["source"],
        "checksum_manifest.json": controlled_copies["checksums"],
        "legacy.timestamps.json": legacy_copies["timestamps"],
        "legacy.vtt": legacy_copies["vtt"],
        "legacy.chapters.json": legacy_copies["chapters"],
        "legacy.meta.json": legacy_copies["meta"],
    }
    evidence_sha256 = {
        name: sha256_file(path) for name, path in evidence_paths.items()
    }
    release_candidate_evidence = {
        "status": "PASS",
        "all_release_gates_passed": True,
        "gate_policy": "approved_legacy_package_candidate.v1",
        "gates": validated["gate_summary"],
        "approved_asset_sha256": {
            name: facts["sha256"] for name, facts in asset_facts.items()
        },
        "approved_asset_size_bytes": {
            name: facts["size_bytes"] for name, facts in asset_facts.items()
        },
        "controlled_approval_sha256": evidence_sha256["approval_evidence.json"],
        "controlled_source_evidence_sha256": evidence_sha256["source_evidence.json"],
        "controlled_checksum_manifest_sha256": evidence_sha256[
            "checksum_manifest.json"
        ],
    }
    release_descriptor = {
        "schema_version": "audiobook_release_descriptor.v1",
        "slug": slug,
        "title": title,
        "author": author,
        "controlled_source_sha256": validated["controlled_source_sha256"],
        "manuscript_sha256": validated["manuscript_sha256"],
        "narration_text_sha256": validated["manuscript_sha256"],
        "approved_source_audio_sha256": asset_facts["mp3"]["sha256"],
        "provider": provider,
        "voice": voice,
        "model": model,
        "delivery_profile": "mp3-96k-mono-48khz",
        "narration_regenerated": False,
        "segment_boundaries_seconds": [
            round(segment_groups[0]["start"], 3),
            *[round(group["end"], 3) for group in segment_groups],
        ],
        "segment_target_seconds": {
            "minimum": MIN_TARGET_SEGMENT_SECONDS,
            "preferred": TARGET_SEGMENT_SECONDS,
            "maximum": MAX_SEGMENT_SECONDS,
        },
        "sync_tier": "paragraph_or_stanza",
        "highlight_sync_enabled": False,
        "evidence_sha256": evidence_sha256,
        "release_candidate_status": "RELEASE_CANDIDATE",
        "release_candidate_evidence": release_candidate_evidence,
        "known_release_blockers": [],
    }
    release_descriptor_sha256 = canonical_sha256(release_descriptor)
    descriptor_path = output_dir / "release-descriptor.json"
    write_json(descriptor_path, release_descriptor)
    if canonical_sha256(read_json(descriptor_path)) != release_descriptor_sha256:
        raise PackageBuildError("Release descriptor changed while writing")
    prefix = immutable_release_prefix(slug, release_descriptor_sha256)

    plan_assets = [
        file_asset(
            asset_id="master.original",
            path=original_copy,
            key=(
                f"{prefix}masters/original-approved-source-sha256-"
                f"{sha256_file(original_copy)}.mp3"
            ),
            mime_type="audio/mpeg",
        ),
        file_asset(
            asset_id="master.pcm",
            path=pcm_master,
            key=f"{prefix}masters/approved-pcm-master-sha256-{sha256_file(pcm_master)}.wav",
            mime_type="audio/wav",
        ),
        file_asset(
            asset_id="release.descriptor",
            path=descriptor_path,
            key=f"{prefix}release-descriptor.json",
            mime_type="application/json",
        ),
    ]
    provenance_mime = {
        "timestamps": "application/json",
        "vtt": "text/vtt",
        "chapters": "application/json",
        "meta": "application/json",
    }
    for name, path in legacy_copies.items():
        plan_assets.append(
            file_asset(
                asset_id=f"provenance.legacy.{name}",
                path=path,
                key=f"{prefix}provenance/legacy/{path.name}",
                mime_type=provenance_mime[name],
            )
        )
    for name, path in controlled_copies.items():
        plan_assets.append(
            file_asset(
                asset_id=f"provenance.controlled.{name}",
                path=path,
                key=f"{prefix}provenance/controlled/{path.name}",
                mime_type="application/json",
            )
        )
    for segment in segment_assets:
        key_base = f"{prefix}delivery/{segment['chapter_id']}/{segment['basename']}"
        sidecar_base = f"{prefix}sidecars/{segment['chapter_id']}/{segment['basename']}"
        plan_assets.extend(
            [
                file_asset(
                    asset_id=segment["asset_ids"]["audio"],
                    path=segment["audio"],
                    key=f"{key_base}-sha256-{sha256_file(segment['audio'])}.mp3",
                    mime_type="audio/mpeg",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["timestamps"],
                    path=segment["timestamps"],
                    key=(
                        f"{sidecar_base}-timestamps-sha256-"
                        f"{sha256_file(segment['timestamps'])}.json"
                    ),
                    mime_type="application/json",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["vtt"],
                    path=segment["vtt"],
                    key=f"{sidecar_base}-sha256-{sha256_file(segment['vtt'])}.vtt",
                    mime_type="text/vtt",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["metadata"],
                    path=segment["metadata"],
                    key=(
                        f"{sidecar_base}-metadata-sha256-"
                        f"{sha256_file(segment['metadata'])}.json"
                    ),
                    mime_type="application/json",
                ),
            ]
        )

    upload_plan = {
        "schema_version": "audiobook_package_upload_plan.v2",
        "slug": slug,
        "release_descriptor_sha256": release_descriptor_sha256,
        "immutable_prefix": prefix,
        "release_status": "RELEASE_CANDIDATE",
        "assets": plan_assets,
    }
    upload_plan_path = output_dir / "upload-plan.json"
    write_json(upload_plan_path, upload_plan)
    semantics = {
        "schema_version": "audiobook_package_semantics.v2",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "slug": slug,
        "release_evidence_version": (
            f"approved-legacy-{evidence_sha256['approval_evidence.json'][:12]}"
        ),
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_sha256": validated["controlled_source_sha256"],
        "manuscript_sha256": validated["manuscript_sha256"],
        "duration_ms": cumulative_ms,
        "segment_count": len(segment_assets),
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "sync_tier": "paragraph_or_stanza",
        "highlight_sync_enabled": False,
        "tracks": track_rows,
    }
    semantics_path = output_dir / "package-semantics.json"
    write_json(semantics_path, semantics)
    result = {
        "status": "RELEASE_CANDIDATE_PACKAGE_BUILT",
        "slug": slug,
        "output_dir": str(output_dir),
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_audio_sha256": asset_facts["mp3"]["sha256"],
        "source_sha256": validated["controlled_source_sha256"],
        "manuscript_sha256": validated["manuscript_sha256"],
        "duration_ms": cumulative_ms,
        "segment_count": len(segment_assets),
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "asset_count": len(plan_assets),
        "upload_plan": str(upload_plan_path),
        "package_semantics": str(semantics_path),
        "release_status": "RELEASE_CANDIDATE",
        "release_blockers": [],
    }
    write_json(output_dir / "build-result.json", result)
    return result


def _validate_canary_inputs(run_dir: Path) -> dict[str, Any]:
    required = {
        "audio": run_dir / CANARY_AUDIO_NAME,
        "timestamps": run_dir / "timestamps.json",
        "clean_manuscript": run_dir / "clean_manuscript.txt",
        "goliveevidence": run_dir / "goliveevidence.json",
        "listening_quality": run_dir / "listening_quality_report.json",
        "rights": run_dir / "rights_metadata_report.json",
        "tts_manifest": run_dir / "tts_chunk_manifest.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise PackageBuildError(f"Required canary inputs are missing: {missing}")
    audio_sha256 = sha256_file(required["audio"])
    if audio_sha256 != CANARY_EXPECTED_AUDIO_SHA256:
        raise PackageBuildError(
            "Approved canary MP3 does not match the production-bound SHA-256"
        )
    timestamps = read_json(required["timestamps"])
    cues = timestamps.get("cues") if isinstance(timestamps, dict) else None
    if not isinstance(cues, list) or len(cues) != 3:
        raise PackageBuildError("Canary requires the three measured paragraph cues")
    if bool(timestamps.get("auto_estimated_sync")):
        raise PackageBuildError("Estimated sync is forbidden for a release package")
    if str(timestamps.get("sync_granularity")) != "paragraph_or_stanza":
        raise PackageBuildError("Canary sync must remain paragraph_or_stanza")
    if abs(float(cues[0].get("end") or 0) - CANARY_SPLIT_SECONDS) > 0.001:
        raise PackageBuildError("Canary split no longer matches the measured cue boundary")
    return {**required, "timestamps_doc": timestamps, "cues": cues}


def build_canary(*, run_dir: Path, output_dir: Path) -> dict[str, Any]:
    inputs = _validate_canary_inputs(run_dir)
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PackageBuildError(f"Output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    originals_dir = output_dir / "masters"
    delivery_dir = output_dir / "delivery/chapter-001"
    sidecars_dir = output_dir / "sidecars/chapter-001"
    originals_dir.mkdir(parents=True, exist_ok=True)
    delivery_dir.mkdir(parents=True, exist_ok=True)
    sidecars_dir.mkdir(parents=True, exist_ok=True)

    original_copy = originals_dir / f"original-approved-source-{CANARY_EXPECTED_AUDIO_SHA256}.mp3"
    shutil.copy2(inputs["audio"], original_copy)
    if sha256_file(original_copy) != CANARY_EXPECTED_AUDIO_SHA256:
        raise PackageBuildError("Retained original MP3 changed during local copy")

    pcm_master = originals_dir / "approved-pcm-master.wav"
    run_checked(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(original_copy),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(pcm_master),
        ]
    )

    segment_paths = [
        delivery_dir / "segment-001.mp3",
        delivery_dir / "segment-002.mp3",
    ]
    filters = [
        f"atrim=start=0:end={CANARY_SPLIT_SECONDS:.3f},asetpts=PTS-STARTPTS",
        f"atrim=start={CANARY_SPLIT_SECONDS:.3f},asetpts=PTS-STARTPTS",
    ]
    for segment_path, audio_filter in zip(segment_paths, filters):
        run_checked(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(original_copy),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                "-af",
                audio_filter,
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "96k",
                str(segment_path),
            ]
        )

    segment_durations = [ffprobe_duration_ms(path) for path in segment_paths]
    if segment_durations != [138_720, 188_349]:
        raise PackageBuildError(
            f"Canary delivery durations changed unexpectedly: {segment_durations}"
        )

    segment_cues = [
        rebased_cues(inputs["cues"][:1], segment_start_seconds=0),
        rebased_cues(
            inputs["cues"][1:],
            segment_start_seconds=CANARY_SPLIT_SECONDS,
        ),
    ]
    segment_word_counts = [
        sum(cue_word_count(cue) for cue in inputs["cues"][:1]),
        sum(cue_word_count(cue) for cue in inputs["cues"][1:]),
    ]
    segment_paragraph_counts = [
        sum(len(cue_paragraphs(cue)) for cue in inputs["cues"][:1]),
        sum(len(cue_paragraphs(cue)) for cue in inputs["cues"][1:]),
    ]

    sidecar_paths: list[dict[str, Path]] = []
    word_cursor = 0
    paragraph_cursor = 0
    cumulative_ms = 0
    segment_semantics: list[dict[str, Any]] = []
    for index in range(2):
        segment_number = index + 1
        segment_id = f"c001-s{segment_number:03d}"
        timestamps_path = sidecars_dir / f"segment-{segment_number:03d}-timestamps.json"
        vtt_path = sidecars_dir / f"segment-{segment_number:03d}.vtt"
        metadata_path = sidecars_dir / f"segment-{segment_number:03d}-metadata.json"
        timestamps_doc = {
            "schema_version": "audiobook_segment_timestamps.v1",
            "slug": CANARY_SLUG,
            "segment_id": segment_id,
            "sync_granularity": "paragraph_or_stanza",
            "auto_estimated_sync": False,
            "cues": segment_cues[index],
        }
        write_json(timestamps_path, timestamps_doc)
        write_vtt(vtt_path, segment_cues[index])

        end_word = word_cursor + segment_word_counts[index] - 1
        end_paragraph = paragraph_cursor + segment_paragraph_counts[index] - 1
        metadata_doc = {
            "schema_version": "audiobook_segment_metadata.v1",
            "slug": CANARY_SLUG,
            "chapter_id": "chapter-001",
            "segment_id": segment_id,
            "order": index,
            "boundary_index_space": "exact_narration_text",
            "reader_alignment_mode": "paragraph_or_stanza",
            "highlight_sync_enabled": False,
            "start_word": word_cursor,
            "end_word": end_word,
            "start_paragraph": paragraph_cursor,
            "end_paragraph": end_paragraph,
            "cumulative_start_ms": cumulative_ms,
            "duration_ms": segment_durations[index],
            "source_audio_sha256": CANARY_EXPECTED_AUDIO_SHA256,
            "delivery_profile": "mp3-96k-mono-48khz",
            "narration_regenerated": False,
        }
        write_json(metadata_path, metadata_doc)
        sidecar_paths.append(
            {
                "timestamps": timestamps_path,
                "vtt": vtt_path,
                "metadata": metadata_path,
            }
        )
        segment_semantics.append(
            {
                "segment_id": segment_id,
                "order": index,
                "start_word": word_cursor,
                "end_word": end_word,
                "start_paragraph": paragraph_cursor,
                "end_paragraph": end_paragraph,
                "cumulative_start_ms": cumulative_ms,
                "duration_ms": segment_durations[index],
                "asset_ids": {
                    "audio": f"{segment_id}.audio",
                    "timestamps": f"{segment_id}.timestamps",
                    "vtt": f"{segment_id}.vtt",
                    "metadata": f"{segment_id}.metadata",
                },
            }
        )
        word_cursor = end_word + 1
        paragraph_cursor = end_paragraph + 1
        cumulative_ms += segment_durations[index]

    controlled_chapter = read_json(
        ROOT
        / "backend/data/controlled_publications"
        / CANARY_SLUG
        / "chapters/chapter-001.json"
    )
    controlled_source_sha256 = str(
        controlled_chapter.get("sourceSha256")
        or controlled_chapter.get("content_hash")
        or ""
    )
    if len(controlled_source_sha256) != 64:
        raise PackageBuildError("Controlled chapter source SHA-256 is unavailable")
    manuscript_sha256 = sha256_file(inputs["clean_manuscript"])
    narration_text_sha256 = str(inputs["timestamps_doc"].get("source_text_hash") or "")
    if len(narration_text_sha256) != 64:
        raise PackageBuildError("Measured narration-text SHA-256 is unavailable")

    evidence_files = [
        inputs["goliveevidence"],
        inputs["listening_quality"],
        inputs["rights"],
        inputs["timestamps"],
        inputs["tts_manifest"],
    ]
    evidence_hashes = {
        path.name: sha256_file(path)
        for path in evidence_files
    }
    release_descriptor = {
        "schema_version": "audiobook_release_descriptor.v1",
        "slug": CANARY_SLUG,
        "title": CANARY_TITLE,
        "author": CANARY_AUTHOR,
        "controlled_source_sha256": controlled_source_sha256,
        "manuscript_sha256": manuscript_sha256,
        "narration_text_sha256": narration_text_sha256,
        "approved_source_audio_sha256": CANARY_EXPECTED_AUDIO_SHA256,
        "provider": "sarvam",
        "voice": "ratan",
        "delivery_profile": "mp3-96k-mono-48khz",
        "narration_regenerated": False,
        "segment_boundaries_seconds": [0.0, CANARY_SPLIT_SECONDS, 327.069],
        "sync_tier": "paragraph_or_stanza",
        "highlight_sync_enabled": False,
        "evidence_sha256": evidence_hashes,
        "known_release_blockers": [
            "CURRENT_AUDIO_DERIVED_ASR_POLICY_REVALIDATION_REQUIRED",
            "HASH_BOUND_PROVIDER_VOICE_RIGHTS_SNAPSHOT_REQUIRED",
            "DEDICATED_PRIMARY_AND_DR_STORAGE_REQUIRED",
            "OBJECT_LOCK_GOVERNANCE_EVIDENCE_REQUIRED",
        ],
    }
    release_descriptor_sha256 = canonical_sha256(release_descriptor)
    descriptor_path = output_dir / "release-descriptor.json"
    write_json(descriptor_path, release_descriptor)
    if canonical_sha256(read_json(descriptor_path)) != release_descriptor_sha256:
        raise PackageBuildError("Release descriptor changed while writing")

    prefix = immutable_release_prefix(CANARY_SLUG, release_descriptor_sha256)
    plan_assets: list[dict[str, Any]] = [
        file_asset(
            asset_id="master.original",
            path=original_copy,
            key=(
                f"{prefix}masters/original-approved-source-sha256-"
                f"{sha256_file(original_copy)}.mp3"
            ),
            mime_type="audio/mpeg",
        ),
        file_asset(
            asset_id="master.pcm",
            path=pcm_master,
            key=f"{prefix}masters/approved-pcm-master-sha256-{sha256_file(pcm_master)}.wav",
            mime_type="audio/wav",
        ),
        file_asset(
            asset_id="release.descriptor",
            path=descriptor_path,
            key=f"{prefix}release-descriptor.json",
            mime_type="application/json",
        ),
    ]
    for index, segment in enumerate(segment_semantics):
        audio_path = segment_paths[index]
        sidecars = sidecar_paths[index]
        segment_name = f"segment-{index + 1:03d}"
        plan_assets.extend(
            [
                file_asset(
                    asset_id=segment["asset_ids"]["audio"],
                    path=audio_path,
                    key=(
                        f"{prefix}delivery/chapter-001/{segment_name}-sha256-"
                        f"{sha256_file(audio_path)}.mp3"
                    ),
                    mime_type="audio/mpeg",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["timestamps"],
                    path=sidecars["timestamps"],
                    key=(
                        f"{prefix}sidecars/chapter-001/{segment_name}-timestamps-sha256-"
                        f"{sha256_file(sidecars['timestamps'])}.json"
                    ),
                    mime_type="application/json",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["vtt"],
                    path=sidecars["vtt"],
                    key=(
                        f"{prefix}sidecars/chapter-001/{segment_name}-sha256-"
                        f"{sha256_file(sidecars['vtt'])}.vtt"
                    ),
                    mime_type="text/vtt",
                ),
                file_asset(
                    asset_id=segment["asset_ids"]["metadata"],
                    path=sidecars["metadata"],
                    key=(
                        f"{prefix}sidecars/chapter-001/{segment_name}-metadata-sha256-"
                        f"{sha256_file(sidecars['metadata'])}.json"
                    ),
                    mime_type="application/json",
                ),
            ]
        )

    upload_plan = {
        "schema_version": "audiobook_package_upload_plan.v2",
        "slug": CANARY_SLUG,
        "release_descriptor_sha256": release_descriptor_sha256,
        "immutable_prefix": prefix,
        "release_status": "PRIVATE_STAGING_ONLY",
        "assets": plan_assets,
    }
    upload_plan_path = output_dir / "upload-plan.json"
    write_json(upload_plan_path, upload_plan)

    semantics = {
        "schema_version": "audiobook_package_semantics.v2",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "slug": CANARY_SLUG,
        "release_evidence_version": (
            f"goliveevidence-{evidence_hashes['goliveevidence.json'][:12]}"
        ),
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_sha256": controlled_source_sha256,
        "manuscript_sha256": manuscript_sha256,
        "duration_ms": cumulative_ms,
        "segment_count": len(segment_semantics),
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "sync_tier": "paragraph_or_stanza",
        "highlight_sync_enabled": False,
        "tracks": [
            {
                "id": "chapter-001",
                "chapter_id": "chapter-001",
                "order": 0,
                "title": CANARY_TITLE,
                "start_word": 0,
                "end_word": word_cursor - 1,
                "start_paragraph": 0,
                "end_paragraph": paragraph_cursor - 1,
                "chunks": segment_semantics,
            }
        ],
    }
    semantics_path = output_dir / "package-semantics.json"
    write_json(semantics_path, semantics)

    result = {
        "status": "PRIVATE_PACKAGE_BUILT",
        "slug": CANARY_SLUG,
        "output_dir": str(output_dir),
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_audio_sha256": CANARY_EXPECTED_AUDIO_SHA256,
        "duration_ms": cumulative_ms,
        "segment_count": 2,
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "upload_plan": str(upload_plan_path),
        "package_semantics": str(semantics_path),
        "release_blockers": release_descriptor["known_release_blockers"],
    }
    write_json(output_dir / "build-result.json", result)
    return result


def receipt_objects(receipt: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
    rows = receipt.get("objects")
    if not isinstance(rows, list):
        rows = receipt.get("assets")
    if not isinstance(rows, list):
        raise PackageBuildError(f"{label} must contain an objects array")
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise PackageBuildError(f"{label} contains a non-object receipt row")
        asset_id = str(row.get("asset_id") or "")
        if not asset_id or asset_id in mapped:
            raise PackageBuildError(f"{label} asset_id is missing or duplicated")
        mapped[asset_id] = row
    return mapped


def storage_record(
    row: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    label: str,
) -> dict[str, str]:
    for field in ("key", "sha256", "size_bytes", "mime_type"):
        if row.get(field) != expected.get(field):
            raise PackageBuildError(f"{label}.{field} does not match the upload plan")
    record = {
        "store": str(row.get("store") or ""),
        "bucket": str(row.get("bucket") or ""),
        "key": str(row.get("key") or ""),
        "version_id": str(row.get("version_id") or ""),
    }
    if not all(record.values()):
        raise PackageBuildError(f"{label} lacks exact storage identity")
    return record


def finalize_package(
    *,
    semantics: Mapping[str, Any],
    upload_plan: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        primary_receipt.get("receipt_role") != "primary"
        or primary_receipt.get("release_eligible") is not True
        or primary_receipt.get("passed") is not True
    ):
        raise PackageBuildError(
            "Primary receipt is not release-eligible production evidence"
        )
    replica_store = replica_receipt.get("store")
    if (
        replica_receipt.get("receipt_role") != "replica"
        or replica_receipt.get("passed") is not True
        or not isinstance(replica_store, Mapping)
        or replica_store.get("release_eligible") is not True
    ):
        raise PackageBuildError(
            "Replica receipt is not release-eligible DR evidence"
        )
    plan_assets = upload_plan.get("assets")
    if not isinstance(plan_assets, list):
        raise PackageBuildError("Upload plan must contain assets")
    plan_by_id = {
        str(asset["asset_id"]): asset
        for asset in plan_assets
        if isinstance(asset, dict) and asset.get("asset_id")
    }
    primary = receipt_objects(primary_receipt, "primary receipt")
    replica = receipt_objects(replica_receipt, "replica receipt")

    package: dict[str, Any] = {
        key: semantics[key]
        for key in (
            "slug",
            "release_evidence_version",
            "release_descriptor_sha256",
            "source_sha256",
            "manuscript_sha256",
            "duration_ms",
            "segment_count",
            "word_count",
            "paragraph_count",
            "sync_tier",
            "highlight_sync_enabled",
        )
    }
    package["schema_version"] = PACKAGE_SCHEMA_VERSION
    package["tracks"] = []
    for track in semantics.get("tracks") or []:
        normalized_track = {
            key: track[key]
            for key in (
                "id",
                "chapter_id",
                "order",
                "title",
                "start_word",
                "end_word",
                "start_paragraph",
                "end_paragraph",
            )
        }
        normalized_track["chunks"] = []
        for chunk in track.get("chunks") or []:
            normalized_chunk = {
                key: chunk[key]
                for key in (
                    "segment_id",
                    "order",
                    "start_word",
                    "end_word",
                    "start_paragraph",
                    "end_paragraph",
                    "cumulative_start_ms",
                    "duration_ms",
                )
            }
            normalized_chunk["assets"] = {}
            for asset_name, asset_id in chunk["asset_ids"].items():
                expected = plan_by_id.get(asset_id)
                primary_row = primary.get(asset_id)
                replica_row = replica.get(asset_id)
                if not expected or not primary_row or not replica_row:
                    raise PackageBuildError(
                        f"Final package lacks primary/DR receipt for {asset_id}"
                    )
                normalized_chunk["assets"][asset_name] = {
                    "sha256": expected["sha256"],
                    "size_bytes": expected["size_bytes"],
                    "mime_type": expected["mime_type"],
                    "storage": storage_record(
                        primary_row,
                        expected=expected,
                        label=f"primary.{asset_id}",
                    ),
                    "replicas": [
                        storage_record(
                            replica_row,
                            expected=expected,
                            label=f"replica.{asset_id}",
                        )
                    ],
                }
            normalized_track["chunks"].append(normalized_chunk)
        package["tracks"].append(normalized_track)

    package = with_canonical_package_version(package)
    return validate_audiobook_package(
        package,
        expected_slug=str(semantics["slug"]),
        expected_source_sha256=str(semantics["source_sha256"]),
        expected_manuscript_sha256=str(semantics["manuscript_sha256"]),
        expected_release_descriptor_sha256=str(
            semantics["release_descriptor_sha256"]
        ),
    )


def finalize_command(
    *,
    package_dir: Path,
    primary_receipt_path: Path,
    replica_receipt_path: Path,
) -> dict[str, Any]:
    semantics = read_json(package_dir / "package-semantics.json")
    upload_plan = read_json(package_dir / "upload-plan.json")
    package = finalize_package(
        semantics=semantics,
        upload_plan=upload_plan,
        primary_receipt=read_json(primary_receipt_path),
        replica_receipt=read_json(replica_receipt_path),
    )
    manifest_path = package_dir / "audiobook_package_manifest.v2.json"
    write_json(manifest_path, package)
    release_manifest_path = package_dir / "release-manifest.json"
    write_json(release_manifest_path, package)
    prefix = immutable_release_prefix(
        str(package["slug"]),
        str(package["release_descriptor_sha256"]),
    )
    manifest_upload_plan = {
        "schema_version": "audiobook_package_upload_plan.v2",
        "slug": package["slug"],
        "release_descriptor_sha256": package["release_descriptor_sha256"],
        "immutable_prefix": prefix,
        "release_status": "FINAL_MANIFEST_ONLY",
        "assets": [
            file_asset(
                asset_id="release.manifest",
                path=release_manifest_path,
                key=f"{prefix}release-manifest.json",
                mime_type="application/json",
            )
        ],
    }
    manifest_plan_path = package_dir / "release-manifest-upload-plan.json"
    write_json(manifest_plan_path, manifest_upload_plan)
    result = {
        "status": "FINAL_PACKAGE_HASH_BOUND",
        "slug": package["slug"],
        "package_version": package["package_version"],
        "release_descriptor_sha256": package["release_descriptor_sha256"],
        "manifest": str(manifest_path),
        "release_manifest_upload_plan": str(manifest_plan_path),
    }
    write_json(package_dir / "finalize-result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build/finalize immutable Earnalism audiobook package v2",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build-canary",
        help="Repackage the approved book-2b9853ec52 narration without TTS",
    )
    build.add_argument("--run-dir", type=Path, default=CANARY_RUN_DIR)
    build.add_argument("--output-dir", type=Path, required=True)

    approved_legacy = subparsers.add_parser(
        "build-approved-legacy",
        help=(
            "Build a release-candidate package from exact, already-approved "
            "legacy audiobook assets"
        ),
    )
    approved_legacy.add_argument("--repo-root", type=Path, default=ROOT)
    approved_legacy.add_argument("--slug", required=True)
    approved_legacy.add_argument("--audio", type=Path, required=True)
    approved_legacy.add_argument("--timestamps", type=Path, required=True)
    approved_legacy.add_argument("--vtt", type=Path, required=True)
    approved_legacy.add_argument("--chapters", type=Path, required=True)
    approved_legacy.add_argument("--meta", type=Path, required=True)
    approved_legacy.add_argument("--output-dir", type=Path, required=True)

    finalize = subparsers.add_parser(
        "finalize",
        help="Bind verified primary and DR VersionIds into a final manifest",
    )
    finalize.add_argument("--package-dir", type=Path, required=True)
    finalize.add_argument("--primary-receipt", type=Path, required=True)
    finalize.add_argument("--replica-receipt", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "build-canary":
            result = build_canary(
                run_dir=args.run_dir.resolve(),
                output_dir=args.output_dir,
            )
        elif args.command == "build-approved-legacy":
            result = build_approved_legacy(
                repo_root=args.repo_root.resolve(),
                slug=args.slug,
                audio_path=args.audio,
                timestamps_path=args.timestamps,
                vtt_path=args.vtt,
                chapters_path=args.chapters,
                meta_path=args.meta,
                output_dir=args.output_dir,
            )
        elif args.command == "finalize":
            result = finalize_command(
                package_dir=args.package_dir.resolve(),
                primary_receipt_path=args.primary_receipt.resolve(),
                replica_receipt_path=args.replica_receipt.resolve(),
            )
        else:  # pragma: no cover - argparse constrains this path.
            raise PackageBuildError(f"Unsupported command: {args.command}")
    except PackageBuildError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
