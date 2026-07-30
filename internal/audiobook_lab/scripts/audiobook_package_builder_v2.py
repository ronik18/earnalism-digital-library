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

``build-qa-candidate`` is the private-new-title producer.  It accepts the exact
Google full-generation manifest, a passing full audio-derived objective QA
report, a passing six-sample full-title listening report, canonical controlled
reader/source/rights/cover truth, and an explicit hash-bound package-build
authorization.  It does not require or create public audio approval.  Provider
files remain unchanged in provenance, while delivery segments are cut only at
canonical paragraph boundaries measured from audio-derived word timestamps.

No command in this module mutates controlled publication truth or uploads
objects.  Upload and verification are delegated to
``audiobook_package_storage_v2.py``.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


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
LEGACY_WORD_NORMALIZATION_SCHEMA = "approved_legacy_sidecar_normalization.v1"
LEGACY_WORD_NORMALIZATION_MODE = "measured_word_to_canonical_source_sections"
QA_CANDIDATE_RELEASE_EVIDENCE_SCHEMA = (
    "earnalism.audiobook_qa_candidate_release_evidence.v1"
)
GOOGLE_PRIVATE_PIPELINE_SCHEMA = "earnalism.google_english_private_pipeline.v1"
GOOGLE_PRIVATE_INPUT_SCHEMA = "earnalism.google_english_private_input.v1"
GOOGLE_FULL_OBJECTIVE_SCHEMA = "earnalism.google_english_full_audio_derived_qa.v1"
GOOGLE_FULL_LISTENING_QA_SCHEMA_VERSION = 1
LISTENING_QA_SCHEMA_VERSION = 3
QA_CANDIDATE_ASR_SCORE_MIN = 9.7
QA_CANDIDATE_COVERAGE_MIN = 0.98
QA_CANDIDATE_LISTENING_THRESHOLDS = {
    "naturalness_score": 8.9,
    "pronunciation_score": 8.9,
    "emotional_expression_score": 8.9,
    "punctuation_pause_score": 8.9,
    "pacing_score": 8.9,
    "continuity_score": 8.9,
    "anti_robotic_texture_score": 8.9,
    "anti_choppy_join_score": 8.9,
    "listener_enjoyment_score": 8.9,
    "overall_listening_score": 8.9,
    "confidence_score": 0.9,
}
QA_CANDIDATE_FATAL_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "list_reading_rhythm_detected",
    "repeated_identical_sentence_endings_detected",
    "abrupt_tts_resets_detected",
    "placeholder_audio_detected",
)
QA_CANDIDATE_ALLOWED_ENGLISH_LISTENING_POLICIES = frozenset(
    {
        "platform_audiobook_acceptance_v4_89",
    }
)
JEKYLL_INCREMENTAL_LISTENING_SCHEMA = (
    "earnalism.jekyll_google_chunk36_incremental_listening_qa.v1"
)
QA_CANDIDATE_DOWNSTREAM_GATES = (
    "PRIVATE_B2_PRIMARY_UPLOAD_REQUIRED",
    "PRIVATE_B2_DR_REPLICA_REQUIRED",
    "CONTROLLED_RELEASE_ACTIVATION_REQUIRED",
    "PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED",
)


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
        normalized = {
            "id": str(cue["id"]),
            "index": local_index,
            "start": start,
            "end": end,
            "duration_seconds": round(end - start, 3),
            "text": str(cue["text"]),
            "granularity": str(cue.get("granularity") or "paragraph_or_stanza"),
        }
        if str(cue.get("timing_origin") or "").strip():
            normalized["timing_origin"] = str(cue["timing_origin"])
        rebased.append(normalized)
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


def _safe_repo_evidence_path(
    repo_root: Path,
    relative_path: Any,
    expected_sha256: Any,
    label: str,
) -> Path:
    normalized = str(relative_path or "").strip()
    candidate_relative = Path(normalized)
    if (
        not normalized
        or candidate_relative.is_absolute()
        or ".." in candidate_relative.parts
    ):
        raise PackageBuildError(f"{label} path is not repository-relative")
    repo_root = repo_root.resolve()
    candidate = (repo_root / candidate_relative).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        raise PackageBuildError(f"{label} path escapes the repository") from None
    if not candidate.is_file():
        raise PackageBuildError(f"{label} file is missing")
    if sha256_file(candidate) != _require_sha256(expected_sha256, f"{label} hash"):
        raise PackageBuildError(f"{label} hash does not match")
    return candidate


def _alignment_tokens(
    text: str,
    *,
    collapse_intraword_hyphens: bool = False,
) -> list[str]:
    normalized = (
        unicodedata.normalize("NFKD", text.replace("\u2019", "'"))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    if collapse_intraword_hyphens:
        normalized = re.sub(r"(?<=[a-z0-9])-(?=[a-z0-9])", "", normalized)
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", normalized)


def _collapsed_whitespace(text: str) -> str:
    return " ".join(text.split())


def _alignment_characters(text: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", text.replace("\u2019", "'"))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _legacy_word_vtt_ranges(
    *,
    timestamps: Mapping[str, Any],
    vtt_path: Path,
    expected_word_count: int,
) -> tuple[list[dict[str, Any]], list[tuple[float, float]]]:
    raw_words = timestamps.get("words")
    if not isinstance(raw_words, list) or len(raw_words) != expected_word_count:
        raise PackageBuildError("Legacy measured-word timestamp count does not match")
    words: list[dict[str, Any]] = []
    previous_start = 0.0
    for index, raw in enumerate(raw_words):
        if not isinstance(raw, Mapping):
            raise PackageBuildError(f"Legacy measured word {index} is invalid")
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            raise PackageBuildError(
                f"Legacy measured word {index} boundary is invalid"
            ) from None
        word = str(raw.get("word") or "").strip()
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end < start
            or (index > 0 and start < previous_start - 0.01)
            or not word
        ):
            raise PackageBuildError(
                f"Legacy measured word {index} is not release-safe"
            )
        words.append({"word": word, "start": start, "end": end})
        previous_start = start

    ranges = _vtt_ranges(vtt_path)
    if len(ranges) != len(words):
        raise PackageBuildError("Legacy word VTT count does not match timestamps")
    for index, (word, (start, end)) in enumerate(zip(words, ranges)):
        expected_end = max(word["end"], word["start"] + 0.05)
        if (
            abs(start - word["start"]) > 0.01
            or abs(end - expected_end) > 0.011
        ):
            raise PackageBuildError(
                f"Legacy word VTT cue {index} does not match timestamps"
            )
    return words, ranges


def _equal_opcode_asr_anchor(
    boundary: int,
    opcodes: list[tuple[str, int, int, int, int]],
) -> Optional[int]:
    for tag, source_start, source_end, asr_start, _asr_end in opcodes:
        if tag == "equal" and source_start <= boundary <= source_end:
            return asr_start + (boundary - source_start)
    return None


def _coalesce_sections_to_equal_opcode_boundaries(
    *,
    sections: list[str],
    source_boundaries: list[int],
    opcodes: list[tuple[str, int, int, int, int]],
    asr_token_word_indexes: list[int],
    measured_word_count: int,
    minimum_retention_ratio: float,
) -> dict[str, Any]:
    if (
        _equal_opcode_asr_anchor(source_boundaries[0], opcodes) != 0
        or _equal_opcode_asr_anchor(source_boundaries[-1], opcodes)
        != len(asr_token_word_indexes)
    ):
        raise PackageBuildError(
            "Legacy normalization source endpoints lack equal-opcode anchors"
        )
    emitted_sections: list[str] = []
    word_boundaries = [0]
    pending_sections: list[str] = []
    anchored_internal_boundaries = 0
    for section_index, section in enumerate(sections):
        pending_sections.append(section)
        if section_index == len(sections) - 1:
            emitted_sections.append("\n\n".join(pending_sections))
            pending_sections = []
            word_boundaries.append(measured_word_count)
            continue
        source_boundary = source_boundaries[section_index + 1]
        asr_boundary = _equal_opcode_asr_anchor(source_boundary, opcodes)
        if (
            asr_boundary is None
            or asr_boundary <= 0
            or asr_boundary >= len(asr_token_word_indexes)
        ):
            continue
        word_boundary = asr_token_word_indexes[asr_boundary]
        if (
            asr_token_word_indexes[asr_boundary - 1] == word_boundary
            or word_boundary <= word_boundaries[-1]
        ):
            continue
        emitted_sections.append("\n\n".join(pending_sections))
        pending_sections = []
        word_boundaries.append(word_boundary)
        anchored_internal_boundaries += 1
    if pending_sections:
        raise PackageBuildError(
            "Legacy normalization did not close the canonical source sections"
        )
    if (
        len(emitted_sections) != len(word_boundaries) - 1
        or anchored_internal_boundaries != len(emitted_sections) - 1
        or anchored_internal_boundaries <= 0
    ):
        raise PackageBuildError(
            "Legacy normalization did not produce equal-opcode section boundaries"
        )
    original_internal_boundaries = len(sections) - 1
    boundary_retention_ratio = (
        anchored_internal_boundaries / original_internal_boundaries
    )
    if boundary_retention_ratio < minimum_retention_ratio:
        raise PackageBuildError(
            "Legacy normalization coalesced too many unanchored source sections"
        )
    return {
        "sections": emitted_sections,
        "word_boundaries": word_boundaries,
        "anchored_internal_boundary_count": anchored_internal_boundaries,
        "coalesced_boundary_count": (
            original_internal_boundaries - anchored_internal_boundaries
        ),
        "boundary_retention_ratio": boundary_retention_ratio,
        "boundary_quality_score": 1.0,
    }


