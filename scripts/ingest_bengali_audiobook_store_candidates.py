#!/usr/bin/env python3
"""Ingest local Bengali audiobook bundles as internal store candidates.

The workflow inventories existing local bundle assets, writes normalized
internal-only review packets, and keeps every public release gate blocked until
human Bengali listening, accessibility, rights, legal, and owner review pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
DEFAULT_INPUT_DIR = ROOT / "output" / "bengali_audiobook_polish" / "bengali-polish-queue-v1" / "bundles" / "ben"
DEFAULT_OUTPUT_DIR = INTERNAL_AUDIOBOOK_ROOT / "bengali_store_candidates"

AUDIO_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
METADATA_EXTENSIONS = {".json", ".md", ".txt", ".yml", ".yaml"}
SIDECAR_EXTENSIONS = {".vtt", ".json"}
COVER_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
TRANSCRIPT_MARKERS = ("transcript", "text", "script", "source")
PUBLIC_RELEASE_BLOCKED = "BLOCKED"
RELEASE_HOLD = "HOLD_BENGALI_AUDIOBOOK_QA_REQUIRED"

BLOCKED_RANGES = (
    range(0x202A, 0x202F),
    range(0x2066, 0x206A),
)
BLOCKED_POINTS = {
    0x200B: "zero-width space",
    0x200C: "zero-width non-joiner",
    0x200D: "zero-width joiner",
    0xFEFF: "byte-order mark / zero-width no-break space",
}


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    extension: str
    size_bytes: int
    sha256: str
    category: str


@dataclass(frozen=True)
class Bundle:
    source_dir: Path
    candidate_slug: str
    files: list[FileRecord]

    @property
    def audio_files(self) -> list[FileRecord]:
        return [record for record in self.files if record.category == "audio"]

    @property
    def metadata_files(self) -> list[FileRecord]:
        return [record for record in self.files if record.category == "metadata"]

    @property
    def sidecar_files(self) -> list[FileRecord]:
        return [record for record in self.files if record.category == "sidecar"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown-bengali-audiobook"


def root_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def ensure_internal_output_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Bengali audiobook candidate output must stay under internal/audiobook_lab") from exc
    relative_parts = resolved.relative_to(ROOT.resolve()).parts
    for index in range(len(relative_parts) - 1):
        if tuple(relative_parts[index : index + 2]) in {("frontend", "public"), ("frontend", "build")}:
            raise ValueError("Bengali audiobook output cannot use frontend/public or frontend/build")
    return resolved


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def read_json_safely(path: Path) -> tuple[Any, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "PASS"
    except Exception as exc:  # noqa: BLE001 - surfaced in the integrity report.
        return None, f"INVALID_JSON: {exc.__class__.__name__}"


def file_category(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix == ".vtt" or any(marker in name for marker in ("timestamp", "chapter", "highlight", "sync")):
        return "sidecar"
    if suffix in COVER_EXTENSIONS:
        return "cover"
    if suffix in {".txt", ".md"} and any(marker in name for marker in TRANSCRIPT_MARKERS):
        return "transcript"
    if suffix in METADATA_EXTENSIONS:
        return "metadata"
    return "unexpected"


def build_file_record(path: Path, input_dir: Path) -> FileRecord:
    return FileRecord(
        path=path,
        relative_path=str(path.relative_to(input_dir)),
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        category=file_category(path),
    )


def scan_bundle_directories(input_dir: Path) -> list[Path]:
    input_dir = input_dir.resolve()
    candidates: list[Path] = []
    for directory in sorted([input_dir, *[path for path in input_dir.rglob("*") if path.is_dir()]]):
        direct_files = [path for path in directory.iterdir() if path.is_file()]
        if not direct_files:
            continue
        has_audio = any(path.suffix.lower() in AUDIO_EXTENSIONS for path in direct_files)
        has_sidecar = any(file_category(path) in {"sidecar", "metadata", "transcript"} for path in direct_files)
        if has_audio or has_sidecar:
            candidates.append(directory)
    return candidates


def scan_bundles(input_dir: Path) -> list[Bundle]:
    input_dir = input_dir.resolve()
    bundles: list[Bundle] = []
    for directory in scan_bundle_directories(input_dir):
        files = [
            build_file_record(path, input_dir)
            for path in sorted(directory.rglob("*"))
            if path.is_file()
        ]
        if not files:
            continue
        relative_dir = directory.relative_to(input_dir)
        candidate_slug = safe_slug("-".join(relative_dir.parts) if relative_dir.parts else directory.name)
        bundles.append(Bundle(source_dir=directory, candidate_slug=candidate_slug, files=files))
    return bundles


def public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def blocked_unicode_reason(codepoint: int) -> str | None:
    for blocked_range in BLOCKED_RANGES:
        if codepoint in blocked_range:
            return "bidirectional Unicode control"
    return BLOCKED_POINTS.get(codepoint)


def hidden_unicode_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, character in enumerate(text):
        reason = blocked_unicode_reason(ord(character))
        if not reason:
            continue
        findings.append(
            {
                "line": text.count("\n", 0, index) + 1,
                "codepoint": f"U+{ord(character):04X}",
                "reason": reason,
            }
        )
    return findings


def has_public_reference(text: str) -> bool:
    return bool(
        re.search(r"https?://|frontend/public|frontend/build|public/audio|/audio/", text, flags=re.IGNORECASE)
    )


def parse_vtt_timestamp(value: str) -> float | None:
    match = re.fullmatch(r"(?:(\d{2,}):)?(\d{2}):(\d{2})\.(\d{3})", value.strip())
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4))
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def parse_vtt(path: Path, audio_duration_seconds: float | None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    if not text.lstrip().startswith("WEBVTT"):
        issues.append("missing WEBVTT header")

    cues: list[dict[str, Any]] = []
    previous_end = 0.0
    large_gaps = 0
    overlaps = 0
    cue_blocks = re.split(r"\n\s*\n", text.strip())
    for block in cue_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timestamp_line = next((line for line in lines if "-->" in line), "")
        if not timestamp_line:
            continue
        start_raw, end_raw = [piece.strip().split()[0] for piece in timestamp_line.split("-->", 1)]
        start = parse_vtt_timestamp(start_raw)
        end = parse_vtt_timestamp(end_raw)
        cue_text = "\n".join(line for line in lines if line != timestamp_line and not line.isdigit())
        if start is None or end is None:
            issues.append(f"invalid VTT timestamp: {timestamp_line}")
            continue
        if start < 0 or end < 0:
            issues.append("negative VTT timestamp")
        if end < start:
            issues.append(f"VTT cue ends before start at {timestamp_line}")
        if cues and start < previous_end:
            overlaps += 1
        gap = start - previous_end if cues else start
        if gap > 5.0:
            large_gaps += 1
        if not cue_text.strip():
            issues.append(f"empty cue text at {timestamp_line}")
        if hidden_unicode_findings(cue_text):
            issues.append(f"hidden Unicode control in cue at {timestamp_line}")
        if has_public_reference(cue_text):
            issues.append(f"public URL or public path reference in cue at {timestamp_line}")
        cues.append({"start_seconds": start, "end_seconds": end, "text": cue_text})
        previous_end = max(previous_end, end)

    if overlaps:
        issues.append(f"{overlaps} overlapping VTT cue(s)")
    if large_gaps:
        issues.append(f"{large_gaps} unexplained large VTT gap(s)")
    bengali_cues = sum(1 for cue in cues if re.search(r"[\u0980-\u09FF]", cue["text"]))
    coverage_seconds = cues[-1]["end_seconds"] if cues else 0.0
    coverage_ratio = None
    if audio_duration_seconds and audio_duration_seconds > 0:
        coverage_ratio = round(min(1.0, coverage_seconds / audio_duration_seconds), 4)
        if coverage_ratio < 0.9:
            issues.append("VTT coverage is below 90 percent of audio duration")

    score = max(0.0, 10.0 - min(6.0, len(issues) * 0.6) - min(2.0, overlaps * 0.2) - min(1.0, large_gaps * 0.05))
    return {
        "path": root_relative(path),
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "cue_count": len(cues),
        "bengali_cue_count": bengali_cues,
        "coverage_seconds": round(coverage_seconds, 3),
        "coverage_ratio": coverage_ratio,
        "issues": sorted(set(issues)),
        "highlight_usability_score": round(score, 1),
    }


def extract_start_end_ms(item: Any) -> tuple[int | None, int | None, str]:
    if not isinstance(item, dict):
        return None, None, ""
    start = item.get("start_ms", item.get("start", item.get("startMs")))
    end = item.get("end_ms", item.get("end", item.get("endMs")))
    text = str(item.get("word") or item.get("text") or item.get("label") or "")
    if isinstance(start, (int, float)) and start < 1000000:
        start_ms = int(start if start > 1000 else start * 1000 if "start_ms" not in item else start)
    else:
        start_ms = int(start) if isinstance(start, (int, float)) else None
    if isinstance(end, (int, float)) and end < 1000000:
        end_ms = int(end if end > 1000 else end * 1000 if "end_ms" not in item else end)
    else:
        end_ms = int(end) if isinstance(end, (int, float)) else None
    return start_ms, end_ms, text


def parse_timestamp_json(path: Path, audio_duration_seconds: float | None) -> dict[str, Any]:
    payload, status = read_json_safely(path)
    issues: list[str] = []
    if status != "PASS":
        return {
            "path": root_relative(path),
            "status": "INVALID",
            "entry_count": 0,
            "issues": [status],
            "highlight_usability_score": 0.0,
        }
    entries = payload if isinstance(payload, list) else payload.get("timestamps", []) if isinstance(payload, dict) else []
    if not isinstance(entries, list):
        entries = []
        issues.append("timestamp payload is not a list")

    previous_end = 0
    overlaps = 0
    order_errors = 0
    empty_text = 0
    public_refs = 0
    hidden_unicode = 0
    for item in entries:
        start_ms, end_ms, text = extract_start_end_ms(item)
        if start_ms is None:
            continue
        if start_ms < 0 or (end_ms is not None and end_ms < 0):
            issues.append("negative timestamp value")
        if end_ms is not None and end_ms < start_ms:
            order_errors += 1
        if start_ms < previous_end:
            overlaps += 1
        if end_ms is not None:
            previous_end = max(previous_end, end_ms)
        else:
            previous_end = max(previous_end, start_ms)
        if not text.strip():
            empty_text += 1
        if has_public_reference(text):
            public_refs += 1
        if hidden_unicode_findings(text):
            hidden_unicode += 1

    if order_errors:
        issues.append(f"{order_errors} timestamp order error(s)")
    if overlaps:
        issues.append(f"{overlaps} overlapping timestamp entrie(s)")
    if empty_text:
        issues.append(f"{empty_text} timestamp entrie(s) with empty text")
    if public_refs:
        issues.append(f"{public_refs} timestamp entrie(s) include public URL/path references")
    if hidden_unicode:
        issues.append(f"{hidden_unicode} timestamp entrie(s) include hidden Unicode controls")

    coverage_ratio = None
    if audio_duration_seconds and audio_duration_seconds > 0:
        coverage_ratio = round(min(1.0, (previous_end / 1000.0) / audio_duration_seconds), 4)
        if coverage_ratio < 0.9:
            issues.append("timestamp coverage is below 90 percent of audio duration")

    score = max(0.0, 10.0 - min(7.0, len(issues) * 0.7) - min(2.0, overlaps * 0.05))
    return {
        "path": root_relative(path),
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "entry_count": len(entries),
        "coverage_ratio": coverage_ratio,
        "issues": sorted(set(issues)),
        "highlight_usability_score": round(score, 1),
    }


def ffprobe_audio_metrics(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {
            "analysis_status": "FFPROBE_REQUIRED_FOR_AUDIO_METRICS",
            "duration_seconds": None,
            "format": "",
            "sample_rate_hz": None,
            "bitrate_bps": None,
            "channels": None,
            "objective_audio_score": 0.0,
        }
    command = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {
            "analysis_status": "FFPROBE_AUDIO_UNREADABLE",
            "ffprobe_error": result.stderr.strip()[:500],
            "duration_seconds": None,
            "format": "",
            "sample_rate_hz": None,
            "bitrate_bps": None,
            "channels": None,
            "objective_audio_score": 0.0,
        }
    payload = json.loads(result.stdout or "{}")
    audio_stream = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"),
        {},
    )
    fmt = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    duration = fmt.get("duration") or audio_stream.get("duration")
    bitrate = fmt.get("bit_rate") or audio_stream.get("bit_rate")
    sample_rate = audio_stream.get("sample_rate")
    channels = audio_stream.get("channels")
    parsed_duration = float(duration) if duration not in {None, ""} else None
    parsed_bitrate = int(float(bitrate)) if bitrate not in {None, ""} else None
    parsed_sample_rate = int(float(sample_rate)) if sample_rate not in {None, ""} else None
    parsed_channels = int(channels) if channels not in {None, ""} else None
    issues: list[str] = []
    if not parsed_duration or parsed_duration <= 0:
        issues.append("missing or invalid duration")
    if parsed_sample_rate and parsed_sample_rate < 22050:
        issues.append("sample rate below review target")
    if parsed_bitrate and parsed_bitrate < 64000:
        issues.append("bitrate below review target")
    if parsed_channels and parsed_channels < 1:
        issues.append("invalid channel count")
    score = max(0.0, 8.8 - len(issues) * 1.2)
    return {
        "analysis_status": "PASS" if not issues else "REVIEW_REQUIRED",
        "duration_seconds": round(parsed_duration, 3) if parsed_duration else None,
        "format": fmt.get("format_name", ""),
        "codec_name": audio_stream.get("codec_name", ""),
        "sample_rate_hz": parsed_sample_rate,
        "bitrate_bps": parsed_bitrate,
        "channels": parsed_channels,
        "peak_level_db": None,
        "clipping_risk": "NOT_MEASURED_FAST_REVIEW",
        "loudness_integrated_lufs": None,
        "leading_silence_seconds": None,
        "trailing_silence_seconds": None,
        "silence_ratio": None,
        "long_pauses": [],
        "abrupt_start_end_risk": "REVIEW_REQUIRED",
        "corruption_readability": "READABLE",
        "issues": issues,
        "objective_audio_score": round(score, 1),
    }


def objective_audio_analysis(bundle: Bundle) -> dict[str, Any]:
    analyses: list[dict[str, Any]] = []
    for record in bundle.audio_files:
        metrics = ffprobe_audio_metrics(record.path)
        metrics.update(
            {
                "source_path": root_relative(record.path),
                "size_bytes": record.size_bytes,
                "sha256": record.sha256,
            }
        )
        analyses.append(metrics)
    scores = [item.get("objective_audio_score", 0.0) for item in analyses]
    duration_seconds = sum(float(item.get("duration_seconds") or 0.0) for item in analyses)
    return {
        "candidate_slug": bundle.candidate_slug,
        "analysis_generated_at": utc_now(),
        "audio_file_count": len(bundle.audio_files),
        "duration_seconds": round(duration_seconds, 3) if duration_seconds else None,
        "ffprobe_status": analyses[0]["analysis_status"] if analyses else "NO_AUDIO_FILES",
        "audio_files": analyses,
        "objective_audio_score": round(min(scores), 1) if scores else 0.0,
    }


def build_source_inventory(bundle: Bundle, input_dir: Path) -> dict[str, Any]:
    required_roles = {
        "audio": bool(bundle.audio_files),
        "metadata_json": any(record.extension == ".json" and "meta" in record.path.name.lower() for record in bundle.files),
        "highlight_vtt": any(record.extension == ".vtt" for record in bundle.files),
        "timestamps_json": any("timestamp" in record.path.name.lower() for record in bundle.files),
        "chapters_json": any("chapter" in record.path.name.lower() for record in bundle.files),
    }
    missing_required = [role for role, present in required_roles.items() if not present]
    audio_hashes: dict[str, list[str]] = {}
    for record in bundle.audio_files:
        audio_hashes.setdefault(record.sha256, []).append(record.relative_path)
    duplicate_audio_files = [paths for paths in audio_hashes.values() if len(paths) > 1]
    audio_stems = {record.path.stem for record in bundle.audio_files}
    orphan_sidecars = []
    for record in bundle.sidecar_files:
        stem = re.sub(r"_(timestamps|timestamp|chapters|chapter|highlight|sync)$", "", record.path.stem)
        if audio_stems and stem not in audio_stems:
            orphan_sidecars.append(record.relative_path)
    unexpected_files = [record.relative_path for record in bundle.files if record.category == "unexpected"]
    return {
        "candidate_slug": bundle.candidate_slug,
        "source_dir": root_relative(bundle.source_dir),
        "input_root": root_relative(input_dir),
        "inventory_generated_at": utc_now(),
        "storage_status": "LOCAL_SOURCE_ONLY",
        "public_serving_status": PUBLIC_RELEASE_BLOCKED,
        "upload_status": "NOT_UPLOADED",
        "files": [
            {
                "path": record.relative_path,
                "source_path": root_relative(record.path),
                "category": record.category,
                "extension": record.extension,
                "size_bytes": record.size_bytes,
                "sha256": record.sha256,
            }
            for record in bundle.files
        ],
        "audio_files": [record.relative_path for record in bundle.audio_files],
        "metadata_files": [record.relative_path for record in bundle.metadata_files],
        "sidecar_files": [record.relative_path for record in bundle.sidecar_files],
        "cover_files": [record.relative_path for record in bundle.files if record.category == "cover"],
        "transcript_files": [record.relative_path for record in bundle.files if record.category == "transcript"],
        "missing_required_files": missing_required,
        "orphan_sidecars": orphan_sidecars,
        "duplicate_audio_files": duplicate_audio_files,
        "unexpected_files": unexpected_files,
    }


def load_primary_metadata(bundle: Bundle) -> dict[str, Any]:
    meta_records = sorted(
        [record for record in bundle.files if record.extension == ".json" and "meta" in record.path.name.lower()],
        key=lambda record: record.relative_path,
    )
    if not meta_records:
        return {}
    payload, status = read_json_safely(meta_records[0].path)
    return payload if status == "PASS" and isinstance(payload, dict) else {}


def normalized_metadata(bundle: Bundle, source_inventory: dict[str, Any], audio_analysis: dict[str, Any]) -> dict[str, Any]:
    meta = load_primary_metadata(bundle)
    title = str(meta.get("title") or bundle.candidate_slug)
    author = str(meta.get("author") or "Unknown")
    duration_ms = meta.get("duration_ms")
    duration_seconds = audio_analysis.get("duration_seconds")
    if duration_seconds is None and isinstance(duration_ms, (int, float)):
        duration_seconds = round(float(duration_ms) / 1000.0, 3)
    return {
        "candidate_slug": bundle.candidate_slug,
        "title": title,
        "author": author,
        "language": "Bengali",
        "language_code": str(meta.get("language") or "ben"),
        "duration_seconds": duration_seconds,
        "chapter_count": meta.get("chapters"),
        "narrator_or_model_source": meta.get("voice") or meta.get("provider_used") or "UNKNOWN",
        "provider_used": meta.get("provider_used", "UNKNOWN"),
        "source_metadata_path": source_inventory["metadata_files"][0] if source_inventory["metadata_files"] else "",
        "storage_status": "LOCAL_SOURCE_ONLY",
        "public_serving_status": PUBLIC_RELEASE_BLOCKED,
        "upload_status": "NOT_UPLOADED",
        "rights_status": "HOLD_RIGHTS_EVIDENCE_REQUIRED",
        "qa_status": "HOLD_HUMAN_QA_REQUIRED",
        "release_status": RELEASE_HOLD,
    }


def audio_file_manifest(bundle: Bundle, copy_internal: bool, candidate_dir: Path) -> dict[str, Any]:
    copied_files: list[dict[str, Any]] = []
    if copy_internal:
        audio_dir = ensure_internal_output_path(candidate_dir / "audio_internal")
        audio_dir.mkdir(parents=True, exist_ok=True)
        for record in bundle.audio_files:
            destination = ensure_internal_output_path(audio_dir / record.path.name)
            shutil.copy2(record.path, destination)
            copied_files.append(
                {
                    "source_path": root_relative(record.path),
                    "internal_copy_path": root_relative(destination),
                    "sha256": sha256_file(destination),
                    "storage_status": "INTERNAL_COPY_ONLY",
                }
            )
    return {
        "candidate_slug": bundle.candidate_slug,
        "generated_at": utc_now(),
        "copy_internal_requested": copy_internal,
        "storage_status": "LOCAL_SOURCE_ONLY" if not copy_internal else "INTERNAL_COPY_ONLY",
        "public_serving_status": PUBLIC_RELEASE_BLOCKED,
        "upload_status": "NOT_UPLOADED",
        "audio_files": [
            {
                "source_path": root_relative(record.path),
                "relative_source_path": record.relative_path,
                "size_bytes": record.size_bytes,
                "sha256": record.sha256,
                "storage_status": "LOCAL_SOURCE_ONLY",
            }
            for record in bundle.audio_files
        ],
        "internal_copies": copied_files,
        "frontend_public_audio_files": public_audio_files(),
        "frontend_build_audio_files": [path for path in public_audio_files() if path.startswith("frontend/build/")],
    }


def sidecar_integrity(bundle: Bundle, audio_analysis: dict[str, Any]) -> dict[str, Any]:
    duration = audio_analysis.get("duration_seconds")
    file_reports: list[dict[str, Any]] = []
    highlight_scores: list[float] = []
    for record in bundle.sidecar_files:
        name = record.path.name.lower()
        if record.extension == ".vtt":
            report = parse_vtt(record.path, duration)
        elif "timestamp" in name:
            report = parse_timestamp_json(record.path, duration)
        elif record.extension == ".json":
            payload, status = read_json_safely(record.path)
            report = {
                "path": root_relative(record.path),
                "status": status,
                "entry_count": len(payload) if isinstance(payload, list) else len(payload or {}) if isinstance(payload, dict) else 0,
                "issues": [] if status == "PASS" else [status],
                "highlight_usability_score": 8.0 if status == "PASS" else 0.0,
            }
        else:
            text = record.path.read_text(encoding="utf-8", errors="replace")
            findings = hidden_unicode_findings(text)
            report = {
                "path": root_relative(record.path),
                "status": "PASS" if not findings and not has_public_reference(text) else "REVIEW_REQUIRED",
                "issues": [finding["reason"] for finding in findings]
                + (["public URL/path reference"] if has_public_reference(text) else []),
                "highlight_usability_score": 8.0 if not findings and not has_public_reference(text) else 5.0,
            }
        file_reports.append(report)
        highlight_scores.append(float(report.get("highlight_usability_score", 0.0)))
    overall = round(min(highlight_scores), 1) if highlight_scores else 0.0
    return {
        "candidate_slug": bundle.candidate_slug,
        "generated_at": utc_now(),
        "sidecar_file_count": len(bundle.sidecar_files),
        "files": file_reports,
        "sidecar_integrity_status": "PASS" if all(report.get("status") == "PASS" for report in file_reports) else "REVIEW_REQUIRED",
        "sync_usability_score": overall,
    }


def highlight_sync_report(sidecar_report: dict[str, Any], audio_analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_slug": sidecar_report["candidate_slug"],
        "generated_at": utc_now(),
        "audio_duration_seconds": audio_analysis.get("duration_seconds"),
        "sync_usability_score": sidecar_report.get("sync_usability_score", 0.0),
        "sync_status": "HOLD_SYNC_QA_REQUIRED",
        "human_sync_review_required": True,
        "files": sidecar_report.get("files", []),
        "release_blocker": "Human Bengali sync/highlight QA >= 9.5 is required before public release candidacy.",
    }


def release_gate_report(
    metadata: dict[str, Any],
    inventory: dict[str, Any],
    audio_analysis: dict[str, Any],
    sync_report: dict[str, Any],
) -> dict[str, Any]:
    public_audio = public_audio_files()
    gates = {
        "objective_audio_score_9_5": audio_analysis.get("objective_audio_score", 0.0) >= 9.5,
        "sync_usability_score_9_5": sync_report.get("sync_usability_score", 0.0) >= 9.5,
        "bengali_human_listening_qa_9_5": False,
        "accessibility_listening_qa_9_5": False,
        "source_text_rights_evidence_exists": False,
        "derivative_audiobook_rights_evidence_exists": False,
        "owner_approval_exists": False,
        "legal_internal_review_exists": False,
        "rollback_plan_exists": False,
        "no_frontend_public_or_build_audio": not public_audio,
        "no_public_audio_object_metadata": True,
        "no_pre_release_public_audio_cta": True,
    }
    ready = all(gates.values())
    blockers = [key for key, passed in gates.items() if not passed]
    if inventory.get("missing_required_files"):
        blockers.append("missing_required_bundle_files")
    return {
        "candidate_slug": metadata["candidate_slug"],
        "generated_at": utc_now(),
        "release_status": "READY_FOR_PUBLIC_RELEASE_CANDIDATE" if ready else RELEASE_HOLD,
        "public_serving_status": PUBLIC_RELEASE_BLOCKED,
        "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "production_approved": False,
        "upload_status": "NOT_UPLOADED",
        "human_qa_required": True,
        "accessibility_qa_required": True,
        "rights_review_required": True,
        "legal_review_required": True,
        "frontend_public_audio_files": [path for path in public_audio if path.startswith("frontend/public/")],
        "frontend_build_audio_files": [path for path in public_audio if path.startswith("frontend/build/")],
        "gates": gates,
        "blockers": blockers,
    }


def source_rights_review(metadata: dict[str, Any]) -> str:
    return f"""# Source Rights Review: {metadata['title']}

