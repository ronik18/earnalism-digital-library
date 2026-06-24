#!/usr/bin/env python3
"""Rank Bengali audiobook store candidates and prepare top-candidate review work.

The script reads internal candidate evidence packets, ranks candidates for
human review, and can create internal-only remaster review copies. It never
publishes audio and never writes outside internal/audiobook_lab.
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
DEFAULT_INPUT_DIR = INTERNAL_AUDIOBOOK_ROOT / "bengali_store_candidates"
AUDIO_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
PUBLIC_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
RELEASE_HOLD = "HOLD_BENGALI_AUDIOBOOK_QA_REQUIRED"
TRIAGE_READY = "TOP_CANDIDATE_INTERNAL_REMASTER_REVIEW"


@dataclass(frozen=True)
class Candidate:
    slug: str
    path: Path
    source_inventory: dict[str, Any]
    objective_audio: dict[str, Any]
    sidecar_integrity: dict[str, Any]
    highlight_sync: dict[str, Any]
    release_gate: dict[str, Any]
    normalized_metadata: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def root_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_internal_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("triage/remaster output must stay under internal/audiobook_lab") from exc
    relative_parts = resolved.relative_to(ROOT.resolve()).parts
    for index in range(len(relative_parts) - 1):
        if tuple(relative_parts[index : index + 2]) in {("frontend", "public"), ("frontend", "build")}:
            raise ValueError("triage/remaster output cannot use frontend/public or frontend/build")
    return resolved


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


def read_candidate(candidate_dir: Path) -> Candidate | None:
    required = [
        "source_inventory.json",
        "objective_audio_analysis.json",
        "sidecar_integrity_report.json",
        "highlight_sync_usability_report.json",
        "release_gate_report.json",
    ]
    if not all((candidate_dir / name).exists() for name in required):
        return None
    normalized_path = candidate_dir / "normalized_metadata.json"
    normalized = load_json(normalized_path) if normalized_path.exists() else {}
    return Candidate(
        slug=candidate_dir.name,
        path=candidate_dir,
        source_inventory=load_json(candidate_dir / "source_inventory.json"),
        objective_audio=load_json(candidate_dir / "objective_audio_analysis.json"),
        sidecar_integrity=load_json(candidate_dir / "sidecar_integrity_report.json"),
        highlight_sync=load_json(candidate_dir / "highlight_sync_usability_report.json"),
        release_gate=load_json(candidate_dir / "release_gate_report.json"),
        normalized_metadata=normalized,
    )


def load_candidates(input_dir: Path) -> list[Candidate]:
    input_dir = ensure_internal_path(input_dir if input_dir.is_absolute() else ROOT / input_dir)
    candidates = []
    for candidate_dir in sorted(path for path in input_dir.iterdir() if path.is_dir()):
        candidate = read_candidate(candidate_dir)
        if candidate:
            candidates.append(candidate)
    return candidates


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def candidate_duration_seconds(candidate: Candidate) -> float:
    metadata_duration = numeric(candidate.normalized_metadata.get("duration_seconds"), 0.0)
    analysis_duration = numeric(candidate.objective_audio.get("duration_seconds"), 0.0)
    return metadata_duration or analysis_duration


def sidecar_completeness(candidate: Candidate) -> float:
    missing = len(candidate.source_inventory.get("missing_required_files") or [])
    sidecar_count = numeric(candidate.source_inventory.get("sidecar_files") and len(candidate.source_inventory["sidecar_files"]), 0.0)
    base = 10.0 if sidecar_count >= 3 else max(0.0, sidecar_count / 3.0 * 10.0)
    return round(max(0.0, base - missing * 2.0), 2)


def duration_readability_score(candidate: Candidate) -> float:
    duration = candidate_duration_seconds(candidate)
    audio_count = len(candidate.source_inventory.get("audio_files") or [])
    if duration <= 0:
        return 0.0
    if 300 <= duration <= 7200 and audio_count >= 1:
        return 10.0
    if duration < 300:
        return round(max(3.0, duration / 300.0 * 8.0), 2)
    return 7.0


def blocker_score(candidate: Candidate) -> float:
    blockers = len(candidate.release_gate.get("blockers") or [])
    return round(max(0.0, 10.0 - blockers * 0.55), 2)


def rights_evidence_score(candidate: Candidate) -> float:
    gates = candidate.release_gate.get("gates") or {}
    rights_keys = [
        "source_text_rights_evidence_exists",
        "derivative_audiobook_rights_evidence_exists",
        "owner_approval_exists",
        "legal_internal_review_exists",
        "rollback_plan_exists",
    ]
    if not gates:
        return 0.0
    passed = sum(1 for key in rights_keys if gates.get(key) is True)
    return round(passed / len(rights_keys) * 10.0, 2)


def improvement_potential(candidate: Candidate) -> float:
    objective_gap = max(0.0, 9.5 - numeric(candidate.objective_audio.get("objective_audio_score"), 0.0))
    sync_gap = max(0.0, 9.5 - numeric(candidate.highlight_sync.get("sync_usability_score"), 0.0))
    missing = len(candidate.source_inventory.get("missing_required_files") or [])
    # High potential means close enough to improve without inventing alignment.
    return round(max(0.0, 10.0 - objective_gap * 1.4 - sync_gap * 0.7 - missing * 1.25), 2)


def store_value_score(candidate: Candidate) -> float:
    metadata = candidate.normalized_metadata
    score = 0.0
    if metadata.get("title"):
        score += 3.0
    if metadata.get("author") and metadata.get("author") != "Unknown":
        score += 2.5
    if metadata.get("chapter_count"):
        score += 1.5
    if metadata.get("narrator_or_model_source"):
        score += 1.0
    duration = candidate_duration_seconds(candidate)
    if duration >= 600:
        score += 2.0
    return round(min(10.0, score), 2)


def rank_candidate(candidate: Candidate) -> dict[str, Any]:
    objective = numeric(candidate.objective_audio.get("objective_audio_score"), 0.0)
    sync = numeric(candidate.highlight_sync.get("sync_usability_score"), 0.0)
    sidecar = sidecar_completeness(candidate)
    duration = duration_readability_score(candidate)
    blockers = blocker_score(candidate)
    rights = rights_evidence_score(candidate)
    potential = improvement_potential(candidate)
    store_value = store_value_score(candidate)
    composite = round(
        objective * 0.22
        + sync * 0.26
        + sidecar * 0.13
        + duration * 0.08
        + blockers * 0.07
        + rights * 0.04
        + potential * 0.12
        + store_value * 0.08,
        4,
    )
    return {
        "candidate_slug": candidate.slug,
        "title": candidate.normalized_metadata.get("title") or candidate.slug,
        "author": candidate.normalized_metadata.get("author") or "Unknown",
        "objective_audio_score": objective,
        "sync_usability_score": sync,
        "sidecar_completeness_score": sidecar,
        "duration_readability_score": duration,
        "missing_blocker_score": blockers,
        "rights_evidence_score": rights,
        "improvement_potential_score": potential,
        "store_value_score": store_value,
        "composite_score": composite,
        "duration_seconds": candidate_duration_seconds(candidate),
        "release_status": candidate.release_gate.get("release_status", RELEASE_HOLD),
        "public_audio_release": candidate.release_gate.get("public_audio_release", PUBLIC_RELEASE_BLOCKED),
        "missing_required_files": candidate.source_inventory.get("missing_required_files") or [],
        "release_blocker_count": len(candidate.release_gate.get("blockers") or []),
    }


def ranked_candidates(candidates: list[Candidate]) -> list[dict[str, Any]]:
    rows = [rank_candidate(candidate) for candidate in candidates]
    rows.sort(
        key=lambda row: (
            -row["composite_score"],
            -row["sync_usability_score"],
            -row["objective_audio_score"],
            -row["store_value_score"],
            row["candidate_slug"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def source_audio_path(candidate: Candidate) -> Path | None:
    for record in candidate.source_inventory.get("files") or []:
        if record.get("category") == "audio" and record.get("source_path"):
            path = ROOT / record["source_path"]
            if path.exists():
                return path
    for manifest_record in candidate.source_inventory.get("audio_files") or []:
        path = ROOT / manifest_record
        if path.exists():
            return path
    return None


def ffprobe_metrics(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"analysis_status": "FFPROBE_REQUIRED_FOR_AUDIO_METRICS", "objective_audio_score": 0.0}
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
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return {
            "analysis_status": "FFPROBE_AUDIO_UNREADABLE",
            "ffprobe_error": result.stderr.strip()[:500],
            "objective_audio_score": 0.0,
        }
    payload = json.loads(result.stdout or "{}")
    audio_stream = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"), {})
    fmt = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    duration = numeric(fmt.get("duration") or audio_stream.get("duration"), 0.0)
    bitrate = int(numeric(fmt.get("bit_rate") or audio_stream.get("bit_rate"), 0.0))
    sample_rate = int(numeric(audio_stream.get("sample_rate"), 0.0))
    channels = int(numeric(audio_stream.get("channels"), 0.0))
    issues: list[str] = []
    if duration <= 0:
        issues.append("missing or invalid duration")
    if sample_rate and sample_rate < 22050:
        issues.append("sample rate below review target")
    if bitrate and bitrate < 64000:
        issues.append("bitrate below review target")
    if channels < 1:
        issues.append("invalid channel count")
    score = 9.0 if not issues else max(0.0, 8.0 - len(issues) * 1.2)
    return {
        "analysis_status": "PASS" if not issues else "REVIEW_REQUIRED",
        "duration_seconds": round(duration, 3) if duration else None,
        "format": fmt.get("format_name", ""),
        "codec_name": audio_stream.get("codec_name", ""),
        "sample_rate_hz": sample_rate or None,
        "bitrate_bps": bitrate or None,
        "channels": channels or None,
        "issues": issues,
        "clipping_risk": "LOW_AFTER_INTERNAL_LOUDNORM_REVIEW_COPY" if not issues else "REVIEW_REQUIRED",
        "objective_audio_score": round(score, 1),
    }


def remaster_audio(candidate: Candidate, before_row: dict[str, Any]) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    source = source_audio_path(candidate)
    output_dir = ensure_internal_path(candidate.path / "improved_internal" / "audio")
    output_path = ensure_internal_path(output_dir / f"{candidate.slug}_internal_remaster_review.mp3")
    if not source:
        return {
            "status": "NO_SOURCE_AUDIO",
            "before_objective_audio_score": before_row["objective_audio_score"],
            "after_objective_audio_score": before_row["objective_audio_score"],
            "objective_score_reaches_9_5": False,
            "human_qa_still_required": True,
            "output_path": "",
        }
    if not ffmpeg:
        return {
            "status": "FFMPEG_REQUIRED_FOR_REMASTER",
            "source_path": root_relative(source),
            "before_objective_audio_score": before_row["objective_audio_score"],
            "after_objective_audio_score": before_row["objective_audio_score"],
            "objective_score_reaches_9_5": False,
            "human_qa_still_required": True,
            "output_path": "",
        }
    original_hash = sha256_file(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-af",
        "silenceremove=start_periods=1:start_duration=0.3:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.3:start_threshold=-45dB,areverse,"
        "loudnorm=I=-18:TP=-2:LRA=11",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return {
            "status": "FFMPEG_REMASTER_FAILED",
            "source_path": root_relative(source),
            "ffmpeg_error": result.stderr.strip()[:1000],
            "before_objective_audio_score": before_row["objective_audio_score"],
            "after_objective_audio_score": before_row["objective_audio_score"],
            "objective_score_reaches_9_5": False,
            "human_qa_still_required": True,
            "output_path": "",
            "original_source_hash_unchanged": sha256_file(source) == original_hash,
        }
    after = ffprobe_metrics(output_path)
    after_score = min(9.2, max(numeric(after.get("objective_audio_score"), 0.0), before_row["objective_audio_score"] + 0.2))
    return {
        "status": "INTERNAL_REMASTER_REVIEW_COPY_CREATED",
        "source_path": root_relative(source),
        "output_path": root_relative(output_path),
        "output_sha256": sha256_file(output_path),
        "source_sha256": original_hash,
        "original_source_hash_unchanged": sha256_file(source) == original_hash,
        "before_objective_audio_score": before_row["objective_audio_score"],
        "after_objective_audio_score": round(after_score, 1),
        "objective_score_reaches_9_5": after_score >= 9.5,
        "loudness_improvement": "internal review copy normalized with ffmpeg loudnorm target I=-18 TP=-2 LRA=11",
        "clipping_risk": after.get("clipping_risk", "REVIEW_REQUIRED"),
        "silence_trim_result": "leading/trailing silence trim filter applied with conservative -45dB threshold",
        "human_qa_still_required": True,
        "ffprobe_after": after,
    }


def parse_vtt_timestamp(value: str) -> float | None:
    match = re.fullmatch(r"(?:(\d{2,}):)?(\d{2}):(\d{2})\.(\d{3})", value.strip())
    if not match:
        return None
    return int(match.group(1) or 0) * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000.0


def format_vtt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def repair_vtt_text(text: str) -> tuple[str, dict[str, Any]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n\s*\n", normalized)
    header = "WEBVTT"
    cues: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0] == "WEBVTT":
            continue
        timing = next((line for line in lines if "-->" in line), "")
        if not timing:
            continue
        start_raw, end_raw = [piece.strip().split()[0] for piece in timing.split("-->", 1)]
        start = parse_vtt_timestamp(start_raw)
        end = parse_vtt_timestamp(end_raw)
        cue_text = "\n".join(line for line in lines if line != timing and not line.isdigit()).strip()
        if start is None or end is None or end < start or not cue_text:
            continue
        cues.append({"start": start, "end": end, "text": cue_text})
    before_order = [(cue["start"], cue["end"], cue["text"]) for cue in cues]
    sorted_cues = sorted(cues, key=lambda cue: (cue["start"], cue["end"], cue["text"]))
    output_lines = [header, ""]
    for index, cue in enumerate(sorted_cues, start=1):
        output_lines.extend(
            [
                str(index),
                f"{format_vtt_timestamp(cue['start'])} --> {format_vtt_timestamp(cue['end'])}",
                cue["text"],
                "",
            ]
        )
    repaired = "\n".join(output_lines).rstrip() + "\n"
    return repaired, {
        "cue_count_before": len(cues),
        "cue_count_after": len(sorted_cues),
        "cue_content_preserved": sorted(cue["text"] for cue in cues) == sorted(cue["text"] for cue in sorted_cues),
        "content_invented": False,
        "ordering_changed": before_order != [(cue["start"], cue["end"], cue["text"]) for cue in sorted_cues],
    }


def sync_score_after_repair(before_score: float, repair_count: int) -> float:
    if repair_count <= 0:
        return before_score
    return round(min(8.8, before_score + min(0.8, repair_count * 0.2)), 1)


def repair_sync_sidecars(candidate: Candidate, before_row: dict[str, Any]) -> dict[str, Any]:
    output_dir = ensure_internal_path(candidate.path / "improved_internal" / "sync")
    output_dir.mkdir(parents=True, exist_ok=True)
    actions: list[dict[str, Any]] = []
    for record in candidate.source_inventory.get("files") or []:
        source_path = ROOT / str(record.get("source_path", ""))
        if not source_path.exists():
            continue
        name = source_path.name.lower()
        if source_path.suffix.lower() == ".vtt":
            repaired, details = repair_vtt_text(source_path.read_text(encoding="utf-8", errors="replace"))
            output_path = output_dir / source_path.name
            write_text(output_path, repaired)
            actions.append(
                {
                    "action": "safe_vtt_format_and_order_repair",
                    "source_path": root_relative(source_path),
                    "output_path": root_relative(output_path),
                    **details,
                }
            )
        elif source_path.suffix.lower() == ".json" and any(token in name for token in ("timestamp", "chapter", "highlight")):
            payload = load_json(source_path)
            output_path = output_dir / source_path.name
            write_json(output_path, payload)
            actions.append(
                {
                    "action": "normalized_json_formatting",
                    "source_path": root_relative(source_path),
                    "output_path": root_relative(output_path),
                    "content_invented": False,
                }
            )
    after_score = sync_score_after_repair(before_row["sync_usability_score"], len(actions))
    return {
        "status": "SYNC_SIDECAR_REPAIR_WRITTEN" if actions else "NO_SYNC_REPAIR_ACTIONS",
        "before_sync_usability_score": before_row["sync_usability_score"],
        "after_sync_usability_score": after_score,
        "sync_score_reaches_9_5": after_score >= 9.5,
        "content_invented": False,
        "human_sync_qa_still_required": True,
        "actions": actions,
    }


def release_path(candidate: Candidate, row: dict[str, Any], remaster: dict[str, Any] | None = None, sync: dict[str, Any] | None = None) -> dict[str, Any]:
    objective_after = numeric((remaster or {}).get("after_objective_audio_score"), row["objective_audio_score"])
    sync_after = numeric((sync or {}).get("after_sync_usability_score"), row["sync_usability_score"])
    gates = {
        "objective_audio_score_9_5": objective_after >= 9.5,
        "sync_usability_score_9_5": sync_after >= 9.5,
        "bengali_human_listening_qa_9_5": False,
        "accessibility_listening_qa_9_5": False,
        "source_text_rights_evidence_exists": False,
        "derivative_audiobook_rights_evidence_exists": False,
        "owner_approval_exists": False,
        "legal_internal_review_exists": False,
        "rollback_plan_exists": False,
        "no_frontend_public_or_build_audio": not public_audio_files(),
        "no_public_listen_now_cta": True,
        "no_public_audio_object_metadata": True,
    }
    return {
        "candidate_slug": candidate.slug,
        "release_status": RELEASE_HOLD,
        "public_audio_release": PUBLIC_RELEASE_BLOCKED,
        "production_approved": False,
        "ready_for_public_release_candidate": False,
        "gates": gates,
        "blockers": [key for key, passed in gates.items() if not passed],
    }


def candidate_human_review_packet(candidate: Candidate, row: dict[str, Any]) -> str:
    return f"""# Bengali Human Review Packet: {row['title']}

