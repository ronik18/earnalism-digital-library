#!/usr/bin/env python3
"""Build and finalize immutable Earnalism audiobook package-v2 releases.

The first supported profile repackages the already-approved
``book-2b9853ec52`` production narration into two customer-delivery segments.
It never invokes TTS.  ``build-canary`` writes local masters, delivery files,
sidecars, a release descriptor, and a storage upload plan.  ``finalize`` binds
verified primary and DR B2 VersionIds into the canonical package manifest.

No command in this module mutates controlled publication truth or uploads
objects.  Upload and verification are delegated to
``audiobook_package_storage_v2.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
        else:
            result = finalize_command(
                package_dir=args.package_dir.resolve(),
                primary_receipt_path=args.primary_receipt.resolve(),
                replica_receipt_path=args.replica_receipt.resolve(),
            )
    except PackageBuildError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