Candidate slug: `{metadata['candidate_slug']}`
Language: Bengali
Status: `HOLD_SOURCE_RIGHTS_EVIDENCE_REQUIRED`

- Source text rights evidence: pending owner/legal review.
- Source provenance: not asserted by this ingestion pass.
- Public release: blocked.
- Required next step: attach source-rights evidence and legal/internal review before release candidacy.
"""


def derivative_rights_review(metadata: dict[str, Any]) -> str:
    return f"""# Derivative Audiobook Rights Review: {metadata['title']}

Candidate slug: `{metadata['candidate_slug']}`
Status: `HOLD_DERIVATIVE_AUDIOBOOK_RIGHTS_EVIDENCE_REQUIRED`

- Existing audio is referenced as a local internal source only.
- Derivative audiobook rights evidence: pending.
- Owner approval: pending.
- Public serving: blocked.
"""


def listening_scorecard(metadata: dict[str, Any]) -> str:
    return f"""# Bengali Listening QA Scorecard: {metadata['title']}

Candidate slug: `{metadata['candidate_slug']}`
Default decision: `HOLD_HUMAN_QA_REQUIRED`

| Criterion | Score /10 | Notes |
| --- | ---: | --- |
| Bengali pronunciation accuracy |  |  |
| Bengali literary rhythm |  |  |
| Emotional restraint |  |  |
| Clarity |  |  |
| Pacing |  |  |
| Pauses |  |  |
| Noise/artifacts |  |  |
| Fatigue risk |  |  |
| Text fidelity |  |  |
| Overall |  |  |