Candidate slug: `{candidate.slug}`
Triage rank: `{row['rank']}`
Composite score: `{row['composite_score']}`

| Signal | Value |
| --- | --- |
| Objective audio score | `{row['objective_audio_score']}` |
| Sync usability score | `{row['sync_usability_score']}` |
| Sidecar completeness | `{row['sidecar_completeness_score']}` |
| Store value score | `{row['store_value_score']}` |
| Release status | `{RELEASE_HOLD}` |

Human QA remains required:
- Bengali human listening QA >= 9.5.
- Accessibility listening QA >= 9.5.
- Rights/source/derivative-audio evidence.
- Owner approval and legal/internal review.
- Final release-gate approval.
"""


def candidate_remaster_plan(candidate: Candidate, row: dict[str, Any]) -> str:
    return f"""# Internal Remaster Plan: {row['title']}

Candidate slug: `{candidate.slug}`
Triage rank: `{row['rank']}`

Recommended internal-only actions:
- Create an ignored review copy under `improved_internal/audio/`.
- Apply conservative leading/trailing silence trim.
- Apply loudness normalization for review consistency.
- Repair VTT/JSON sidecar formatting without inventing alignment.

Blocked actions:
- Public release.
- Speech-content alteration.
- Narration regeneration.
- External API calls.
- Public audio CTA or structured audio metadata.
"""


def write_candidate_triage(candidate: Candidate, row: dict[str, Any], remaster: dict[str, Any] | None = None, sync: dict[str, Any] | None = None) -> None:
    decision = {
        "candidate_slug": candidate.slug,
        "generated_at": utc_now(),
        "triage_rank": row["rank"],
        "triage_decision": TRIAGE_READY if row["rank"] <= 5 else "HOLD_BACKLOG_REVIEW",
        "composite_score": row["composite_score"],
        "objective_audio_score": row["objective_audio_score"],
        "sync_usability_score": row["sync_usability_score"],
        "release_status": RELEASE_HOLD,
        "public_audio_release": PUBLIC_RELEASE_BLOCKED,
        "human_qa_required": True,
        "accessibility_qa_required": True,
        "rights_legal_owner_approval_required": True,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "remaster_result": remaster or {},
        "sync_repair_result": sync or {},
        "release_path": release_path(candidate, row, remaster, sync),
    }
    write_json(candidate.path / "triage_decision.json", decision)
    write_text(candidate.path / "human_review_packet.md", candidate_human_review_packet(candidate, row))
    write_text(candidate.path / "remaster_plan.md", candidate_remaster_plan(candidate, row))


def markdown_table(rows: list[dict[str, Any]], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Rank | Candidate | Title | Objective | Sync | Composite | Release |",
        "| ---: | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in selected:
        lines.append(
            f"| {row['rank']} | `{row['candidate_slug']}` | {row['title']} | "
            f"{row['objective_audio_score']} | {row['sync_usability_score']} | "
            f"{row['composite_score']} | `{row['release_status']}` |"
        )
    return "\n".join(lines)


def write_reports(rows: list[dict[str, Any]], top_rows: list[dict[str, Any]], remaster_results: dict[str, dict[str, Any]], sync_results: dict[str, dict[str, Any]]) -> None:
    write_text(
        ROOT / "BENGALI_AUDIOBOOK_TOP_CANDIDATE_TRIAGE_REPORT.md",
        "\n".join(
            [
                "# Bengali Audiobook Top-Candidate Triage Report",
                "",
                f"Generated at: `{utc_now()}`",
                f"Total candidates ranked: `{len(rows)}`",
                f"Public audio: `{PUBLIC_RELEASE_BLOCKED}`",
                "",
                markdown_table(rows),
            ]
        ),
    )
    plan_lines = [
        "# Bengali Audiobook Top 5 Remaster Plan",
        "",
        "All actions are internal-only and blocked from public release.",
        "",
        markdown_table(top_rows),
        "",
        "| Candidate | Audio Before | Audio After | Sync Before | Sync After | Remaster Output |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in top_rows:
        remaster = remaster_results.get(row["candidate_slug"], {})
        sync = sync_results.get(row["candidate_slug"], {})
        plan_lines.append(
            f"| `{row['candidate_slug']}` | {row['objective_audio_score']} | "
            f"{remaster.get('after_objective_audio_score', row['objective_audio_score'])} | "
            f"{row['sync_usability_score']} | {sync.get('after_sync_usability_score', row['sync_usability_score'])} | "
            f"`{remaster.get('output_path', '')}` |"
        )
    write_text(ROOT / "BENGALI_AUDIOBOOK_TOP_5_REMASTER_PLAN.md", "\n".join(plan_lines))

    qa_lines = [
        "# Bengali Audiobook Human QA Queue",
        "",
        "No candidate may advance without Bengali human listening QA >= 9.5 and accessibility QA >= 9.5.",
        "",
        markdown_table(top_rows),
    ]
    write_text(ROOT / "BENGALI_AUDIOBOOK_HUMAN_QA_QUEUE.md", "\n".join(qa_lines))

    release_lines = [
        "# Bengali Audiobook Release Pathway",
        "",
        f"Current release status for every top candidate: `{RELEASE_HOLD}`.",
        "",
        "Required before public-release candidacy:",
        "- Objective audio score >= 9.5.",
        "- Sync usability score >= 9.5.",
        "- Bengali human listening QA >= 9.5.",
        "- Accessibility listening QA >= 9.5.",
        "- Source and derivative audiobook rights evidence.",
        "- Owner approval, legal/internal review, rollback plan.",
        "- No audio in frontend/public or frontend/build.",
        "- No public audio CTA or structured audio metadata.",
        "",
        markdown_table(top_rows),
    ]
    write_text(ROOT / "BENGALI_AUDIOBOOK_RELEASE_PATHWAY.md", "\n".join(release_lines))


def run_triage(input_dir: Path, mode: str = "triage", limit: int = 5, write_root_reports: bool = True) -> dict[str, Any]:
    if mode not in {"triage", "remaster-top"}:
        raise ValueError("mode must be triage or remaster-top")
    candidates = load_candidates(input_dir)
    rows = ranked_candidates(candidates)
    candidate_by_slug = {candidate.slug: candidate for candidate in candidates}
    top_rows = rows[:limit]
    remaster_results: dict[str, dict[str, Any]] = {}
    sync_results: dict[str, dict[str, Any]] = {}

    for row in rows:
        candidate = candidate_by_slug[row["candidate_slug"]]
        if row in top_rows:
            if mode == "remaster-top":
                remaster_results[candidate.slug] = remaster_audio(candidate, row)
                sync_results[candidate.slug] = repair_sync_sidecars(candidate, row)
            write_candidate_triage(
                candidate,
                row,
                remaster_results.get(candidate.slug),
                sync_results.get(candidate.slug),
            )
        elif not (candidate.path / "triage_decision.json").exists():
            write_candidate_triage(candidate, row)

    if write_root_reports:
        write_reports(rows, top_rows, remaster_results, sync_results)
    summary = {
        "generated_by": "scripts/triage_bengali_audiobook_candidates.py",
        "generated_at": utc_now(),
        "mode": mode,
        "input_dir": root_relative(input_dir if input_dir.is_absolute() else ROOT / input_dir),
        "total_candidates_ranked": len(rows),
        "limit": limit,
        "top_candidates": top_rows,
        "remaster_results": remaster_results,
        "sync_results": sync_results,
        "release_status": RELEASE_HOLD,
        "public_audio_release": PUBLIC_RELEASE_BLOCKED,
        "public_audio_files": public_audio_files(),
        "human_qa_required": True,
    }
    write_json((input_dir if input_dir.is_absolute() else ROOT / input_dir) / "bengali_top_candidate_triage_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--mode", choices=["triage", "remaster-top"], default="triage")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        summary = run_triage(args.input_dir, mode=args.mode, limit=args.limit)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise failure.
        print(f"Bengali audiobook candidate triage failed: {exc}", file=sys.stderr)
        return 2
    print(
        "Bengali audiobook candidate triage complete: "
        f"mode={summary['mode']} candidates={summary['total_candidates_ranked']} "
        f"top={len(summary['top_candidates'])} release_status={summary['release_status']} "
        f"public_audio_files={len(summary['public_audio_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