def _normalize_legacy_measured_word_sidecars(
    *,
    repo_root: Path,
    context: Mapping[str, Any],
    slug: str,
    approval: Mapping[str, Any],
    timestamps: Mapping[str, Any],
    vtt_path: Path,
    meta: Mapping[str, Any],
    asset_facts: Mapping[str, Mapping[str, Any]],
    manuscript_sha256: str,
    audio_sha256: str,
    duration_seconds: float,
) -> dict[str, Any]:
    contract = approval.get("approved_legacy_sidecar_normalization")
    if not isinstance(contract, Mapping):
        raise PackageBuildError("Approved legacy sidecar normalization is invalid")
    if (
        contract.get("schema_version") != LEGACY_WORD_NORMALIZATION_SCHEMA
        or contract.get("mode") != LEGACY_WORD_NORMALIZATION_MODE
        or contract.get("output_granularity") != "section"
        or approval.get("source_coverage_method")
        != "audio_derived_asr_matching_characters_over_canonical_source_characters"
    ):
        raise PackageBuildError("Approved legacy sidecar normalization is unsupported")

    evidence_path = _safe_repo_evidence_path(
        repo_root,
        contract.get("release_evidence_path"),
        contract.get("release_evidence_sha256"),
        "Legacy normalization release evidence",
    )
    evidence = read_json(evidence_path)
    measured_quality = (
        evidence.get("measured_quality") if isinstance(evidence, Mapping) else None
    )
    sidecars = evidence.get("sidecars") if isinstance(evidence, Mapping) else None
    release_gates = (
        evidence.get("release_gates") if isinstance(evidence, Mapping) else None
    )
    if (
        evidence.get("schema_version")
        != "audiobook_package_v2_legacy_normalization_evidence.v1"
        or evidence.get("slug") != slug
        or evidence.get("status") != "NORMALIZATION_INPUT_EVIDENCE_READY"
        or evidence.get("narration_regenerated") is not False
        or evidence.get("release_gate_mutated") is not False
        or not isinstance(measured_quality, Mapping)
        or not isinstance(sidecars, Mapping)
        or not isinstance(release_gates, Mapping)
        or measured_quality.get("auto_estimated_sync") is not False
        or measured_quality.get("sync_tier")
        != "SECTION_BOUNDARIES_EQUAL_OPCODE_MEASURED"
        or measured_quality.get("boundary_method")
        != "equal_opcode_anchored_internal_boundaries"
        or release_gates.get("source_binding") != "PASS"
        or release_gates.get("asr_source") != "PASS"
        or release_gates.get("first_last") != "PASS"
        or release_gates.get("sidecars") != "PASS"
    ):
        raise PackageBuildError("Legacy normalization release evidence does not pass")
    upstream_reference = evidence.get("upstream_release_evidence")
    if not isinstance(upstream_reference, Mapping):
        raise PackageBuildError("Legacy normalization upstream evidence is missing")
    upstream_path = _safe_repo_evidence_path(
        repo_root,
        upstream_reference.get("path"),
        upstream_reference.get("sha256"),
        "Legacy normalization upstream release evidence",
    )
    upstream = read_json(upstream_path)
    upstream_quality = (
        upstream.get("measured_quality") if isinstance(upstream, Mapping) else None
    )
    upstream_sidecars = (
        upstream.get("sidecars") if isinstance(upstream, Mapping) else None
    )
    upstream_gates = (
        upstream.get("release_gates") if isinstance(upstream, Mapping) else None
    )
    if (
        upstream.get("slug") != slug
        or not isinstance(upstream_quality, Mapping)
        or not isinstance(upstream_sidecars, Mapping)
        or not isinstance(upstream_gates, Mapping)
        or upstream_quality.get("sync_score")
        != measured_quality.get("upstream_transcript_vtt_sync_score")
        or upstream_quality.get("sync_tier")
        != measured_quality.get("upstream_sync_tier")
        or upstream_quality.get("auto_estimated_sync")
        != measured_quality.get("auto_estimated_sync")
        or upstream_sidecars.get("timestamps") != sidecars.get("timestamps")
        or upstream_sidecars.get("vtt") != sidecars.get("vtt")
        or any(
            upstream_gates.get(name) != "PASS"
            for name in ("source_binding", "asr_source", "first_last", "sidecars")
        )
    ):
        raise PackageBuildError(
            "Legacy normalization upstream release evidence conflicts"
        )
    upstream_sync_score = _require_number(
        measured_quality.get("upstream_transcript_vtt_sync_score"),
        "Legacy normalization upstream transcript/VTT sync score",
        0.000001,
    )
    evidence_timestamps = sidecars.get("timestamps")
    evidence_vtt = sidecars.get("vtt")
    if (
        not isinstance(evidence_timestamps, Mapping)
        or not isinstance(evidence_vtt, Mapping)
        or evidence_timestamps.get("sha256")
        != asset_facts["timestamps"]["sha256"]
        or evidence_vtt.get("sha256") != asset_facts["vtt"]["sha256"]
    ):
        raise PackageBuildError("Legacy normalization sidecar evidence conflicts")

    expected_hashes = contract.get("input_sha256")
    if not isinstance(expected_hashes, Mapping):
        raise PackageBuildError("Legacy normalization input hashes are missing")
    for name in ("timestamps", "vtt"):
        if expected_hashes.get(name) != asset_facts[name]["sha256"]:
            raise PackageBuildError(
                f"Legacy normalization {name} hash does not match approved bytes"
            )

    chapter_files = contract.get("source_chapter_files")
    if not isinstance(chapter_files, list) or not chapter_files:
        raise PackageBuildError("Legacy normalization source chapters are missing")
    checksum_rows = _checksum_rows(context["checksum_manifest"])
    source_parts: list[str] = []
    for relative_value in chapter_files:
        relative = str(relative_value or "").strip()
        if (
            not relative.startswith("chapters/")
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise PackageBuildError(
                "Legacy normalization chapter path is not controlled"
            )
        expected_hash = checksum_rows.get(relative)
        if not expected_hash:
            raise PackageBuildError(
                "Legacy normalization chapter lacks a controlled checksum"
            )
        mirror_paths = [directory / relative for directory in context["dirs"]]
        if (
            any(not path.is_file() for path in mirror_paths)
            or any(sha256_file(path) != expected_hash for path in mirror_paths)
            or mirror_paths[0].read_bytes() != mirror_paths[1].read_bytes()
        ):
            raise PackageBuildError(
                "Legacy normalization controlled chapter mirrors diverge"
            )
        chapter = read_json(mirror_paths[0])
        content = chapter.get("content") if isinstance(chapter, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise PackageBuildError(
                "Legacy normalization controlled chapter has no content"
            )
        source_parts.append(content.rstrip("\n"))

    source_text = "\n".join(source_parts) + "\n"
    canonical_source_sha256 = hashlib.sha256(
        source_text.encode("utf-8")
    ).hexdigest()
    equivalence = contract.get("source_text_equivalence")
    collapse_intraword_hyphens = False
    narrated_manuscript_path: Optional[Path] = None
    if equivalence is None:
        if canonical_source_sha256 != manuscript_sha256:
            raise PackageBuildError(
                "Legacy normalization source does not match narrated manuscript"
            )
    else:
        if (
            not isinstance(equivalence, Mapping)
            or equivalence.get("schema_version")
            != "approved_legacy_source_text_equivalence.v1"
            or equivalence.get("mode") != "collapse_whitespace_only"
            or equivalence.get("alignment_token_mode")
            != "collapse_intraword_ascii_hyphens"
            or equivalence.get("canonical_source_sha256")
            != canonical_source_sha256
        ):
            raise PackageBuildError(
                "Approved legacy source text equivalence is unsupported"
            )
        narrated_manuscript_path = _safe_repo_evidence_path(
            repo_root,
            equivalence.get("narrated_manuscript_path"),
            equivalence.get("narrated_manuscript_sha256"),
            "Legacy narrated manuscript",
        )
        if sha256_file(narrated_manuscript_path) != manuscript_sha256:
            raise PackageBuildError(
                "Legacy narrated manuscript conflicts with approved source hash"
            )
        narrated_text = narrated_manuscript_path.read_text(encoding="utf-8")
        if _collapsed_whitespace(narrated_text) != _collapsed_whitespace(source_text):
            raise PackageBuildError(
                "Legacy narrated and canonical source differ beyond whitespace"
            )
        collapse_intraword_hyphens = True
    sections = [
        section.rstrip()
        for section in re.split(r"\n[ \t]*\n", source_text.rstrip("\n"))
        if section.strip()
    ]
    expected_section_count = int(
        _require_number(
            contract.get("source_section_count"),
            "Legacy normalization source section count",
            1,
        )
    )
    if len(sections) != expected_section_count:
        raise PackageBuildError(
            "Legacy normalization source section count does not match"
        )
    reconstructed = "\n\n".join(sections) + "\n"
    if reconstructed != source_text:
        raise PackageBuildError(
            "Legacy normalization would rewrite canonical source text"
        )
    normalization_source = evidence.get("source")
    if (
        not isinstance(normalization_source, Mapping)
        or len(chapter_files) != 1
        or normalization_source.get("chapter_path") != chapter_files[0]
        or normalization_source.get("chapter_sha256")
        != checksum_rows.get(chapter_files[0])
        or normalization_source.get("manuscript_sha256") != manuscript_sha256
        or normalization_source.get(
            "canonical_source_sha256",
            manuscript_sha256,
        )
        != canonical_source_sha256
        or normalization_source.get("section_count") != len(sections)
        or normalization_source.get("coverage") != approval.get("source_coverage")
        or normalization_source.get("coverage_method")
        != approval.get("source_coverage_method")
    ):
        raise PackageBuildError(
            "Legacy normalization canonical source evidence conflicts"
        )
    if equivalence is not None and (
        normalization_source.get("text_equivalence_mode")
        != "collapse_whitespace_only"
        or normalization_source.get("alignment_token_mode")
        != "collapse_intraword_ascii_hyphens"
        or normalization_source.get("narrated_manuscript_sha256")
        != manuscript_sha256
    ):
        raise PackageBuildError(
            "Legacy normalization source equivalence evidence conflicts"
        )

    expected_word_count = int(
        _require_number(
            contract.get("measured_word_count"),
            "Legacy normalization measured word count",
            1,
        )
    )
    words, _ranges = _legacy_word_vtt_ranges(
        timestamps=timestamps,
        vtt_path=vtt_path,
        expected_word_count=expected_word_count,
    )
    if (
        timestamps.get("slug") != slug
        or timestamps.get("audio_hash") != audio_sha256
        or timestamps.get("source_text_hash") != manuscript_sha256
        or timestamps.get("auto_estimated_sync") is not False
        or str(timestamps.get("alignment_method") or "").lower()
        != "openai_verbose_json_word_timestamps"
    ):
        raise PackageBuildError(
            "Legacy measured-word timestamps do not match release truth"
        )

    source_tokens: list[str] = []
    source_boundaries = [0]
    for section in sections:
        tokens = _alignment_tokens(
            section,
            collapse_intraword_hyphens=collapse_intraword_hyphens,
        )
        if not tokens:
            raise PackageBuildError("Canonical source section has no alignment tokens")
        source_tokens.extend(tokens)
        source_boundaries.append(len(source_tokens))
    asr_tokens: list[str] = []
    asr_token_word_indexes: list[int] = []
    for word_index, word in enumerate(words):
        tokens = _alignment_tokens(
            word["word"],
            collapse_intraword_hyphens=collapse_intraword_hyphens,
        )
        if not tokens:
            raise PackageBuildError("Legacy measured word has no alignment token")
        asr_tokens.extend(tokens)
        asr_token_word_indexes.extend([word_index] * len(tokens))
    matcher = difflib.SequenceMatcher(
        None,
        source_tokens,
        asr_tokens,
        autojunk=False,
    )
    minimum_ratio = _require_number(
        contract.get("minimum_monotonic_alignment_ratio"),
        "Legacy normalization monotonic alignment ratio",
        0,
    )
    if matcher.ratio() < minimum_ratio:
        raise PackageBuildError(
            "Legacy measured words do not align safely to canonical source sections"
        )
    opcodes = matcher.get_opcodes()
    required_retention_ratio = _require_number(
        contract.get("minimum_boundary_retention_ratio"),
        "Legacy normalization boundary retention ratio",
        0,
    )
    boundary_result = _coalesce_sections_to_equal_opcode_boundaries(
        sections=sections,
        source_boundaries=source_boundaries,
        opcodes=opcodes,
        asr_token_word_indexes=asr_token_word_indexes,
        measured_word_count=len(words),
        minimum_retention_ratio=required_retention_ratio,
    )
    emitted_sections = boundary_result["sections"]
    word_boundaries = boundary_result["word_boundaries"]
    anchored_internal_boundaries = boundary_result[
        "anchored_internal_boundary_count"
    ]
    coalesced_boundary_count = boundary_result["coalesced_boundary_count"]
    boundary_retention_ratio = boundary_result["boundary_retention_ratio"]
    boundary_quality_score = boundary_result["boundary_quality_score"]
    controlled_boundary_score = _require_number(
        approval.get("measured_section_boundary_score"),
        "Measured section boundary score",
        1.0,
    )
    if (
        approval.get("measured_section_boundary_method")
        != "equal_opcode_anchored_internal_boundaries"
        or abs(boundary_quality_score - controlled_boundary_score) > 0.000001
        or abs(
            boundary_quality_score
            - _require_number(
                measured_quality.get("post_conversion_boundary_quality_score"),
                "Post-conversion section boundary quality score",
                1.0,
            )
        )
        > 0.000001
    ):
        raise PackageBuildError(
            "Legacy normalization section boundary quality evidence conflicts"
        )

    time_boundaries = [
        0.0
        if boundary == 0
        else duration_seconds
        if boundary == len(words)
        else round(words[boundary]["start"], 3)
        for boundary in word_boundaries
    ]
    cues: list[dict[str, Any]] = []
    for index, section in enumerate(emitted_sections):
        start = time_boundaries[index]
        end = time_boundaries[index + 1]
        if end <= start:
            raise PackageBuildError(
                f"Legacy normalized source section {index} has no measured duration"
            )
        cues.append(
            {
                "id": f"paragraph-{index + 1:04d}",
                "index": index,
                "start": start,
                "end": end,
                "duration_seconds": round(end - start, 3),
                "text": section,
                "granularity": "section",
                "timing_origin": (
                    "measured_equal_opcode_word_anchor_bound_to_canonical_source"
                ),
            }
        )
    if "\n\n".join(cue["text"] for cue in cues) + "\n" != source_text:
        raise PackageBuildError(
            "Legacy normalization cues do not preserve canonical source text"
        )
    if (
        normalization_source.get("emitted_section_count") != len(cues)
        or normalization_source.get("anchored_internal_boundary_count")
        != anchored_internal_boundaries
        or normalization_source.get("coalesced_boundary_count")
        != coalesced_boundary_count
        or abs(
            _require_number(
                normalization_source.get("boundary_retention_ratio"),
                "Normalization evidence boundary retention ratio",
                0,
            )
            - boundary_retention_ratio
        )
        > 0.000001
    ):
        raise PackageBuildError(
            "Legacy normalization emitted-boundary evidence conflicts"
        )
    source_characters = _alignment_characters(source_text)
    asr_characters = _alignment_characters(
        " ".join(word["word"] for word in words)
    )
    if not source_characters or not asr_characters:
        raise PackageBuildError(
            "Legacy normalization cannot measure ASR/source coverage"
        )
    character_matcher = difflib.SequenceMatcher(
        None,
        source_characters,
        asr_characters,
        autojunk=False,
    )
    source_coverage = (
        sum(block.size for block in character_matcher.get_matching_blocks())
        / len(source_characters)
    )
    if abs(
        source_coverage
        - _require_number(
            approval.get("source_coverage"),
            "ASR/source coverage",
            0.98,
        )
    ) > 0.000001:
        raise PackageBuildError(
            "Legacy normalized source coverage conflicts with controlled evidence"
        )

    meta_score = _require_number(
        meta.get("sync_score", meta.get("vtt_alignment_score")),
        "Legacy metadata measured sync score",
        0.000001,
    )
    if (
        meta.get("slug") != slug
        or meta.get("audio_hash") != audio_sha256
        or meta.get("source_text_hash") != manuscript_sha256
        or meta.get("auto_estimated_sync") is not False
        or abs(meta_score - upstream_sync_score) > 0.000001
    ):
        raise PackageBuildError(
            "Legacy metadata does not match measured normalization evidence"
        )
    return {
        "cues": cues,
        "source_coverage": source_coverage,
        "alignment_ratio": matcher.ratio(),
        "boundary_quality_score": boundary_quality_score,
        "boundary_retention_ratio": boundary_retention_ratio,
        "anchored_internal_boundary_count": anchored_internal_boundaries,
        "coalesced_boundary_count": (
            coalesced_boundary_count
        ),
        "release_evidence_path": evidence_path,
        "narrated_manuscript_path": narrated_manuscript_path,
    }


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
    normalization_requested = (
        approval.get("approved_legacy_sidecar_normalization") is not None
    )
    measured_sync_score: Optional[float] = None
    if not normalization_requested:
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
    normalization_result: Optional[dict[str, Any]] = None
    if approval.get("approved_legacy_sidecar_normalization") is not None:
        normalization_result = _normalize_legacy_measured_word_sidecars(
            repo_root=repo_root,
            context=context,
            slug=slug,
            approval=approval,
            timestamps=timestamps,
            vtt_path=inputs["vtt"],
            meta=meta,
            asset_facts=asset_facts,
            manuscript_sha256=manuscript_sha256,
            audio_sha256=asset_facts["mp3"]["sha256"],
            duration_seconds=duration_seconds,
        )
        cues = normalization_result["cues"]
        measured_sync_score = normalization_result["boundary_quality_score"]
    else:
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
    if normalization_result is None:
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
        or abs(meta_duration_seconds - duration_seconds)
        > AUDIO_DURATION_TOLERANCE_SECONDS
    ):
        raise PackageBuildError("Legacy metadata sidecar does not match release truth")
    if (
        normalization_result is None
        and str(meta.get("sync_granularity") or "").lower()
        not in MEASURED_SYNC_GRANULARITIES
    ):
        raise PackageBuildError("Legacy metadata sync is not paragraph/stanza measured")
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
        "normalization_result": normalization_result,
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
            "measured_sync_kind": (
                "equal_opcode_anchored_section_boundaries"
                if normalization_result is not None
                else "paragraph_or_stanza"
            ),
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


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _candidate_artifact(
    value: Any,
    *,
    run_dir: Path,
    label: str,
) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise PackageBuildError(f"{label} path is missing")
    path = Path(raw).expanduser()
    path = (run_dir / path).resolve() if not path.is_absolute() else path.resolve()
    if not _is_within(path, run_dir):
        raise PackageBuildError(f"{label} must remain inside the private full run")
    if not path.is_file():
        raise PackageBuildError(f"{label} is missing: {path}")
    return path


def _lexical_tokens(text: str) -> list[str]:
    normalized = (
        str(text or "")
        .lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("—", " ")
        .replace("–", " ")
    )
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", normalized)


def _candidate_chapter_material(
    context: Mapping[str, Any],
    *,
    slug: str,
) -> dict[str, Any]:
    directories = context["dirs"]
    reader_manifest = context["reader_manifest"]
    public_book = context["public_book"]
    checksum_rows = _checksum_rows(context["checksum_manifest"])
    raw_reader_chapters = reader_manifest.get("chapters")
    raw_public_chapters = public_book.get("chapters")
    if (
        not isinstance(raw_reader_chapters, list)
        or not raw_reader_chapters
        or raw_reader_chapters != raw_public_chapters
    ):
        raise PackageBuildError(
            "Controlled public and reader chapter manifests must agree"
        )
    ordered_metadata = sorted(
        raw_reader_chapters,
        key=lambda row: int(row.get("order") or 0)
        if isinstance(row, Mapping)
        else 0,
    )
    expected_orders = list(range(1, len(ordered_metadata) + 1))
    if [
        row.get("order") if isinstance(row, Mapping) else None
        for row in ordered_metadata
    ] != expected_orders:
        raise PackageBuildError("Controlled chapter order is not contiguous")

    chapter_rows: list[dict[str, Any]] = []
    for metadata in ordered_metadata:
        if not isinstance(metadata, Mapping):
            raise PackageBuildError("Controlled chapter metadata is invalid")
        chapter_id = str(metadata.get("id") or "")
        if not PACKAGE_ID_RE.fullmatch(chapter_id):
            raise PackageBuildError("Controlled chapter id is invalid")
        relative = f"chapters/{chapter_id}.json"
        expected_sha256 = checksum_rows.get(relative)
        if not expected_sha256:
            raise PackageBuildError(
                f"Controlled checksum is missing for {relative}"
            )
        documents = [read_json(directory / relative) for directory in directories]
        for directory, document in zip(directories, documents):
            if sha256_file(directory / relative) != expected_sha256:
                raise PackageBuildError(
                    f"Controlled chapter checksum is stale: {relative}"
                )
            if not isinstance(document, Mapping):
                raise PackageBuildError(f"Controlled chapter is invalid: {relative}")
        if documents[0] != documents[1]:
            raise PackageBuildError(
                f"Controlled chapter mirrors diverge: {relative}"
            )
        document = documents[0]
        text = (
            str(document.get("content") or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .strip()
        )
        if (
            document.get("bookSlug") != slug
            or document.get("id") != chapter_id
            or document.get("order") != metadata.get("order")
            or document.get("processing_status") != "ready"
            or document.get("processing_warnings") not in (None, [])
            or not text
        ):
            raise PackageBuildError(
                f"Controlled chapter is not reader-ready: {relative}"
            )
        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]
        if not paragraphs or any(not _lexical_tokens(item) for item in paragraphs):
            raise PackageBuildError(
                f"Controlled chapter lacks packageable paragraphs: {relative}"
            )
        chapter_rows.append(
            {
                "id": chapter_id,
                "order": int(metadata["order"]),
                "title": str(metadata.get("title") or chapter_id),
                "text": text,
                "paragraphs": paragraphs,
                "path": directories[0] / relative,
                "sha256": expected_sha256,
            }
        )
    source_text = "\n\n".join(row["text"] for row in chapter_rows).strip() + "\n"
    return {
        "chapters": chapter_rows,
        "source_text": source_text,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "chapter_sha256": {
            row["id"]: row["sha256"] for row in chapter_rows
        },
    }


def _candidate_cover_context(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    directories = context["dirs"]
    checksum_rows = _checksum_rows(context["checksum_manifest"])
    filename = "cover_approval_evidence.json"
    expected_sha256 = checksum_rows.get(filename)
    if not expected_sha256:
        raise PackageBuildError("Controlled cover approval checksum is missing")
    documents = [read_json(directory / filename) for directory in directories]
    for directory in directories:
        if sha256_file(directory / filename) != expected_sha256:
            raise PackageBuildError("Controlled cover approval checksum is stale")
    if documents[0] != documents[1]:
        raise PackageBuildError("Controlled cover approval mirrors diverge")
    evidence = documents[0]
    if not isinstance(evidence, Mapping):
        raise PackageBuildError("Controlled cover approval evidence is invalid")
    public_book = context["public_book"]
    dimensions = public_book.get("cover_dimensions")
    if not isinstance(dimensions, Mapping):
        raise PackageBuildError("Canonical front/back cover dimensions are missing")
    active = evidence.get("active_approvals")
    history = evidence.get("history")
    if not isinstance(active, Mapping) or not isinstance(history, list):
        raise PackageBuildError("Canonical cover approvals are incomplete")
    events = {
        str(row.get("event_id")): row
        for row in history
        if isinstance(row, Mapping) and row.get("event_id")
    }
    cover_rows: dict[str, dict[str, Any]] = {}
    for kind, public_url_field in (
        ("front", "cover_url"),
        ("back", "back_cover_url"),
    ):
        event = events.get(str(active.get(kind) or ""))
        url = str(public_book.get(public_url_field) or "")
        expected_dimensions = dimensions.get(kind)
        if (
            not isinstance(event, Mapping)
            or event.get("slug") != public_book.get("slug")
            or event.get("kind") != kind
            or event.get("decision") != "APPROVE_CANONICAL_COVER"
            or event.get("candidate_sha256") != event.get("remote_sha256")
            or not SHA256_RE.fullmatch(str(event.get("remote_sha256") or ""))
            or not isinstance(event.get("cloudinary"), Mapping)
            or event["cloudinary"].get("url") != url
            or not url.startswith("https://")
            or str(event.get("remote_sha256")) not in url
            or expected_dimensions
            != [event.get("width"), event.get("height")]
            or not str(event.get("rights_basis") or "").strip()
            or event.get("reader_audio_release_truth_unchanged") is not True
        ):
            raise PackageBuildError(
                f"Canonical {kind} cover is not approval-bound"
            )
        cover_rows[kind] = {
            "url": url,
            "sha256": str(event["remote_sha256"]),
            "width": int(event["width"]),
            "height": int(event["height"]),
            "approval_event_id": str(event["event_id"]),
        }
    return {
        "path": directories[0] / filename,
        "sha256": expected_sha256,
        "covers": cover_rows,
    }


def _load_qa_candidate_publication(
    repo_root: Path,
    slug: str,
) -> dict[str, Any]:
    context = _load_mirrored_publication(repo_root, slug)
    public_book = context["public_book"]
    reader_manifest = context["reader_manifest"]
    approval = context["approval_evidence"]
    source_evidence = context["source_evidence"]
    if any(
        document.get("slug") != slug
        for document in (public_book, reader_manifest, approval, source_evidence)
    ):
        raise PackageBuildError("Controlled candidate slug identity conflicts")
    if (
        public_book.get("approved_to_publish") is not True
        or public_book.get("isPublic") is not True
        or public_book.get("isLive") is not True
        or public_book.get("allowPublicReading") is not True
        or public_book.get("audio_enabled") is not False
        or public_book.get("audiobook_enabled") is not False
        or reader_manifest.get("audio_enabled") is not False
        or reader_manifest.get("audiobook_enabled") is not False
        or approval.get("approved_to_publish") is not True
        or approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_BLOCKED"
    ):
        raise PackageBuildError(
            "QA-candidate profile requires a live reader with public audio "
            "still blocked"
        )
    if (
        approval.get("rights_tier") != "A"
        or str(approval.get("verification_status") or "").lower() != "approved"
        or approval.get("audiobook_use_approved") is not True
        or not str(source_evidence.get("rights_basis") or "").strip()
        or source_evidence.get("reader_facing_boilerplate_removed") is not True
    ):
        raise PackageBuildError(
            "Controlled candidate rights are not tier A and audiobook-cleared"
        )
    title = str(public_book.get("title") or "").strip()
    author = str(public_book.get("author") or "").strip()
    language = str(reader_manifest.get("language") or "").strip().lower()
    if (
        not title
        or not author
        or reader_manifest.get("title") != title
        or reader_manifest.get("author") != author
        or language not in {"en", "eng", "english"}
    ):
        raise PackageBuildError(
            "Controlled English title/author/language identity is incomplete"
        )
    chapter_material = _candidate_chapter_material(context, slug=slug)
    cover_context = _candidate_cover_context(context)
    return {
        **context,
        "title": title,
        "author": author,
        "language": "en",
        "chapter_material": chapter_material,
        "cover_context": cover_context,
        "controlled_source_sha256": _require_sha256(
            source_evidence.get("source_hash"),
            "Controlled source hash",
        ),
    }


def _validate_candidate_full_manifest(
    manifest_path: Path,
    *,
    context: Mapping[str, Any],
    slug: str,
) -> dict[str, Any]:
    path = manifest_path.expanduser().resolve()
    if path.name != "full_generation_manifest.json" or not path.is_file():
        raise PackageBuildError(
            "QA candidate requires an exact full_generation_manifest.json"
        )
    run_dir = path.parent
    manifest = read_json(path)
    if not isinstance(manifest, Mapping):
        raise PackageBuildError("Full generation manifest must be an object")
    if (
        manifest.get("schema_version") != GOOGLE_PRIVATE_PIPELINE_SCHEMA
        or manifest.get("status") != "FULL_GENERATION_PRIVATE_QA_PENDING"
        or manifest.get("mode") != "full"
        or manifest.get("provider") != "google"
        or not str(manifest.get("language_code") or "").startswith("en-")
        or manifest.get("private_output_only") is not True
        or manifest.get("public_release_approved") is not False
        or manifest.get("upload_performed") is not False
        or manifest.get("publication_performed") is not False
        or manifest.get("release_mutation_performed") is not False
        or manifest.get("paid_lock_restored_byte_for_byte") is not True
        or manifest.get("provider_calls_ran") is not True
        or manifest.get("errors") != []
    ):
        raise PackageBuildError("Full generation manifest is not private QA-ready")
    if (
        manifest.get("slug") != slug
        or manifest.get("title") != context["title"]
        or manifest.get("author") != context["author"]
    ):
        raise PackageBuildError("Full generation title identity conflicts")
    declared_manifest = _candidate_artifact(
        manifest.get("result_manifest_path"),
        run_dir=run_dir,
        label="Full result manifest",
    )
    if declared_manifest != path:
        raise PackageBuildError("Full result manifest binding is stale")
    source_path = _candidate_artifact(
        manifest.get("sanitized_source_copy"),
        run_dir=run_dir,
        label="Sanitized source",
    )
    input_manifest_path = _candidate_artifact(
        manifest.get("input_manifest_copy"),
        run_dir=run_dir,
        label="Input manifest",
    )
    source_sha256 = sha256_file(source_path)
    input_manifest_sha256 = sha256_file(input_manifest_path)
    canonical_source = context["chapter_material"]["source_text"].encode("utf-8")
    if (
        source_path.read_bytes() != canonical_source
        or source_sha256 != context["chapter_material"]["source_sha256"]
        or manifest.get("source_sha256") != source_sha256
        or manifest.get("input_manifest_sha256") != input_manifest_sha256
    ):
        raise PackageBuildError(
            "Full generation source is not the exact canonical controlled manuscript"
        )
    input_manifest = read_json(input_manifest_path)
    if not isinstance(input_manifest, Mapping):
        raise PackageBuildError("Google input manifest must be an object")
    expected_controlled_path = f"data/controlled_publications/{slug}"
    if (
        input_manifest.get("schema_version") != GOOGLE_PRIVATE_INPUT_SCHEMA
        or input_manifest.get("slug") != slug
        or input_manifest.get("title") != context["title"]
        or input_manifest.get("author") != context["author"]
        or str(input_manifest.get("language") or "").lower() != "en"
        or input_manifest.get("sanitized_source_sha256") != source_sha256
        or input_manifest.get("sanitized_source_characters")
        != len(canonical_source.decode("utf-8"))
        or input_manifest.get("chapter_count")
        != len(context["chapter_material"]["chapters"])
        or input_manifest.get("chapter_orders")
        != list(range(1, len(context["chapter_material"]["chapters"]) + 1))
        or input_manifest.get("sanitization_status") != "PASS"
        or input_manifest.get("rights_status") != "PASS"
        or input_manifest.get("commercial_use_allowed") is not True
        or input_manifest.get("controlled_publication_path")
        != expected_controlled_path
        or input_manifest.get("source_evidence_path")
        != f"{expected_controlled_path}/source_evidence.json"
        or input_manifest.get("approval_evidence_path")
        != f"{expected_controlled_path}/approval_evidence.json"
        or input_manifest.get("public_audio_release_approved") is not False
    ):
        raise PackageBuildError(
            "Google input manifest is not bound to canonical reader/source/rights truth"
        )

    generated = manifest.get("generated_audio")
    unit_count = manifest.get("unit_count")
    if (
        not isinstance(generated, list)
        or not generated
        or not isinstance(unit_count, int)
        or isinstance(unit_count, bool)
        or unit_count != len(generated)
        or manifest.get("synthesis_calls") != unit_count
    ):
        raise PackageBuildError("Full generation audio sequence is incomplete")
    expected_unit_hashes: list[str] = []
    records: list[dict[str, Any]] = []
    flattened_source = _collapsed_whitespace(source_path.read_text(encoding="utf-8"))
    cursor = 0
    seen_paths: set[Path] = set()
    seen_hashes: set[str] = set()
    for index, raw in enumerate(generated):
        if not isinstance(raw, Mapping):
            raise PackageBuildError(f"Generated audio row {index} is invalid")
        unit_id = f"chunk_{index:04d}"
        characters = raw.get("characters")
        if (
            raw.get("unit_id") != unit_id
            or not isinstance(characters, int)
            or isinstance(characters, bool)
            or characters <= 0
        ):
            raise PackageBuildError(
                "Generated audio order or character count is invalid"
            )
        end = cursor + characters
        source_text = flattened_source[cursor:end]
        if (
            end > len(flattened_source)
            or hashlib.sha256(source_text.encode("utf-8")).hexdigest()
            != raw.get("text_sha256")
        ):
            raise PackageBuildError(
                f"Generated audio source order diverges at {unit_id}"
            )
        cursor = end
        if index < unit_count - 1:
            if flattened_source[cursor : cursor + 1] != " ":
                raise PackageBuildError(
                    f"Generated audio source boundary is invalid at {unit_id}"
                )
            cursor += 1
        audio_path = _candidate_artifact(
            raw.get("audio_path"),
            run_dir=run_dir,
            label=unit_id,
        )
        audio_sha256 = sha256_file(audio_path)
        with audio_path.open("rb") as audio_stream:
            header = audio_stream.read(3)
        if (
            audio_path.suffix.lower() != ".mp3"
            or audio_path in seen_paths
            or audio_sha256 in seen_hashes
            or raw.get("audio_sha256") != audio_sha256
            or raw.get("audio_size_bytes") != audio_path.stat().st_size
            or (header != b"ID3" and header[:1] != b"\xff")
        ):
            raise PackageBuildError(
                f"Generated provider audio identity is invalid at {unit_id}"
            )
        duration_ms = ffprobe_duration_ms(audio_path)
        expected_unit_hashes.append(str(raw["text_sha256"]))
        records.append(
            {
                "unit_id": unit_id,
                "text_sha256": str(raw["text_sha256"]),
                "characters": characters,
                "source_text": source_text,
                "audio_path": audio_path,
                "audio_sha256": audio_sha256,
                "audio_size_bytes": audio_path.stat().st_size,
                "duration_ms": duration_ms,
            }
        )
        seen_paths.add(audio_path)
        seen_hashes.add(audio_sha256)
    if (
        cursor != len(flattened_source)
        or manifest.get("unit_hashes") != expected_unit_hashes
    ):
        raise PackageBuildError(
            "Generated audio chunks do not cover the canonical manuscript exactly"
        )
    try:
        speaking_rate = float(manifest.get("speaking_rate"))
        pitch = float(manifest.get("pitch"))
    except (TypeError, ValueError):
        raise PackageBuildError(
            "Generated audio voice settings are invalid"
        ) from None
    expected_attempt_fingerprint = canonical_sha256(
        {
            "schema": GOOGLE_PRIVATE_PIPELINE_SCHEMA,
            "mode": "full",
            "provider": "google",
            "source_sha256": source_sha256,
            "manifest_sha256": input_manifest_sha256,
            "voice": manifest.get("voice"),
            "language_code": manifest.get("language_code"),
            "speaking_rate": speaking_rate,
            "pitch": pitch,
            "unit_hashes": expected_unit_hashes,
        }
    )
    if (
        not str(manifest.get("voice") or "").startswith(
            f"{manifest.get('language_code')}-"
        )
        or not math.isfinite(speaking_rate)
        or not 0.25 <= speaking_rate <= 4.0
        or not math.isfinite(pitch)
        or not -20.0 <= pitch <= 20.0
        or manifest.get("attempt_fingerprint")
        != expected_attempt_fingerprint
        or not SHA256_RE.fullmatch(
            str(manifest.get("audition_evidence_sha256") or "")
        )
    ):
        raise PackageBuildError(
            "Generated audio attempt identity or voice binding is invalid"
        )
    sequence_sha256 = canonical_sha256(
        [record["audio_sha256"] for record in records]
    )
    bounded_repair = manifest.get("bounded_chunk_repair")
    objective_attempt_fingerprint = expected_attempt_fingerprint
    if bounded_repair is not None:
        if not isinstance(bounded_repair, Mapping):
            raise PackageBuildError("Bounded repair evidence must be an object")
        chunk_index = bounded_repair.get("chunk_index")
        if (
            bounded_repair.get("schema_version")
            != "earnalism.google_english_bounded_chunk_repair.v1"
            or bounded_repair.get("status")
            != "PRIVATE_REPLACEMENT_CANDIDATE_QA_PENDING"
            or bounded_repair.get("slug") != slug
            or bounded_repair.get("source_sha256") != source_sha256
            or bounded_repair.get("input_manifest_sha256")
            != input_manifest_sha256
            or bounded_repair.get("base_attempt_fingerprint")
            != expected_attempt_fingerprint
            or not isinstance(chunk_index, int)
            or isinstance(chunk_index, bool)
            or not 0 <= chunk_index < len(records)
            or bounded_repair.get("unit_id") != records[chunk_index]["unit_id"]
            or bounded_repair.get("text_sha256")
            != records[chunk_index]["text_sha256"]
            or bounded_repair.get("changed_chunk_indexes") != [chunk_index]
            or bounded_repair.get("replacement_audio_file_count") != 1
            or bounded_repair.get("preserved_audio_file_count")
            != len(records) - 1
            or bounded_repair.get("full_source_text_changed") is not False
            or bounded_repair.get("publication_performed") is not False
            or bounded_repair.get("release_mutation_performed") is not False
            or bounded_repair.get("upload_performed") is not False
            or bounded_repair.get("candidate_audio_sequence_sha256")
            != sequence_sha256
            or manifest.get("candidate_audio_sequence_sha256")
            != sequence_sha256
            or manifest.get("repair_synthesis_calls") != 1
            or manifest.get("total_provider_calls_across_lineage")
            != len(records) + 1
        ):
            raise PackageBuildError(
                "Bounded repair lineage is incomplete or conflicts with the candidate"
            )
        for field in (
            "base_full_manifest_sha256",
            "base_candidate_binding_sha256",
            "failed_listening_evidence_sha256",
            "repair_attempt_fingerprint",
        ):
            if not SHA256_RE.fullmatch(str(bounded_repair.get(field) or "")):
                raise PackageBuildError(
                    f"Bounded repair {field} is not a SHA-256"
                )
        base_hashes = bounded_repair.get("base_ordered_audio_hashes")
        current_hashes = [record["audio_sha256"] for record in records]
        if (
            not isinstance(base_hashes, list)
            or len(base_hashes) != len(records)
            or any(
                not SHA256_RE.fullmatch(str(value or ""))
                for value in base_hashes
            )
            or [
                index
                for index, (base, current) in enumerate(
                    zip(base_hashes, current_hashes)
                )
                if base != current
            ]
            != [chunk_index]
            or bounded_repair.get("prior_audio_sha256")
            != base_hashes[chunk_index]
            or bounded_repair.get("replacement_audio_sha256")
            != current_hashes[chunk_index]
        ):
            raise PackageBuildError(
                "Bounded repair does not prove one exact changed audio unit"
            )
        objective_attempt_fingerprint = str(
            bounded_repair["repair_attempt_fingerprint"]
        )
    manifest_sha256 = sha256_file(path)
    candidate_binding_sha256 = canonical_sha256(
        {
            "manifest_sha256": manifest_sha256,
            "source_sha256": source_sha256,
            "input_manifest_sha256": input_manifest_sha256,
            "ordered_text_hashes": expected_unit_hashes,
            "ordered_audio_hashes": [
                record["audio_sha256"] for record in records
            ],
        }
    )
    return {
        "path": path,
        "sha256": manifest_sha256,
        "manifest": manifest,
        "run_dir": run_dir,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "input_manifest_path": input_manifest_path,
        "input_manifest_sha256": input_manifest_sha256,
        "input_manifest": input_manifest,
        "records": records,
        "candidate_audio_sequence_sha256": sequence_sha256,
        "candidate_binding_sha256": candidate_binding_sha256,
        "bounded_repair": bounded_repair,
        "objective_attempt_fingerprint": objective_attempt_fingerprint,
    }


def _strict_objective_metrics(
    value: Mapping[str, Any],
    *,
    label: str,
) -> None:
    _require_number(
        value.get("score"),
        f"{label} ASR/source score",
        QA_CANDIDATE_ASR_SCORE_MIN,
    )
    _require_number(
        value.get("coverage"),
        f"{label} ASR/source coverage",
        QA_CANDIDATE_COVERAGE_MIN,
    )
    _require_number(
        value.get("precision"),
        f"{label} ASR/source precision",
        QA_CANDIDATE_COVERAGE_MIN,
    )
    for field in (
        "first_words_match",
        "last_words_match",
        "ordered_content_integrity_pass",
        "no_missing_content",
        "no_duplicate_content",
        "no_reordered_content",
        "no_unexpected_content",
    ):
        if value.get(field) is not True:
            raise PackageBuildError(f"{label} does not prove {field}")
    token_counts = [
        value.get(field)
        for field in (
            "source_token_count",
            "transcript_token_count",
            "equal_token_count",
        )
    ]
    if (
        any(
            not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            for count in token_counts
        )
        or len(set(token_counts)) != 1
        or value.get("missing_tokens") != {}
        or value.get("duplicate_tokens") != {}
        or value.get("unexpected_tokens") != {}
        or value.get("ordered_alignment_operations") != []
    ):
        raise PackageBuildError(
            f"{label} does not prove exact normalized token identity"
        )


def _validate_candidate_objective_qa(
    objective_path: Path,
    *,
    full: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    path = objective_path.expanduser().resolve()
    if not path.is_file():
        raise PackageBuildError("Full audio-derived QA report is missing")
    report = read_json(path)
    if not isinstance(report, Mapping):
        raise PackageBuildError("Full audio-derived QA report must be an object")
    manifest = full["manifest"]
    if (
        report.get("schema_version") != GOOGLE_FULL_OBJECTIVE_SCHEMA
        or report.get("status")
        != "FULL_AUDIO_DERIVED_ASR_SYNC_PASS_PRIVATE_ONLY"
        or report.get("objective_pass") is not True
        or report.get("blockers") != []
        or report.get("next_stage") != "FULL_TITLE_LISTENING_QA_PRIVATE_ONLY"
        or report.get("slug") != manifest.get("slug")
        or report.get("title") != context["title"]
        or report.get("author") != context["author"]
        or report.get("provider") != "google"
        or report.get("voice") != manifest.get("voice")
        or report.get("language_code") != manifest.get("language_code")
        or report.get("full_manifest_sha256") != full["sha256"]
        or Path(str(report.get("full_manifest_path") or "")).expanduser().resolve()
        != full["path"]
        or report.get("source_sha256") != full["source_sha256"]
        or report.get("input_manifest_sha256")
        != full["input_manifest_sha256"]
        or report.get("attempt_fingerprint")
        != full["objective_attempt_fingerprint"]
        or report.get("candidate_audio_sequence_sha256")
        != full["candidate_audio_sequence_sha256"]
        or report.get("candidate_binding_sha256")
        != full["candidate_binding_sha256"]
        or report.get("private_output_only") is not True
        or report.get("public_release_approved") is not False
        or report.get("upload_performed") is not False
        or report.get("publication_performed") is not False
        or report.get("release_mutation_performed") is not False
        or report.get("paid_lock_read_or_written") is not False
    ):
        raise PackageBuildError(
            "Full audio-derived QA report is not exact, private, passing evidence"
        )
    asr = report.get("audio_derived_asr")
    asr_settings = asr.get("settings") if isinstance(asr, Mapping) else None
    if (
        not isinstance(asr, Mapping)
        or asr.get("status") != "PASS"
        or asr.get("source_blind") is not True
        or asr.get("audio_derived") is not True
        or asr.get("provider") != "local_openai_whisper"
        or asr.get("provider_calls_made") is not False
        or not isinstance(asr_settings, Mapping)
        or asr_settings.get("word_timestamps") is not True
        or asr_settings.get("initial_prompt") is not None
    ):
        raise PackageBuildError("Full audio-derived ASR does not pass")
    _require_number(
        asr.get("required_score"),
        "Declared full audio-derived ASR score gate",
        QA_CANDIDATE_ASR_SCORE_MIN,
    )
    _require_number(
        asr.get("required_coverage"),
        "Declared full audio-derived ASR coverage gate",
        QA_CANDIDATE_COVERAGE_MIN,
    )
    aggregate = asr.get("full_title_aggregate")
    if (
        not isinstance(aggregate, Mapping)
        or aggregate.get("pass") is not True
        or aggregate.get("audio_derived_asr_gate_pass") is not True
        or aggregate.get("audio_derived_asr_gate_blockers") != []
        or aggregate.get("frontmatter_absent") is not True
    ):
        raise PackageBuildError("Full-title ASR aggregate does not pass")
    _strict_objective_metrics(aggregate, label="Full-title aggregate")
    reports = asr.get("reports")
    records = full["records"]
    bounded_repair = full.get("bounded_repair")
    local_asr_run_count = asr.get("local_asr_run_count")
    reused_asr_report_count = asr.get("reused_local_asr_report_count", 0)
    if (
        not isinstance(reports, list)
        or len(reports) != len(records)
        or asr.get("chunk_count") != len(records)
        or not isinstance(local_asr_run_count, int)
        or isinstance(local_asr_run_count, bool)
        or not isinstance(reused_asr_report_count, int)
        or isinstance(reused_asr_report_count, bool)
        or local_asr_run_count < 0
        or reused_asr_report_count < 0
        or local_asr_run_count + reused_asr_report_count != len(records)
    ):
        raise PackageBuildError("Full audio-derived ASR chunk set is incomplete")
    if bounded_repair is None:
        if (
            local_asr_run_count != len(records)
            or reused_asr_report_count != 0
        ):
            raise PackageBuildError(
                "Non-repaired candidate cannot reuse ASR evidence"
            )
        expected_reused_unit_ids: list[str] = []
        expected_reuse_report_sha256s: list[str] = []
    else:
        changed_index = int(bounded_repair["chunk_index"])
        expected_reused_unit_ids = [
            record["unit_id"]
            for index, record in enumerate(records)
            if index != changed_index
        ]
        reuse_report_sha256s = asr.get("reused_report_sha256s")
        if (
            local_asr_run_count != 1
            or reused_asr_report_count != len(records) - 1
            or asr.get("reused_unit_ids") != expected_reused_unit_ids
            or not isinstance(reuse_report_sha256s, list)
            or len(reuse_report_sha256s) != 1
            or not SHA256_RE.fullmatch(
                str(reuse_report_sha256s[0] or "")
            )
        ):
            raise PackageBuildError(
                "Bounded repair ASR reuse counts or provenance are invalid"
            )
        expected_reuse_report_sha256s = [
            str(reuse_report_sha256s[0])
        ]

    word_timestamps: list[dict[str, Any]] = []
    raw_timestamp_rows: list[list[dict[str, Any]]] = []
    for index, (record, raw) in enumerate(zip(records, reports)):
        if not isinstance(raw, Mapping):
            raise PackageBuildError(f"Objective ASR row {index} is invalid")
        label = record["unit_id"]
        if (
            raw.get("index") != index
            or raw.get("unit_id") != label
            or raw.get("source_text_sha256") != record["text_sha256"]
            or raw.get("audio_sha256") != record["audio_sha256"]
            or raw.get("pass") is not True
            or raw.get("word_timestamp_evidence_valid") is not True
            or raw.get("word_timestamp_anomalies") != []
            or raw.get("frontmatter_absent") is not True
            or raw.get("audio_derived_asr_gate_pass") is not True
            or raw.get("audio_derived_asr_gate_blockers") != []
        ):
            raise PackageBuildError(f"Objective ASR binding fails at {label}")
        if bounded_repair is None:
            if (
                raw.get("asr_evidence_origin")
                not in (None, "local_source_blind_whisper")
                or raw.get("reused_from_report_sha256") is not None
            ):
                raise PackageBuildError(
                    f"Unexpected ASR reuse provenance at {label}"
                )
        else:
            changed_index = int(bounded_repair["chunk_index"])
            expected_origin = (
                "local_source_blind_whisper"
                if index == changed_index
                else "exact_prior_private_report"
            )
            expected_reuse_sha256 = (
                None
                if index == changed_index
                else expected_reuse_report_sha256s[0]
            )
            if (
                raw.get("asr_evidence_origin") != expected_origin
                or raw.get("reused_from_report_sha256")
                != expected_reuse_sha256
            ):
                raise PackageBuildError(
                    f"Bounded repair ASR provenance fails at {label}"
                )
        _strict_objective_metrics(raw, label=label)
        duration_seconds = _require_number(
            raw.get("duration_seconds"),
            f"{label} objective audio duration",
            0.000001,
        )
        if (
            abs(duration_seconds * 1000 - record["duration_ms"])
            > AUDIO_DURATION_TOLERANCE_SECONDS * 1000
        ):
            raise PackageBuildError(
                f"{label} objective duration does not match provider audio"
            )
        source_tokens = _lexical_tokens(record["source_text"])
        transcript = str(raw.get("transcript") or "").strip()
        transcript_tokens = _lexical_tokens(transcript)
        words = raw.get("audio_derived_word_timestamps")
        if (
            not source_tokens
            or len(transcript_tokens) != len(source_tokens)
            or not isinstance(words, list)
            or not words
            or raw.get("transcript_sha256")
            != hashlib.sha256(transcript.encode("utf-8")).hexdigest()
            or raw.get("word_timestamp_sha256") != canonical_sha256(words)
        ):
            raise PackageBuildError(
                f"{label} transcript does not map exactly to raw source tokens"
            )
        expanded_words: list[dict[str, Any]] = []
        validated_raw_words: list[dict[str, Any]] = []
        prior_local_end = 0.0
        for timestamp_index, word in enumerate(words):
            if not isinstance(word, Mapping):
                raise PackageBuildError(f"{label} word timestamp is invalid")
            try:
                local_start = float(word.get("start_seconds"))
                local_end = float(word.get("end_seconds"))
            except (TypeError, ValueError):
                raise PackageBuildError(
                    f"{label} word timestamp is invalid"
                ) from None
            if (
                not math.isfinite(local_start)
                or not math.isfinite(local_end)
                or local_start + 0.05 < prior_local_end
                or local_end <= local_start
                or local_end > record["duration_ms"] / 1000 + 0.05
            ):
                raise PackageBuildError(
                    f"{label} word timestamps are not audio-derived and monotonic"
                )
            timestamp_tokens = _lexical_tokens(str(word.get("word") or ""))
            group_id = f"{label}:timestamp-{timestamp_index:05d}"
            for transcript_token in timestamp_tokens:
                expanded_words.append(
                    {
                        "transcript_token": transcript_token,
                        "timestamp_group_id": group_id,
                        "start_seconds": None,
                        "end_seconds": None,
                        "local_start_seconds": round(local_start, 6),
                        "local_end_seconds": round(local_end, 6),
                        "unit_id": label,
                    }
                )
            validated_raw_words.append(dict(word))
            prior_local_end = local_end
        if (
            [row["transcript_token"] for row in expanded_words]
            != transcript_tokens
            or len(expanded_words) != len(source_tokens)
        ):
            raise PackageBuildError(
                f"{label} measured timestamps do not cover the raw transcript exactly"
            )
        for word_index, expanded_word in enumerate(expanded_words):
            word_timestamps.append(
                {
                    **expanded_word,
                    "source_token": source_tokens[word_index],
                }
            )
        raw_timestamp_rows.append(validated_raw_words)

    if bounded_repair is not None:
        qa_binding = {
            "schema_version": GOOGLE_FULL_OBJECTIVE_SCHEMA,
            "full_manifest_sha256": full["sha256"],
            "source_sha256": full["source_sha256"],
            "input_manifest_sha256": full["input_manifest_sha256"],
            "attempt_fingerprint": full["objective_attempt_fingerprint"],
            "candidate_audio_sequence_sha256": (
                full["candidate_audio_sequence_sha256"]
            ),
            "candidate_binding_sha256": full["candidate_binding_sha256"],
            "asr_model_sha256": asr.get("model_sha256"),
            "asr_settings": asr.get("settings"),
            "ordered_audio_hashes": [
                record["audio_sha256"] for record in records
            ],
            "ordered_transcript_hashes": [
                item.get("transcript_sha256") for item in reports
            ],
            "ordered_asr_evidence_origins": [
                item.get("asr_evidence_origin") for item in reports
            ],
            "ordered_reuse_report_sha256s": [
                item.get("reused_from_report_sha256") for item in reports
            ],
            "ordered_unit_evidence": [
                {
                    "index": item.get("index"),
                    "unit_id": item.get("unit_id"),
                    "source_text_sha256": item.get("source_text_sha256"),
                    "audio_sha256": item.get("audio_sha256"),
                    "duration_seconds": item.get("duration_seconds"),
                    "transcript_sha256": item.get("transcript_sha256"),
                    "word_timestamp_sha256": item.get(
                        "word_timestamp_sha256"
                    ),
                }
                for item in reports
            ],
        }
        if (
            not SHA256_RE.fullmatch(str(asr.get("model_sha256") or ""))
            or report.get("qa_binding_sha256")
            != canonical_sha256(qa_binding)
        ):
            raise PackageBuildError(
                "Bounded repair objective QA provenance hash is invalid"
            )

    sync = report.get("measured_sync")
    if not isinstance(sync, Mapping):
        raise PackageBuildError("Measured sync report is missing")
    sections = sync.get("sections")
    if (
        sync.get("status") != "PASS"
        or sync.get("sync_pass") is not True
        or sync.get("audio_derived_or_measured") is not True
        or sync.get("auto_estimated_sync") is not False
        or sync.get("public_word_level_sync_claim_allowed") is not False
        or str(sync.get("granularity") or "")
        != "measured_source_bound_section"
        or not isinstance(sections, list)
        or len(sections) != len(records)
        or sync.get("section_count") != len(records)
    ):
        raise PackageBuildError(
            "Measured sync is not complete audio-derived section evidence"
        )
    _require_number(
        sync.get("sync_score"),
        "Measured sync score",
        QA_CANDIDATE_ASR_SCORE_MIN,
    )
    _require_number(
        sync.get("coverage"),
        "Measured sync coverage",
        QA_CANDIDATE_COVERAGE_MIN,
    )
    word_cursor = 0
    prior_absolute_end = 0.0
    absolute_timestamp_rows: list[dict[str, Any]] = []
    for index, (record, section) in enumerate(zip(records, sections)):
        if not isinstance(section, Mapping):
            raise PackageBuildError(f"Measured section {index} is invalid")
        try:
            start = float(section.get("start_seconds"))
            end = float(section.get("end_seconds"))
            duration = float(section.get("duration_seconds"))
        except (TypeError, ValueError):
            raise PackageBuildError(
                f"Measured section {index} boundary is invalid"
            ) from None
        if (
            section.get("unit_id") != record["unit_id"]
            or section.get("source_text_sha256") != record["text_sha256"]
            or section.get("audio_sha256") != record["audio_sha256"]
            or section.get("binding_pass") is not True
            or section.get("contiguous_measured_interval") is not True
            or section.get("duration_binding_pass") is not True
            or abs(start - prior_absolute_end) > 0.001
            or abs((end - start) - duration) > 0.001
            or abs(duration * 1000 - record["duration_ms"])
            > AUDIO_DURATION_TOLERANCE_SECONDS * 1000
        ):
            raise PackageBuildError(
                f"Measured sync binding fails at {record['unit_id']}"
            )
        local_count = len(_lexical_tokens(record["source_text"]))
        for offset in range(local_count):
            word_timestamps[word_cursor + offset]["start_seconds"] = round(
                start
                + float(
                    word_timestamps[word_cursor + offset]["local_start_seconds"]
                ),
                6,
            )
            word_timestamps[word_cursor + offset]["end_seconds"] = round(
                start
                + float(
                    word_timestamps[word_cursor + offset]["local_end_seconds"]
                ),
                6,
            )
        expected_absolute_words = []
        for raw_word in raw_timestamp_rows[index]:
            expected_absolute_words.append(
                {
                    **raw_word,
                    "start_seconds": round(
                        start + float(raw_word["start_seconds"]),
                        6,
                    ),
                    "end_seconds": round(
                        start + float(raw_word["end_seconds"]),
                        6,
                    ),
                }
            )
        if section.get("audio_derived_word_timestamp_sha256") != canonical_sha256(
            raw_timestamp_rows[index]
        ):
            raise PackageBuildError(
                f"Measured timestamp hash fails at {record['unit_id']}"
            )
        report_absolute_words = reports[index].get(
            "absolute_audio_derived_word_timestamps"
        )
        if report_absolute_words != expected_absolute_words:
            raise PackageBuildError(
                f"Absolute measured timestamps fail at {record['unit_id']}"
            )
        absolute_timestamp_rows.extend(expected_absolute_words)
        word_cursor += local_count
        prior_absolute_end = end
    total_duration = _require_number(
        sync.get("total_measured_duration_seconds"),
        "Full candidate measured duration",
        0.000001,
    )
    if (
        abs(total_duration - prior_absolute_end) > 0.001
        or word_cursor != len(word_timestamps)
        or aggregate.get("audio_derived_word_timestamp_count")
        != len(absolute_timestamp_rows)
        or aggregate.get("audio_derived_word_timestamps_sha256")
        != canonical_sha256(absolute_timestamp_rows)
    ):
        raise PackageBuildError("Measured sync does not cover the full candidate")
    return {
        "path": path,
        "sha256": sha256_file(path),
        "report": report,
        "asr": asr,
        "sync": sync,
        "word_timestamps": word_timestamps,
        "duration_ms": round(total_duration * 1000),
    }


def _validate_listening_scores(
    scores: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field, minimum in QA_CANDIDATE_LISTENING_THRESHOLDS.items():
        _require_number(scores.get(field), f"{label} {field}", minimum)


def _validate_candidate_listening_qa(
    listening_path: Path,
    *,
    full: Mapping[str, Any],
    objective: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    path = listening_path.expanduser().resolve()
    if not path.is_file():
        raise PackageBuildError("Six-sample full-title listening QA is missing")
    report = read_json(path)
    if not isinstance(report, Mapping):
        raise PackageBuildError("Full-title listening QA must be an object")
    lock_sha256_before = str(report.get("paid_lock_sha256_before") or "")
    lock_sha256_after = str(report.get("paid_lock_sha256_after") or "")
    incremental = (
        report.get("schema_version")
        == JEKYLL_INCREMENTAL_LISTENING_SCHEMA
    )
    if (
        report.get("status") != "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY"
        or report.get("qa_schema_version")
        != GOOGLE_FULL_LISTENING_QA_SCHEMA_VERSION
        or report.get("slug") != full["manifest"].get("slug")
        or report.get("title") != context["title"]
        or report.get("author") != context["author"]
        or str(report.get("language") or "").strip().lower()
        not in {"en", "eng", "english"}
        or report.get("provider") != "google"
        or report.get("voice") != full["manifest"].get("voice")
        or report.get("full_manifest_sha256") != full["sha256"]
        or report.get("source_sha256") != full["source_sha256"]
        or report.get("input_manifest_sha256")
        != full["input_manifest_sha256"]
        or report.get("candidate_audio_sequence_sha256")
        != full["candidate_audio_sequence_sha256"]
        or report.get("candidate_binding_sha256")
        != full["candidate_binding_sha256"]
        or report.get("blockers") != []
        or report.get("private_output_only") is not True
        or report.get("public_release_approved") is not False
        or report.get("upload_performed") is not False
        or report.get("publication_performed") is not False
        or report.get("release_mutation_performed") is not False
        or report.get("provider_calls_ran") is not True
        or report.get("paid_lock_read_or_written") is not True
        or report.get("paid_lock_touched") is not True
        or report.get("paid_lock_restored_byte_for_byte") is not True
        or not SHA256_RE.fullmatch(lock_sha256_before)
        or lock_sha256_after != lock_sha256_before
    ):
        raise PackageBuildError(
            "Six-sample listening QA is not exact, private, passing evidence"
        )
    quality_report = report.get("listening_quality_report")
    if (
        not isinstance(quality_report, Mapping)
        or quality_report.get("qa_schema_version")
        != LISTENING_QA_SCHEMA_VERSION
        or quality_report.get("slug") != report.get("slug")
        or quality_report.get("title") != context["title"]
        or quality_report.get("author") != context["author"]
        or str(quality_report.get("language") or "").strip().lower()
        not in {"en", "eng", "english"}
        or quality_report.get("audio_hash")
        != full["candidate_audio_sequence_sha256"]
        or quality_report.get("candidate_binding_sha256")
        != full["candidate_binding_sha256"]
    ):
        raise PackageBuildError("Listening quality report binding is invalid")
    quality = quality_report.get("listening_quality")
    samples = quality.get("samples") if isinstance(quality, Mapping) else None
    aggregate = quality.get("aggregate") if isinstance(quality, Mapping) else None
    release_policy = str(quality_report.get("release_policy") or "")
    if (
        not isinstance(quality, Mapping)
        or quality.get("status") != "PASS"
        or quality.get("audio_hash") != full["candidate_audio_sequence_sha256"]
        or release_policy
        not in QA_CANDIDATE_ALLOWED_ENGLISH_LISTENING_POLICIES
        or quality.get("release_policy") != release_policy
        or quality.get("blockers") != []
        or quality.get("dialogue_emotional_sections_judged") is not True
        or not isinstance(samples, list)
        or len(samples) != 6
        or not isinstance(aggregate, Mapping)
    ):
        raise PackageBuildError("Listening quality report does not contain six passes")
    _validate_listening_scores(aggregate, label="Listening aggregate")
    records = {record["unit_id"]: record for record in full["records"]}
    seen_units: set[str] = set()
    for sample in samples:
        if not isinstance(sample, Mapping):
            raise PackageBuildError("Listening sample is invalid")
        unit_id = str(sample.get("unit_id") or "")
        record = records.get(unit_id)
        scores = sample.get("scores")
        flags = sample.get("judge_flags")
        if (
            not record
            or unit_id in seen_units
            or sample.get("sample_audio_hash") != record["audio_sha256"]
            or sample.get("source_text_sha256") != record["text_sha256"]
            or not isinstance(scores, Mapping)
            or not isinstance(flags, Mapping)
            or sample.get("frontmatter_present") is not False
            or str(sample.get("blocker_reason") or "").strip()
        ):
            raise PackageBuildError(
                f"Listening sample is not source/audio-bound: {unit_id}"
            )
        _validate_listening_scores(scores, label=f"Listening sample {unit_id}")
        if any(flags.get(flag) is not False for flag in QA_CANDIDATE_FATAL_FLAGS):
            raise PackageBuildError(
                f"Listening sample has fatal or missing flags: {unit_id}"
            )
        seen_units.add(unit_id)
    if any(quality.get(flag) is not False for flag in QA_CANDIDATE_FATAL_FLAGS):
        raise PackageBuildError("Listening aggregate has fatal or missing flags")
    prior_listening_path: Optional[Path] = None
    if incremental:
        bounded_repair = full.get("bounded_repair")
        if (
            full["manifest"].get("slug") != "jekyll-and-hyde"
            or not isinstance(bounded_repair, Mapping)
            or release_policy != "platform_audiobook_acceptance_v4_89"
            or report.get("active_release_policy") != release_policy
            or report.get("provider_call_count") != 1
            or report.get("reused_judgment_count") != 5
            or report.get("new_judgment_count") != 1
            or report.get("all_sample_judgments_hash_bound") is not True
            or report.get("audio_derived_objective_qa_sha256")
            != objective["sha256"]
            or report.get("audio_derived_objective_qa_path")
            != str(objective["path"])
        ):
            raise PackageBuildError(
                "Incremental Jekyll listening QA provenance is invalid"
            )
        prior_sha256 = str(
            report.get("prior_listening_report_sha256") or ""
        )
        prior_listening_path = Path(
            str(report.get("prior_listening_report_path") or "")
        ).expanduser().resolve()
        if (
            not prior_listening_path.is_file()
            or not SHA256_RE.fullmatch(prior_sha256)
            or sha256_file(prior_listening_path) != prior_sha256
            or prior_sha256
            != bounded_repair.get("failed_listening_evidence_sha256")
        ):
            raise PackageBuildError(
                "Incremental Jekyll prior listening report is missing or stale"
            )
        prior_report = read_json(prior_listening_path)
        prior_quality = (
            prior_report.get("listening_quality_report")
            if isinstance(prior_report, Mapping)
            else None
        )
        prior_listening = (
            prior_quality.get("listening_quality")
            if isinstance(prior_quality, Mapping)
            else None
        )
        prior_samples = (
            prior_listening.get("samples")
            if isinstance(prior_listening, Mapping)
            else None
        )
        if (
            prior_report.get("status") != "BLOCKED_LISTENING_QA"
            or prior_report.get("slug") != report.get("slug")
            or prior_report.get("candidate_binding_sha256")
            != bounded_repair.get("base_candidate_binding_sha256")
            or not isinstance(prior_samples, list)
            or len(prior_samples) != 6
        ):
            raise PackageBuildError(
                "Incremental Jekyll prior listening evidence is invalid"
            )
        prior_by_unit = {
            str(sample.get("unit_id") or ""): sample
            for sample in prior_samples
            if isinstance(sample, Mapping)
        }
        reused_samples = [
            sample
            for sample in samples
            if sample.get("judgment_reused") is True
        ]
        new_samples = [
            sample
            for sample in samples
            if sample.get("judgment_reused") is False
        ]
        reused_unit_ids = [str(sample["unit_id"]) for sample in reused_samples]
        new_unit_ids = [str(sample["unit_id"]) for sample in new_samples]
        if (
            len(reused_samples) != 5
            or len(new_samples) != 1
            or report.get("reused_judgment_unit_ids") != reused_unit_ids
            or report.get("new_judgment_unit_ids") != new_unit_ids
            or new_unit_ids != [str(bounded_repair.get("unit_id"))]
            or set(prior_by_unit) != seen_units
        ):
            raise PackageBuildError(
                "Incremental Jekyll listening reuse counts are invalid"
            )
        for sample in reused_samples:
            unit_id = str(sample["unit_id"])
            prior_sample = prior_by_unit.get(unit_id)
            if (
                not isinstance(prior_sample, Mapping)
                or sample.get("judgment_reuse_reason")
                != "SOURCE_AND_AUDIO_HASH_UNCHANGED"
                or sample.get("prior_listening_report_path")
                != str(prior_listening_path)
                or sample.get("prior_listening_report_sha256")
                != prior_sha256
                or sample.get("prior_candidate_binding_sha256")
                != bounded_repair.get("base_candidate_binding_sha256")
                or any(
                    sample.get(field) != prior_sample.get(field)
                    for field in (
                        "sample_audio_hash",
                        "source_text_sha256",
                        "scores",
                        "judge_flags",
                        "frontmatter_present",
                        "notes",
                        "blocker_reason",
                    )
                )
            ):
                raise PackageBuildError(
                    f"Incremental listening reuse was altered at {unit_id}"
                )
        new_sample = new_samples[0]
        if (
            new_sample.get("new_judgment_reason")
            != "REPLACEMENT_AUDIO_HASH_CHANGED"
            or new_sample.get("active_release_policy") != release_policy
            or new_sample.get("sample_audio_hash")
            == prior_by_unit[new_unit_ids[0]].get("sample_audio_hash")
        ):
            raise PackageBuildError(
                "Incremental Jekyll replacement judgment is not new"
            )
    elif report.get("provider_call_count") != 6:
        raise PackageBuildError(
            "Six-sample listening QA provider call count is invalid"
        )
    return {
        "path": path,
        "sha256": sha256_file(path),
        "report": report,
        "quality_report": quality_report,
        "release_policy": release_policy,
        "prior_listening_path": prior_listening_path,
        "minimum_scores": {
            field: float(aggregate[field])
            for field in QA_CANDIDATE_LISTENING_THRESHOLDS
        },
    }


def _controlled_candidate_hashes(
    context: Mapping[str, Any],
) -> dict[str, str]:
    directory = context["dirs"][0]
    filenames = (
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "approval_evidence.json",
        "checksum_manifest.json",
        "cover_approval_evidence.json",
    )
    return {filename: sha256_file(directory / filename) for filename in filenames}


def _validate_candidate_release_evidence(
    evidence_path: Path,
    *,
    full: Mapping[str, Any],
    objective: Mapping[str, Any],
    listening: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    path = evidence_path.expanduser().resolve()
    if not path.is_file():
        raise PackageBuildError("Explicit QA-candidate release evidence is missing")
    evidence = read_json(path)
    if not isinstance(evidence, Mapping):
        raise PackageBuildError("QA-candidate release evidence must be an object")
    controlled_hashes = _controlled_candidate_hashes(context)
    expected_downstream = list(QA_CANDIDATE_DOWNSTREAM_GATES)
    expected_fields = {
        "schema_version",
        "status",
        "slug",
        "title",
        "author",
        "controlled_source_sha256",
        "manuscript_sha256",
        "full_generation_manifest_sha256",
        "objective_qa_sha256",
        "listening_qa_sha256",
        "candidate_audio_sequence_sha256",
        "candidate_binding_sha256",
        "controlled_evidence_sha256",
        "controlled_chapter_sha256",
        "package_build_authorized",
        "public_release_authorized",
        "upload_authorized",
        "catalog_mutation_authorized",
        "downstream_release_gates_required",
        "release_evidence_version",
        "prepared_by",
        "generated_at",
    }
    if (
        set(evidence) != expected_fields
        or evidence.get("schema_version")
        != QA_CANDIDATE_RELEASE_EVIDENCE_SCHEMA
        or evidence.get("status") != "QA_CANDIDATE_PACKAGE_BUILD_AUTHORIZED"
        or evidence.get("slug") != full["manifest"].get("slug")
        or evidence.get("title") != context["title"]
        or evidence.get("author") != context["author"]
        or evidence.get("controlled_source_sha256")
        != context["controlled_source_sha256"]
        or evidence.get("manuscript_sha256") != full["source_sha256"]
        or evidence.get("full_generation_manifest_sha256") != full["sha256"]
        or evidence.get("objective_qa_sha256") != objective["sha256"]
        or evidence.get("listening_qa_sha256") != listening["sha256"]
        or evidence.get("candidate_audio_sequence_sha256")
        != full["candidate_audio_sequence_sha256"]
        or evidence.get("candidate_binding_sha256")
        != full["candidate_binding_sha256"]
        or evidence.get("controlled_evidence_sha256") != controlled_hashes
        or evidence.get("controlled_chapter_sha256")
        != context["chapter_material"]["chapter_sha256"]
        or evidence.get("package_build_authorized") is not True
        or evidence.get("public_release_authorized") is not False
        or evidence.get("upload_authorized") is not False
        or evidence.get("catalog_mutation_authorized") is not False
        or evidence.get("downstream_release_gates_required")
        != expected_downstream
        or not str(evidence.get("release_evidence_version") or "").strip()
        or not str(evidence.get("prepared_by") or "").strip()
        or not str(evidence.get("generated_at") or "").strip()
    ):
        raise PackageBuildError(
            "Explicit release evidence is stale, permissive, or not hash-bound"
        )
    return {
        "path": path,
        "sha256": sha256_file(path),
        "document": evidence,
        "controlled_hashes": controlled_hashes,
    }


def _measured_candidate_paragraphs(
    *,
    context: Mapping[str, Any],
    objective: Mapping[str, Any],
) -> list[dict[str, Any]]:
    words = objective["word_timestamps"]
    paragraph_defs: list[dict[str, Any]] = []
    word_cursor = 0
    paragraph_cursor = 0
    for chapter in context["chapter_material"]["chapters"]:
        chapter_start_word = word_cursor
        chapter_start_paragraph = paragraph_cursor
        for paragraph in chapter["paragraphs"]:
            token_count = len(_lexical_tokens(paragraph))
            paragraph_defs.append(
                {
                    "id": f"paragraph-{paragraph_cursor + 1:05d}",
                    "chapter_id": chapter["id"],
                    "chapter_order": chapter["order"],
                    "chapter_title": chapter["title"],
                    "index": paragraph_cursor,
                    "text": _collapsed_whitespace(paragraph),
                    "start_word": word_cursor,
                    "end_word": word_cursor + token_count - 1,
                }
            )
            word_cursor += token_count
            paragraph_cursor += 1
        chapter["start_word"] = chapter_start_word
        chapter["end_word"] = word_cursor - 1
        chapter["start_paragraph"] = chapter_start_paragraph
        chapter["end_paragraph"] = paragraph_cursor - 1
    if word_cursor != len(words) or not paragraph_defs:
        raise PackageBuildError(
            "Canonical paragraphs do not map to audio-derived word timestamps"
        )
    total_seconds = objective["duration_ms"] / 1000
    boundaries = [0.0]
    for paragraph in paragraph_defs[1:]:
        start_word = int(paragraph["start_word"])
        if (
            words[start_word - 1]["timestamp_group_id"]
            == words[start_word]["timestamp_group_id"]
        ):
            raise PackageBuildError(
                "A canonical paragraph boundary falls inside one measured "
                "timestamp group"
            )
        boundary = float(words[paragraph["start_word"]]["start_seconds"])
        if boundary <= boundaries[-1]:
            raise PackageBuildError(
                "Audio-derived paragraph boundaries are not monotonic"
            )
        boundaries.append(boundary)
    boundaries.append(total_seconds)
    for index, paragraph in enumerate(paragraph_defs):
        start = boundaries[index]
        end = boundaries[index + 1]
        if end <= start:
            raise PackageBuildError("Measured paragraph duration is not positive")
        paragraph["start"] = round(start, 6)
        paragraph["end"] = round(end, 6)
        paragraph["duration_seconds"] = round(end - start, 6)
        paragraph["granularity"] = "paragraph"
        paragraph["timing_origin"] = (
            "audio_derived_word_timestamps_to_exact_canonical_paragraph"
        )
    return paragraph_defs


def _candidate_segment_groups(
    *,
    chapters: list[dict[str, Any]],
    paragraphs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for chapter in chapters:
        remaining = [
            paragraph
            for paragraph in paragraphs
            if paragraph["chapter_id"] == chapter["id"]
        ]
        if not remaining:
            raise PackageBuildError(f"Chapter {chapter['id']} has no paragraphs")
        segment_index = 0
        while remaining:
            start = float(remaining[0]["start"])
            allowed = [
                index
                for index, paragraph in enumerate(remaining)
                if float(paragraph["end"]) - start <= MAX_SEGMENT_SECONDS + 0.001
            ]
            if not allowed:
                raise PackageBuildError(
                    "A canonical paragraph exceeds the 12-minute segment maximum"
                )
            choices: list[tuple[float, int]] = []
            for index in allowed:
                end = float(remaining[index]["end"])
                tail = float(remaining[-1]["end"]) - end
                if tail and tail < MIN_TARGET_SEGMENT_SECONDS:
                    continue
                choices.append((abs((end - start) - TARGET_SEGMENT_SECONDS), index))
            if not choices:
                choices = [
                    (
                        abs(
                            (float(remaining[index]["end"]) - start)
                            - TARGET_SEGMENT_SECONDS
                        ),
                        index,
                    )
                    for index in allowed
                ]
            selected_index = min(choices)[1]
            selected = remaining[: selected_index + 1]
            segment_index += 1
            groups.append(
                {
                    "chapter": chapter,
                    "chapter_segment_index": segment_index,
                    "start": start,
                    "end": float(selected[-1]["end"]),
                    "paragraphs": selected,
                }
            )
            remaining = remaining[selected_index + 1 :]
    _validate_segment_source_coverage(
        groups,
        duration_seconds=float(paragraphs[-1]["end"]),
    )
    return groups


def _write_concat_list(path: Path, sources: Iterable[Path]) -> None:
    lines: list[str] = []
    for source in sources:
        escaped = str(source.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_qa_candidate(
    *,
    repo_root: Path,
    slug: str,
    full_manifest_path: Path,
    objective_qa_path: Path,
    listening_qa_path: Path,
    release_evidence_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    context = _load_qa_candidate_publication(repo_root.resolve(), slug)
    full = _validate_candidate_full_manifest(
        full_manifest_path,
        context=context,
        slug=slug,
    )
    objective = _validate_candidate_objective_qa(
        objective_qa_path,
        full=full,
        context=context,
    )
    listening = _validate_candidate_listening_qa(
        listening_qa_path,
        full=full,
        objective=objective,
        context=context,
    )
    release_evidence = _validate_candidate_release_evidence(
        release_evidence_path,
        full=full,
        objective=objective,
        listening=listening,
        context=context,
    )
    paragraphs = _measured_candidate_paragraphs(
        context=context,
        objective=objective,
    )
    chapters = context["chapter_material"]["chapters"]
    groups = _candidate_segment_groups(
        chapters=chapters,
        paragraphs=paragraphs,
    )

    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PackageBuildError(f"Output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    masters_dir = output_dir / "masters"
    provider_dir = output_dir / "provenance/provider/audio"
    evidence_dir = output_dir / "provenance/evidence"
    controlled_dir = output_dir / "provenance/controlled"

    provider_copies: list[dict[str, Any]] = []
    for record in full["records"]:
        destination = (
            provider_dir
            / f"{record['unit_id']}-sha256-{record['audio_sha256']}.mp3"
        )
        copied = _copy_exact(
            record["audio_path"],
            destination,
            record["audio_sha256"],
        )
        provider_copies.append({**record, "copied_path": copied})

    evidence_sources = {
        "full_generation_manifest": full["path"],
        "full_audio_derived_qa": objective["path"],
        "full_listening_qa": listening["path"],
        "release_evidence": release_evidence["path"],
        "sanitized_source": full["source_path"],
        "input_manifest": full["input_manifest_path"],
    }
    if listening["prior_listening_path"] is not None:
        evidence_sources["prior_listening_qa"] = listening[
            "prior_listening_path"
        ]
    evidence_copies = {
        name: _copy_exact(
            source,
            evidence_dir / source.name,
            sha256_file(source),
        )
        for name, source in evidence_sources.items()
    }
    controlled_sources = {
        "public_book": context["dirs"][0] / "public_book.json",
        "reader_manifest": context["dirs"][0] / "reader_manifest.json",
        "source_evidence": context["dirs"][0] / "source_evidence.json",
        "approval_evidence": context["dirs"][0] / "approval_evidence.json",
        "checksum_manifest": context["dirs"][0] / "checksum_manifest.json",
        "cover_approval_evidence": context["cover_context"]["path"],
    }
    for chapter in chapters:
        controlled_sources[f"chapter_{chapter['order']:03d}"] = chapter["path"]
    controlled_copies = {
        name: _copy_exact(
            source,
            controlled_dir / source.name
            if not name.startswith("chapter_")
            else controlled_dir / "chapters" / source.name,
            sha256_file(source),
        )
        for name, source in controlled_sources.items()
    }

    concat_path = output_dir / ".private-provider-concat.txt"
    _write_concat_list(
        concat_path,
        [record["copied_path"] for record in provider_copies],
    )
    pcm_master = masters_dir / "candidate-pcm-master.wav"
    pcm_master.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_checked(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
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
    finally:
        concat_path.unlink(missing_ok=True)
    if not pcm_master.is_file() or pcm_master.stat().st_size <= 0:
        raise PackageBuildError("Candidate PCM master was not created")
    master_duration_ms = ffprobe_duration_ms(pcm_master)
    if (
        abs(master_duration_ms - objective["duration_ms"])
        > AUDIO_DURATION_TOLERANCE_SECONDS * 1000
    ):
        raise PackageBuildError(
            "Candidate PCM master duration does not match measured source audio"
        )

    word_cursor = 0
    paragraph_cursor = 0
    cumulative_ms = 0
    segment_assets: list[dict[str, Any]] = []
    track_rows: list[dict[str, Any]] = []
    for chapter_order, chapter in enumerate(chapters):
        chapter_groups = [
            group for group in groups if group["chapter"]["id"] == chapter["id"]
        ]
        track_start_word = word_cursor
        track_start_paragraph = paragraph_cursor
        chunks: list[dict[str, Any]] = []
        for group in chapter_groups:
            segment_id = (
                f"c{chapter_order + 1:03d}-"
                f"s{group['chapter_segment_index']:03d}"
            )
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
                    str(pcm_master),
                    "-map",
                    "0:a:0",
                    "-map_metadata",
                    "-1",
                    "-af",
                    (
                        f"atrim=start={group['start']:.6f}:end={group['end']:.6f},"
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
                group["paragraphs"],
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
                    "sync_granularity": "paragraph",
                    "sync_method": (
                        "audio_derived_word_timestamps_to_exact_canonical_paragraph"
                    ),
                    "alignment_method": (
                        "audio_derived_word_timestamps_to_exact_canonical_paragraph"
                    ),
                    "auto_estimated_sync": False,
                    "source_audio_sequence_sha256": full[
                        "candidate_audio_sequence_sha256"
                    ],
                    "source_text_sha256": full["source_sha256"],
                    "cues": local_cues,
                },
            )
            write_vtt(vtt_output, local_cues)
            word_count = sum(
                paragraph["end_word"] - paragraph["start_word"] + 1
                for paragraph in group["paragraphs"]
            )
            paragraph_count = len(group["paragraphs"])
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
                    "boundary_index_space": "exact_canonical_narration_text",
                    "reader_alignment_mode": "paragraph",
                    "highlight_sync_enabled": False,
                    "start_word": word_cursor,
                    "end_word": end_word,
                    "start_paragraph": paragraph_cursor,
                    "end_paragraph": end_paragraph,
                    "cumulative_start_ms": cumulative_ms,
                    "duration_ms": duration_ms,
                    "source_audio_sequence_sha256": full[
                        "candidate_audio_sequence_sha256"
                    ],
                    "delivery_profile": "mp3-96k-mono-48khz",
                    "narration_regenerated": False,
                    "measured_source_start_seconds": round(group["start"], 6),
                    "measured_source_end_seconds": round(group["end"], 6),
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
        source_duration_ms=objective["duration_ms"],
        encoded_duration_ms=cumulative_ms,
    )
    if (
        word_cursor != len(objective["word_timestamps"])
        or paragraph_cursor != len(paragraphs)
    ):
        raise PackageBuildError("Package semantic ranges do not cover the manuscript")

    evidence_paths = {
        f"{name}{path.suffix}": path
        for name, path in evidence_copies.items()
    }
    evidence_paths.update(
        {
            f"controlled.{name}.json": path
            for name, path in controlled_copies.items()
        }
    )
    evidence_sha256 = {
        name: sha256_file(path) for name, path in evidence_paths.items()
    }
    release_candidate_evidence = {
        "status": "PASS",
        "all_pre_storage_release_gates_passed": True,
        "gate_policy": "qa_candidate_package_build.v1",
        "gates": {
            "reader_truth": "PASS",
            "source_content_toc": "PASS",
            "rights_tier": "A",
            "language": context["language"],
            "listening_policy": listening["release_policy"],
            "covers": context["cover_context"]["covers"],
            "asr_score": float(
                objective["asr"]["full_title_aggregate"]["score"]
            ),
            "source_coverage": float(
                objective["asr"]["full_title_aggregate"]["coverage"]
            ),
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_integrity": True,
            "listening_minimum_scores": listening["minimum_scores"],
            "listening_sample_count": 6,
            "fatal_flags": [],
            "sync_tier": "PARAGRAPH_OR_SECTION_SYNC_PREMIUM",
            "auto_estimated_sync": False,
        },
        "full_generation_manifest_sha256": full["sha256"],
        "objective_qa_sha256": objective["sha256"],
        "listening_qa_sha256": listening["sha256"],
        "package_build_authorization_sha256": release_evidence["sha256"],
    }
    release_descriptor = {
        "schema_version": "audiobook_release_descriptor.v1",
        "slug": slug,
        "title": context["title"],
        "author": context["author"],
        "controlled_source_sha256": context["controlled_source_sha256"],
        "manuscript_sha256": full["source_sha256"],
        "narration_text_sha256": full["source_sha256"],
        "source_audio_identity": {
            "kind": "ordered_provider_chunks",
            "provider": "google",
            "sequence_sha256": full["candidate_audio_sequence_sha256"],
            "chunk_count": len(provider_copies),
            "ordered_sha256": [
                record["audio_sha256"] for record in provider_copies
            ],
        },
        "provider": "google",
        "voice": str(full["manifest"].get("voice") or ""),
        "model": "Google Cloud Text-to-Speech",
        "speaking_rate": full["manifest"].get("speaking_rate"),
        "pitch": full["manifest"].get("pitch"),
        "delivery_profile": "mp3-96k-mono-48khz",
        "provider_source_files_unchanged": True,
        "segment_boundaries_seconds": [
            round(groups[0]["start"], 6),
            *[round(group["end"], 6) for group in groups],
        ],
        "segment_target_seconds": {
            "minimum": MIN_TARGET_SEGMENT_SECONDS,
            "preferred": TARGET_SEGMENT_SECONDS,
            "maximum": MAX_SEGMENT_SECONDS,
        },
        "sync_tier": "paragraph",
        "highlight_sync_enabled": False,
        "evidence_sha256": evidence_sha256,
        "release_candidate_status": "QA_PASSED_STORAGE_PENDING",
        "release_candidate_evidence": release_candidate_evidence,
        "known_release_blockers": list(QA_CANDIDATE_DOWNSTREAM_GATES),
    }
    release_descriptor_sha256 = canonical_sha256(release_descriptor)
    descriptor_path = output_dir / "release-descriptor.json"
    write_json(descriptor_path, release_descriptor)
    if canonical_sha256(read_json(descriptor_path)) != release_descriptor_sha256:
        raise PackageBuildError("Release descriptor changed while writing")
    prefix = immutable_release_prefix(slug, release_descriptor_sha256)

    plan_assets: list[dict[str, Any]] = [
        file_asset(
            asset_id="master.pcm",
            path=pcm_master,
            key=(
                f"{prefix}masters/candidate-pcm-master-sha256-"
                f"{sha256_file(pcm_master)}.wav"
            ),
            mime_type="audio/wav",
        ),
        file_asset(
            asset_id="release.descriptor",
            path=descriptor_path,
            key=f"{prefix}release-descriptor.json",
            mime_type="application/json",
        ),
    ]
    for record in provider_copies:
        plan_assets.append(
            file_asset(
                asset_id=f"provenance.provider.{record['unit_id']}",
                path=record["copied_path"],
                key=(
                    f"{prefix}provenance/provider/audio/"
                    f"{record['copied_path'].name}"
                ),
                mime_type="audio/mpeg",
            )
        )
    for name, path in evidence_copies.items():
        plan_assets.append(
            file_asset(
                asset_id=f"provenance.evidence.{name}",
                path=path,
                key=f"{prefix}provenance/evidence/{path.name}",
                mime_type=(
                    "text/plain"
                    if path.suffix.lower() == ".txt"
                    else "application/json"
                ),
            )
        )
    for name, path in controlled_copies.items():
        plan_assets.append(
            file_asset(
                asset_id=f"provenance.controlled.{name}",
                path=path,
                key=(
                    f"{prefix}provenance/controlled/"
                    f"{'chapters/' if name.startswith('chapter_') else ''}"
                    f"{path.name}"
                ),
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
        "release_evidence_version": release_evidence["document"][
            "release_evidence_version"
        ],
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_sha256": context["controlled_source_sha256"],
        "manuscript_sha256": full["source_sha256"],
        "duration_ms": cumulative_ms,
        "segment_count": len(segment_assets),
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "sync_tier": "paragraph",
        "highlight_sync_enabled": False,
        "tracks": track_rows,
    }
    semantics_path = output_dir / "package-semantics.json"
    write_json(semantics_path, semantics)
    result = {
        "status": "QA_CANDIDATE_PACKAGE_BUILT",
        "slug": slug,
        "output_dir": str(output_dir),
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_audio_sequence_sha256": full[
            "candidate_audio_sequence_sha256"
        ],
        "source_sha256": context["controlled_source_sha256"],
        "manuscript_sha256": full["source_sha256"],
        "duration_ms": cumulative_ms,
        "chapter_count": len(track_rows),
        "segment_count": len(segment_assets),
        "word_count": word_cursor,
        "paragraph_count": paragraph_cursor,
        "asset_count": len(plan_assets),
        "upload_plan": str(upload_plan_path),
        "package_semantics": str(semantics_path),
        "release_status": "RELEASE_CANDIDATE",
        "public_release_approved": False,
        "upload_performed": False,
        "catalog_mutation_performed": False,
        "release_blockers": list(QA_CANDIDATE_DOWNSTREAM_GATES),
    }
    write_json(output_dir / "build-result.json", result)
    return result


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
    normalization_result = validated.get("normalization_result")
    package_sync_granularity = (
        "section"
        if isinstance(normalization_result, Mapping)
        else "paragraph_or_stanza"
    )
    if isinstance(normalization_result, Mapping):
        controlled_sources["normalization_release_evidence"] = normalization_result[
            "release_evidence_path"
        ]
        if normalization_result.get("narrated_manuscript_path") is not None:
            controlled_sources["narrated_manuscript"] = normalization_result[
                "narrated_manuscript_path"
            ]
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
                    "sync_granularity": package_sync_granularity,
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
                    "reader_alignment_mode": package_sync_granularity,
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
    if "normalization_release_evidence" in controlled_copies:
        evidence_paths["normalization_release_evidence.json"] = controlled_copies[
            "normalization_release_evidence"
        ]
    if "narrated_manuscript" in controlled_copies:
        evidence_paths["narrated_manuscript.txt"] = controlled_copies[
            "narrated_manuscript"
        ]
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
    if "normalization_release_evidence.json" in evidence_sha256:
        release_candidate_evidence[
            "normalization_release_evidence_sha256"
        ] = evidence_sha256["normalization_release_evidence.json"]
    if "narrated_manuscript.txt" in evidence_sha256:
        release_candidate_evidence["narrated_manuscript_sha256"] = evidence_sha256[
            "narrated_manuscript.txt"
        ]
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
        "sync_tier": package_sync_granularity,
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
                mime_type=(
                    "text/plain"
                    if name == "narrated_manuscript"
                    else "application/json"
                ),
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
        "sync_tier": package_sync_granularity,
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

    qa_candidate = subparsers.add_parser(
        "build-qa-candidate",
        help=(
            "Build a private new-title release candidate from exact Google "
            "full-generation, objective-QA, six-sample listening, controlled "
            "truth, and package-build authorization evidence"
        ),
    )
    qa_candidate.add_argument("--repo-root", type=Path, default=ROOT)
    qa_candidate.add_argument("--slug", required=True)
    qa_candidate.add_argument("--full-manifest", type=Path, required=True)
    qa_candidate.add_argument("--objective-qa", type=Path, required=True)
    qa_candidate.add_argument("--listening-qa", type=Path, required=True)
    qa_candidate.add_argument("--release-evidence", type=Path, required=True)
    qa_candidate.add_argument("--output-dir", type=Path, required=True)

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
        elif args.command == "build-qa-candidate":
            result = build_qa_candidate(
                repo_root=args.repo_root.resolve(),
                slug=args.slug,
                full_manifest_path=args.full_manifest,
                objective_qa_path=args.objective_qa,
                listening_qa_path=args.listening_qa,
                release_evidence_path=args.release_evidence,
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