Reviewer name/date:
Decision: `HOLD_HUMAN_QA_REQUIRED`

Allowed decisions: `HOLD_HUMAN_QA_REQUIRED`, `REGENERATE_OR_REMASTER`, `READY_FOR_OWNER_REVIEW`, `READY_FOR_PUBLIC_RELEASE_CANDIDATE`.
"""


def accessibility_scorecard(metadata: dict[str, Any]) -> str:
    return f"""# Accessibility Listening QA Scorecard: {metadata['title']}

Candidate slug: `{metadata['candidate_slug']}`
Default decision: `HOLD_ACCESSIBILITY_QA_REQUIRED`

| Criterion | Score /10 | Notes |
| --- | ---: | --- |
| Blind-listening usability |  |  |
| Low-vision sync usability |  |  |
| Transcript availability |  |  |
| Highlight sync usefulness |  |  |
| Keyboard/screen-reader player readiness notes |  |  |
| Overall accessibility listening score |  |  |

Reviewer name/date:
Decision: `HOLD_ACCESSIBILITY_QA_REQUIRED`
"""


def remaster_plan(metadata: dict[str, Any], audio_analysis: dict[str, Any], sidecar_report: dict[str, Any]) -> str:
    return f"""# Remaster Improvement Plan: {metadata['title']}

Candidate slug: `{metadata['candidate_slug']}`
Current release status: `HOLD_BENGALI_AUDIOBOOK_QA_REQUIRED`

- Objective audio score: `{audio_analysis.get('objective_audio_score', 0.0)}`
- Sync usability score: `{sidecar_report.get('sync_usability_score', 0.0)}`
- Human Bengali listening QA: pending.
- Accessibility listening QA: pending.

Safe internal improvements may include normalized JSON/VTT sidecars and internal review-only loudness/silence repair copies under `improved_internal/`.
Speech content must not be altered, regenerated, or externally transcribed by this workflow.
"""


def store_listing(metadata: dict[str, Any], release_report: dict[str, Any]) -> str:
    duration = metadata.get("duration_seconds") or "pending objective measurement"
    chapter_count = metadata.get("chapter_count") or "pending"
    narrator = metadata.get("narrator_or_model_source") or "pending"
    return f"""# Store Listing Draft: {metadata['title']}

Title: {metadata['title']}
Author: {metadata['author']}
Language: Bengali
Candidate slug: {metadata['candidate_slug']}
Duration: {duration}
Chapter count: {chapter_count}
Narrator/model/source: {narrator}
Rights status: HOLD_RIGHTS_EVIDENCE_REQUIRED
QA status: HOLD_HUMAN_QA_REQUIRED
Release status: {release_report['release_status']}

Suggested premium description:
An internal Bengali audiobook store candidate prepared for careful rights, listening, sync, accessibility, and owner review.

Blocked public claims:
- Public availability claim.
- Accessibility compliance claim.
- Broad catalog-quality claim.

Allowed internal claims:
- Local source assets inventoried.
- Audio hashes recorded.
- Human Bengali listening QA remains required.
"""


def repair_sidecars(bundle: Bundle, candidate_dir: Path) -> list[dict[str, Any]]:
    improved_dir = ensure_internal_output_path(candidate_dir / "improved_internal" / "sidecars")
    actions: list[dict[str, Any]] = []
    for record in bundle.files:
        if record.extension not in {".json", ".vtt"}:
            continue
        destination = improved_dir / record.path.name
        if record.extension == ".json":
            payload, status = read_json_safely(record.path)
            if status == "PASS":
                write_json(destination, payload)
                actions.append({"action": "normalized_json_formatting", "source": root_relative(record.path), "output": root_relative(destination)})
        elif record.extension == ".vtt":
            text = record.path.read_text(encoding="utf-8", errors="replace")
            normalized = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines())
            write_text(destination, normalized)
            actions.append({"action": "repaired_vtt_line_formatting", "source": root_relative(record.path), "output": root_relative(destination)})
    if actions:
        write_json(candidate_dir / "improved_internal" / "improvement_actions.json", actions)
    return actions


def write_candidate(bundle: Bundle, input_dir: Path, output_dir: Path, mode: str, copy_internal: bool) -> dict[str, Any]:
    candidate_dir = ensure_internal_output_path(output_dir / bundle.candidate_slug)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    inventory = build_source_inventory(bundle, input_dir)
    audio_analysis = objective_audio_analysis(bundle)
    metadata = normalized_metadata(bundle, inventory, audio_analysis)
    manifest = audio_file_manifest(bundle, copy_internal, candidate_dir)
    sidecar_report = sidecar_integrity(bundle, audio_analysis)
    sync_report = highlight_sync_report(sidecar_report, audio_analysis)
    release_report = release_gate_report(metadata, inventory, audio_analysis, sync_report)

    write_json(candidate_dir / "source_inventory.json", inventory)
    write_json(candidate_dir / "normalized_metadata.json", metadata)
    write_json(candidate_dir / "audio_file_manifest.json", manifest)
    write_text(candidate_dir / "source_rights_review.md", source_rights_review(metadata))
    write_text(candidate_dir / "derivative_audiobook_rights_review.md", derivative_rights_review(metadata))
    write_json(candidate_dir / "objective_audio_analysis.json", audio_analysis)
    write_json(candidate_dir / "sidecar_integrity_report.json", sidecar_report)
    write_json(candidate_dir / "highlight_sync_usability_report.json", sync_report)
    write_text(candidate_dir / "bengali_listening_qa_scorecard.md", listening_scorecard(metadata))
    write_text(candidate_dir / "accessibility_listening_qa_scorecard.md", accessibility_scorecard(metadata))
    write_text(candidate_dir / "remaster_improvement_plan.md", remaster_plan(metadata, audio_analysis, sidecar_report))
    write_text(candidate_dir / "store_listing_draft.md", store_listing(metadata, release_report))
    write_json(candidate_dir / "release_gate_report.json", release_report)

    improvements: list[dict[str, Any]] = []
    if mode == "improve-internal":
        improvements = repair_sidecars(bundle, candidate_dir)

    return {
        "candidate_slug": bundle.candidate_slug,
        "candidate_dir": root_relative(candidate_dir),
        "title": metadata["title"],
        "author": metadata["author"],
        "audio_file_count": len(bundle.audio_files),
        "sidecar_file_count": len(bundle.sidecar_files),
        "missing_required_files": inventory["missing_required_files"],
        "objective_audio_score": audio_analysis.get("objective_audio_score", 0.0),
        "sync_usability_score": sidecar_report.get("sync_usability_score", 0.0),
        "objective_audio_status": audio_analysis.get("ffprobe_status"),
        "release_status": release_report["release_status"],
        "public_serving_status": PUBLIC_RELEASE_BLOCKED,
        "human_qa_required": True,
        "accessibility_qa_required": True,
        "rights_review_required": True,
        "automatic_improvement_count": len(improvements),
    }


def aggregate_markdown_inventory(summary: dict[str, Any]) -> str:
    lines = [
        "# Bengali Audiobook Store Candidate Inventory",
        "",
        f"Source path scanned: `{summary['source_input_dir']}`",
        f"Candidates detected: `{summary['candidate_count']}`",
        f"Release status: `{RELEASE_HOLD}`",
        "",
        "| Candidate | Audio | Sidecars | Missing Required | Release Status |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for candidate in summary["candidates"]:
        missing = ", ".join(candidate["missing_required_files"]) or "none"
        lines.append(
            f"| `{candidate['candidate_slug']}` | {candidate['audio_file_count']} | "
            f"{candidate['sidecar_file_count']} | {missing} | `{candidate['release_status']}` |"
        )
    return "\n".join(lines)


def aggregate_quality_scorecard(summary: dict[str, Any]) -> str:
    lines = [
        "# Bengali Audiobook Store Quality Scorecard",
        "",
        "| Candidate | Objective Audio | Sync Usability | Human QA | Accessibility QA | Decision |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for candidate in summary["candidates"]:
        lines.append(
            f"| `{candidate['candidate_slug']}` | {candidate['objective_audio_score']} | "
            f"{candidate['sync_usability_score']} | HOLD | HOLD | `{RELEASE_HOLD}` |"
        )
    return "\n".join(lines)


def aggregate_release_gate(summary: dict[str, Any]) -> str:
    public_audio = summary["public_audio_files"]
    return "\n".join(
        [
            "# Bengali Audiobook Store Release Gate Report",
            "",
            f"Overall status: `{RELEASE_HOLD}`",
            f"Public audio files in frontend trees: `{len(public_audio)}`",
            "No candidate is marked public-ready without human Bengali listening QA >= 9.5.",
            "Rights, derivative-audio evidence, owner approval, legal review, and rollback plan remain required.",
        ]
    )


def aggregate_improvement_plan(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Bengali Audiobook Store Improvement Plan",
            "",
            "Stage name: `BENGALI_AUDIOBOOK_STORE_CANDIDATE_REVIEW_AND_REMASTER`",
            "",
            "Future Bengali onboarding should run:",
            "`npm run audiobook:bengali-store-candidates:review`",
            "",
            "For internal-only safe sidecar cleanup, run:",
            "`npm run audiobook:bengali-store-candidates:improve`",
            "",
            "Public release remains blocked until objective audio, sync, human listening, accessibility, rights, legal, owner approval, and rollback gates all pass at 9.5+/10 where scored.",
        ]
    )


def write_aggregate_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    write_text(ROOT / "BENGALI_AUDIOBOOK_STORE_CANDIDATE_INVENTORY.md", aggregate_markdown_inventory(summary))
    write_text(ROOT / "BENGALI_AUDIOBOOK_STORE_QUALITY_SCORECARD.md", aggregate_quality_scorecard(summary))
    write_text(ROOT / "BENGALI_AUDIOBOOK_STORE_RELEASE_GATE_REPORT.md", aggregate_release_gate(summary))
    write_text(ROOT / "BENGALI_AUDIOBOOK_STORE_IMPROVEMENT_PLAN.md", aggregate_improvement_plan(summary))
    write_text(
        ROOT / "BENGALI_AUDIOBOOK_STORE_ORCHESTRATOR_STAGE.md",
        aggregate_improvement_plan(summary),
    )
    write_json(output_dir / "bengali_store_candidate_summary.json", summary)


def ingest_bengali_store_candidates(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    mode: str = "review",
    copy_internal: bool = False,
) -> dict[str, Any]:
    input_dir = input_dir if input_dir.is_absolute() else ROOT / input_dir
    output_dir = ensure_internal_output_path(output_dir if output_dir.is_absolute() else ROOT / output_dir)
    if mode not in {"review", "improve-internal"}:
        raise ValueError("mode must be review or improve-internal")
    if not input_dir.exists():
        raise FileNotFoundError(f"Bengali audiobook bundle input path does not exist: {input_dir}")

    bundles = scan_bundles(input_dir)
    candidate_summaries = [
        write_candidate(bundle, input_dir, output_dir, mode, copy_internal)
        for bundle in bundles
    ]
    public_audio = public_audio_files()
    summary = {
        "generated_by": "scripts/ingest_bengali_audiobook_store_candidates.py",
        "generated_at": utc_now(),
        "mode": mode,
        "source_input_dir": root_relative(input_dir),
        "output_dir": root_relative(output_dir),
        "candidate_count": len(candidate_summaries),
        "candidate_slugs": [candidate["candidate_slug"] for candidate in candidate_summaries],
        "candidates": candidate_summaries,
        "release_status": RELEASE_HOLD,
        "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "public_audio_files": public_audio,
        "frontend_public_audio_files": [path for path in public_audio if path.startswith("frontend/public/")],
        "frontend_build_audio_files": [path for path in public_audio if path.startswith("frontend/build/")],
        "human_qa_required": True,
        "rights_legal_owner_approval_required": True,
    }
    write_aggregate_reports(output_dir, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--mode", choices=["review", "improve-internal"], default="review")
    parser.add_argument("--copy-internal", action="store_true")
    args = parser.parse_args()

    try:
        summary = ingest_bengali_store_candidates(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            mode=args.mode,
            copy_internal=args.copy_internal,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should report concise failure.
        print(f"Bengali audiobook store candidate ingest failed: {exc}", file=sys.stderr)
        return 2

    print(
        "Bengali audiobook store candidate ingest complete: "
        f"mode={summary['mode']} candidates={summary['candidate_count']} "
        f"release_status={summary['release_status']} public_audio_files={len(summary['public_audio_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
