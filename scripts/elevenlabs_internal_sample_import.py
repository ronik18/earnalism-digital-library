#!/usr/bin/env python3
"""Validate and register a manual ElevenLabs internal sample import.

This script never calls ElevenLabs, generates audio, publishes audio, or writes
audio into public frontend directories. It only records internal evidence for
an owner-generated sample that already exists under internal/audiobook_lab.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
INTERNAL_SAMPLE_ONLY = "INTERNAL_SAMPLE_ONLY"
INTERNAL_FULL_CHAPTER_ONLY = "INTERNAL_FULL_CHAPTER_ONLY"
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"
PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
READY_FOR_INTERNAL_IMPORT = "READY_FOR_INTERNAL_IMPORT"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_under(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay under {root.relative_to(ROOT)}") from exc


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def sentence_items(
    sample_text: str,
    *,
    book_slug: str,
    chapter: str,
    audio_hash: str,
    sentence_chunk_map: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, raw_line in enumerate(sample_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^\[(s\d{3})\]\s*(.+)$", line)
        sentence_id = match.group(1) if match else f"s{index:03d}"
        text = match.group(2).strip() if match else line
        chunk = (sentence_chunk_map or {}).get(sentence_id, {})
        item = {
            "text_fragment_id": f"{book_slug}-chapter-{int(chapter):03d}-{sentence_id}",
            "sentence_id": sentence_id,
            "chapter": int(chapter),
            "text": text,
            "start_ms": None,
            "end_ms": None,
            "timing_source": "placeholder_manual_alignment_required",
            "sync_level": "sentence",
            "sync_status": HOLD_SYNC_QA_REQUIRED,
            "audio_hash": chunk.get("audio_hash") or audio_hash,
            "public": False,
        }
        if chunk.get("chunk_id"):
            item["chunk_id"] = chunk["chunk_id"]
        items.append(item)
    return items


def find_imported_audio(imported_audio_dir: Path) -> list[Path]:
    if not imported_audio_dir.exists():
        return []
    return sorted(
        path for path in imported_audio_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_manual_chunk_sample_workflow(sample_dir: Path) -> bool:
    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    return (manual_dir / "expected_audio_filenames.json").exists() or (
        manual_dir / "manual_download_validation_report.json"
    ).exists()


def is_full_chapter_workflow(sample_dir: Path) -> bool:
    return (sample_dir / "full_chapter_sync_source_with_ids.txt").exists() or (sample_dir / "full_chapter_text.txt").exists()


def text_path_for(sample_dir: Path) -> Path:
    if is_full_chapter_workflow(sample_dir):
        sync_source = sample_dir / "full_chapter_sync_source_with_ids.txt"
        if sync_source.exists():
            return sync_source
        return sample_dir / "full_chapter_text.txt"
    return sample_dir / "sample_text.txt"


def chunk_audio_id(path: Path) -> str:
    match = re.search(r"(c\d{3})", path.stem)
    return match.group(1) if match else ""


def source_sentence_lookup(sample_dir: Path) -> dict[str, str]:
    sentence_map_path = sample_dir / "sentence_map.json"
    if sentence_map_path.exists():
        sentence_map = load_json(sentence_map_path)
        if isinstance(sentence_map, dict):
            return {
                str(sentence_id): str(value.get("source_text") or value.get("narration_text") or "")
                for sentence_id, value in sentence_map.items()
                if isinstance(value, dict)
            }

    lookup: dict[str, str] = {}
    source_path = text_path_for(sample_dir)
    if not source_path.exists():
        return lookup
    for raw_line in source_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = re.match(r"^\[(s\d{3})\]\s*(.+)$", line)
        if match:
            lookup[match.group(1)] = match.group(2).strip()
    return lookup


def manual_sentence_items(
    *,
    book_slug: str,
    chapter: str,
    sample_dir: Path,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup = source_sentence_lookup(sample_dir)
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk_id = str(chunk["chunk_id"])
        audio_hash = str(chunk["audio_hash"])
        for sentence_id in chunk.get("sentence_ids", []):
            sentence_id = str(sentence_id)
            items.append(
                {
                    "text_fragment_id": f"{book_slug}-chapter-{int(chapter):03d}-{sentence_id}",
                    "sentence_id": sentence_id,
                    "chapter": int(chapter),
                    "chunk_id": chunk_id,
                    "text": lookup.get(sentence_id, ""),
                    "start_ms": None,
                    "end_ms": None,
                    "timing_source": "placeholder_manual_alignment_required",
                    "sync_level": "sentence",
                    "sync_status": HOLD_SYNC_QA_REQUIRED,
                    "audio_hash": audio_hash,
                    "public": False,
                }
            )
    return items


def load_manual_chunk_audio(
    *,
    sample_dir: Path,
    book_slug: str,
    chapter: str,
) -> tuple[list[dict[str, Any]], str, Path, Path, Path, dict[str, Any]]:
    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    validation_report_path = manual_dir / "manual_download_validation_report.json"
    expected_manifest_path = manual_dir / "expected_audio_filenames.json"
    if not validation_report_path.exists():
        raise FileNotFoundError(f"manual_download_validation_report.json not found: {validation_report_path}")
    if not expected_manifest_path.exists():
        raise FileNotFoundError(f"expected_audio_filenames.json not found: {expected_manifest_path}")

    validation_report = load_json(validation_report_path)
    expected_manifest = load_json(expected_manifest_path)
    status = validation_report.get("status")
    if status != READY_FOR_INTERNAL_IMPORT:
        raise ValueError(
            "manual_download_validation_report.json must be READY_FOR_INTERNAL_IMPORT "
            f"before import; found {status}"
        )

    expected_chunks = expected_manifest.get("chunks")
    if not isinstance(expected_chunks, list) or not expected_chunks:
        raise ValueError("expected_audio_filenames.json must contain a non-empty chunks list")

    imported_audio_dir = repo_path(expected_manifest.get("imported_audio_dir") or sample_dir / "imported_audio")
    ensure_under(imported_audio_dir, INTERNAL_AUDIOBOOK_ROOT, "manual imported audio directory")
    if not imported_audio_dir.exists():
        raise FileNotFoundError(f"manual imported audio directory not found: {imported_audio_dir.relative_to(ROOT)}")

    expected_names = [str(chunk.get("audio_filename") or "") for chunk in expected_chunks]
    if any(not name for name in expected_names):
        raise ValueError("each expected manual chunk must declare audio_filename")
    if len(expected_names) != len(set(expected_names)):
        raise ValueError("expected manual chunk audio filenames must be unique")

    expected_by_name = set(expected_names)
    actual_audio_files = {
        path.name: path
        for path in sorted(imported_audio_dir.iterdir())
        if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS
    }
    missing = [name for name in expected_names if name not in actual_audio_files]
    unexpected = sorted(name for name in actual_audio_files if name not in expected_by_name)
    if missing:
        raise FileNotFoundError("missing expected manual chunk audio files: " + ", ".join(missing))
    if unexpected:
        raise ValueError("unexpected audio files in manual imported_audio: " + ", ".join(unexpected))

    report_present = {
        str(item.get("audio_filename")): item
        for item in validation_report.get("present_audio", [])
        if isinstance(item, dict)
    }
    if len(report_present) != len(expected_names):
        raise ValueError("manual_download_validation_report.json present_audio does not match expected chunks")
    if validation_report.get("missing_audio"):
        raise ValueError("manual_download_validation_report.json still records missing audio")
    if validation_report.get("unexpected_audio"):
        raise ValueError("manual_download_validation_report.json still records unexpected audio")
    if validation_report.get("public_audio_files"):
        raise ValueError("manual_download_validation_report.json records public/build audio files")

    chunks: list[dict[str, Any]] = []
    for expected_chunk in expected_chunks:
        chunk_id = str(expected_chunk.get("chunk_id") or "")
        if not re.fullmatch(r"c\d{3}", chunk_id):
            raise ValueError(f"manual chunk has invalid chunk_id: {chunk_id}")
        audio_filename = str(expected_chunk["audio_filename"])
        expected_audio_path = repo_path(expected_chunk.get("expected_audio_path") or imported_audio_dir / audio_filename)
        ensure_under(expected_audio_path, INTERNAL_AUDIOBOOK_ROOT, "expected audio path")
        audio_path = actual_audio_files[audio_filename]
        ensure_under(audio_path, INTERNAL_AUDIOBOOK_ROOT, "manual imported audio")
        if audio_path.resolve() != expected_audio_path.resolve():
            raise ValueError(
                f"expected audio path for {chunk_id} does not match imported file: "
                f"{expected_audio_path.relative_to(ROOT)}"
            )
        audio_hash = sha256_file(audio_path)
        report_entry = report_present.get(audio_filename)
        if not report_entry:
            raise ValueError(f"manual validation report is missing present_audio for {audio_filename}")
        if str(report_entry.get("audio_hash")) != audio_hash:
            raise ValueError(f"manual validation report hash is stale for {audio_filename}")
        sentence_ids = [str(sentence_id) for sentence_id in expected_chunk.get("sentence_ids", [])]
        chunks.append(
            {
                "chunk_id": chunk_id,
                "chapter": int(chapter),
                "audio_filename": audio_filename,
                "audio_path": str(audio_path.relative_to(ROOT)),
                "audio_hash": audio_hash,
                "file_size_bytes": audio_path.stat().st_size,
                "sentence_ids": sentence_ids,
                "sentence_count": len(sentence_ids),
                "text_hash": expected_chunk.get("text_hash"),
                "settings_hash": expected_chunk.get("settings_hash"),
                "estimated_duration_seconds": expected_chunk.get("estimated_duration_seconds"),
                "generation_status": "IMPORTED_OWNER_MANUAL_DOWNLOAD",
                "provider": expected_manifest.get("provider") or "ElevenLabs",
                "voice_name": expected_manifest.get("voice_name") or "Rachel",
                "voice_id": expected_manifest.get("voice_id") or "21m00Tcm4TlvDq8ikWAM",
                "public": False,
            }
        )

    ordered_chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    if ordered_chunk_ids != sorted(ordered_chunk_ids):
        raise ValueError("manual chunks must be ordered by stable chunk_id")

    combined_audio_hash = sha256_text("\n".join(chunk["audio_hash"] for chunk in chunks))
    return chunks, combined_audio_hash, imported_audio_dir, validation_report_path, expected_manifest_path, expected_manifest


def load_chunk_audio(
    *,
    sample_dir: Path,
    audio_files: list[Path],
    book_slug: str,
    chapter: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], str]:
    chunk_manifest_path = sample_dir / "chunk_manifest.json"
    chunk_manifest = load_json(chunk_manifest_path) if chunk_manifest_path.exists() else {}
    manifest_chunks = list(chunk_manifest.get("chunks") or [])
    audio_by_name = {path.name: path for path in audio_files}
    audio_by_chunk_id = {chunk_audio_id(path): path for path in audio_files if chunk_audio_id(path)}
    chunks: list[dict[str, Any]] = []
    sentence_chunk_map: dict[str, dict[str, str]] = {}

    if manifest_chunks:
        for manifest_chunk in manifest_chunks:
            chunk_id = str(manifest_chunk.get("chunk_id") or "")
            audio_filename = str(manifest_chunk.get("audio_filename") or "")
            audio_path = audio_by_name.get(audio_filename) or audio_by_chunk_id.get(chunk_id)
            if audio_path is None:
                raise FileNotFoundError(
                    f"Missing imported audio for {chunk_id or audio_filename} under "
                    f"{(sample_dir / 'imported_audio').relative_to(ROOT)}"
                )
            ensure_under(audio_path, INTERNAL_AUDIOBOOK_ROOT, "imported audio")
            audio_hash = sha256_file(audio_path)
            chunk = {
                "chunk_id": chunk_id,
                "chapter": int(chapter),
                "audio_path": str(audio_path.relative_to(ROOT)),
                "audio_hash": audio_hash,
                "text_hash": manifest_chunk.get("text_hash"),
                "settings_hash": manifest_chunk.get("settings_hash"),
                "sentence_start": manifest_chunk.get("sentence_start"),
                "sentence_end": manifest_chunk.get("sentence_end"),
                "sentence_count": manifest_chunk.get("sentence_count"),
                "word_count": manifest_chunk.get("word_count"),
                "estimated_seconds": manifest_chunk.get("estimated_seconds"),
                "public": False,
            }
            chunks.append(chunk)
            start = int(str(manifest_chunk.get("sentence_start", "s000"))[1:])
            end = int(str(manifest_chunk.get("sentence_end", "s000"))[1:])
            for index in range(start, end + 1):
                sentence_chunk_map[f"s{index:03d}"] = {"chunk_id": chunk_id, "audio_hash": audio_hash}
    else:
        for index, audio_path in enumerate(audio_files, start=1):
            ensure_under(audio_path, INTERNAL_AUDIOBOOK_ROOT, "imported audio")
            chunk_id = chunk_audio_id(audio_path) or f"c{index:03d}"
            audio_hash = sha256_file(audio_path)
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chapter": int(chapter),
                    "audio_path": str(audio_path.relative_to(ROOT)),
                    "audio_hash": audio_hash,
                    "public": False,
                }
            )

    combined_audio_hash = sha256_text("\n".join(chunk["audio_hash"] for chunk in chunks))
    return chunks, sentence_chunk_map, combined_audio_hash


def run_import(*, book_slug: str, chapter: str, sample_dir: Path) -> dict[str, Any]:
    sample_dir = sample_dir if sample_dir.is_absolute() else ROOT / sample_dir
    ensure_under(sample_dir, INTERNAL_AUDIOBOOK_ROOT, "sample-dir")
    public_audio = public_audio_files()
    if public_audio:
        raise ValueError("public audio files are present: " + ", ".join(public_audio))

    manual_chunk_sample = is_manual_chunk_sample_workflow(sample_dir)
    sample_text_path = text_path_for(sample_dir)
    if not manual_chunk_sample and not sample_text_path.exists():
        raise FileNotFoundError(f"{sample_text_path.name} not found: {sample_text_path}")

    generated_at = utc_now()
    imported_audio_dir = sample_dir / "imported_audio"
    full_chapter = is_full_chapter_workflow(sample_dir) and not manual_chunk_sample
    chunks: list[dict[str, Any]] = []
    sentence_chunk_map: dict[str, dict[str, str]] = {}
    audio_relative = ""
    combined_sample_manifest_path: Path | None = None
    manual_validation_report_path: Path | None = None
    expected_manifest_path: Path | None = None
    expected_manifest: dict[str, Any] = {}

    if manual_chunk_sample:
        (
            chunks,
            audio_hash,
            imported_audio_dir,
            manual_validation_report_path,
            expected_manifest_path,
            expected_manifest,
        ) = load_manual_chunk_audio(sample_dir=sample_dir, book_slug=book_slug, chapter=chapter)
        audio_status = INTERNAL_SAMPLE_ONLY
    else:
        audio_files = find_imported_audio(imported_audio_dir)
        if not audio_files:
            raise FileNotFoundError(f"No imported audio file found under {imported_audio_dir.relative_to(ROOT)}")
        if not full_chapter and len(audio_files) > 1:
            raise ValueError("Exactly one imported audio file is allowed for this internal sample.")

        if full_chapter:
            chunks, sentence_chunk_map, audio_hash = load_chunk_audio(
                sample_dir=sample_dir, audio_files=audio_files, book_slug=book_slug, chapter=chapter
            )
            audio_status = INTERNAL_FULL_CHAPTER_ONLY
        else:
            audio_path = audio_files[0]
            ensure_under(audio_path, INTERNAL_AUDIOBOOK_ROOT, "imported audio")
            audio_hash = sha256_file(audio_path)
            audio_relative = str(audio_path.relative_to(ROOT))
            audio_status = INTERNAL_SAMPLE_ONLY

    sample_text = sample_text_path.read_text(encoding="utf-8") if sample_text_path.exists() else "\n".join(
        chunk.get("audio_filename", "") for chunk in chunks
    )

    imported_manifest = {
        "generated_by": "scripts/elevenlabs_internal_sample_import.py",
        "generated_at": generated_at,
        "book_slug": book_slug,
        "chapter": int(chapter),
        "provider": "ElevenLabs",
        "voice_name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "audio_status": audio_status,
        "status": audio_status,
        "import_workflow": "manual_chunk_sample" if manual_chunk_sample else ("full_chapter" if full_chapter else "single_file_sample"),
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "production_approved": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "full_book_generation_allowed": False,
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "audio_hash": audio_hash,
        "text_hash": sha256_text(sample_text),
        "sample_dir": str(sample_dir.relative_to(ROOT)),
    }
    if manual_chunk_sample:
        imported_manifest["chunks"] = chunks
        imported_manifest["chunk_count"] = len(chunks)
        imported_manifest["audio_paths"] = [chunk["audio_path"] for chunk in chunks]
        imported_manifest["manual_download_validation_report_path"] = str(manual_validation_report_path.relative_to(ROOT))
        imported_manifest["expected_audio_filenames_path"] = str(expected_manifest_path.relative_to(ROOT))
        imported_manifest["imported_audio_dir"] = str(imported_audio_dir.relative_to(ROOT))
    elif full_chapter:
        imported_manifest["chunks"] = chunks
        imported_manifest["chunk_count"] = len(chunks)
        imported_manifest["audio_paths"] = [chunk["audio_path"] for chunk in chunks]
    else:
        imported_manifest["audio_path"] = audio_relative

    sync_manifest = {
        "generated_by": "scripts/elevenlabs_internal_sample_import.py",
        "generated_at": generated_at,
        "book_slug": book_slug,
        "chapter": int(chapter),
        "provider": "ElevenLabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "sync_level": "sentence",
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "audio_status": audio_status,
        "production_status": PRODUCTION_BLOCKED,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public": False,
        "timing_qa_passed": False,
        "public_audio_allowed": False,
        "items": (
            manual_sentence_items(book_slug=book_slug, chapter=chapter, sample_dir=sample_dir, chunks=chunks)
            if manual_chunk_sample
            else sentence_items(
                sample_text,
                book_slug=book_slug,
                chapter=chapter,
                audio_hash=audio_hash,
                sentence_chunk_map=sentence_chunk_map,
            )
        ),
    }
    if manual_chunk_sample or full_chapter:
        sync_manifest["chunks"] = chunks

    imported_manifest_path = sample_dir / "imported_audio_manifest.json"
    sync_manifest_path = sample_dir / "sync_manifest.json"
    imported_manifest_path.write_text(json.dumps(imported_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_manifest_path.write_text(json.dumps(sync_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if manual_chunk_sample:
        combined_sample_manifest = {
            "generated_by": "scripts/elevenlabs_internal_sample_import.py",
            "generated_at": generated_at,
            "book_slug": book_slug,
            "chapter": int(chapter),
            "provider": expected_manifest.get("provider") or "ElevenLabs",
            "voice": expected_manifest.get("voice_name") or "Rachel",
            "voice_name": expected_manifest.get("voice_name") or "Rachel",
            "voice_id": expected_manifest.get("voice_id") or "21m00Tcm4TlvDq8ikWAM",
            "status": INTERNAL_SAMPLE_ONLY,
            "audio_status": INTERNAL_SAMPLE_ONLY,
            "sync_status": HOLD_SYNC_QA_REQUIRED,
            "chunk_count": len(chunks),
            "chunks": chunks,
            "combined_audio_hash": audio_hash,
            "production_status": PRODUCTION_BLOCKED,
            "production_approved": False,
            "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "public_audio_allowed": False,
            "provider_api_called": False,
            "audio_generated_by_repo": False,
            "listen_now_cta_allowed": False,
            "audio_object_metadata_allowed": False,
            "timing_qa_passed": False,
            "manual_download_validation_report_path": str(manual_validation_report_path.relative_to(ROOT)),
            "expected_audio_filenames_path": str(expected_manifest_path.relative_to(ROOT)),
            "imported_audio_manifest_path": str(imported_manifest_path.relative_to(ROOT)),
            "sync_manifest_path": str(sync_manifest_path.relative_to(ROOT)),
        }
        combined_sample_manifest_path = sample_dir / "combined_sample_manifest.json"
        combined_sample_manifest_path.write_text(
            json.dumps(combined_sample_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return {
        "status": audio_status,
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "audio_hash": audio_hash,
        "audio_path": audio_relative,
        "chunk_count": len(chunks),
        "imported_audio_manifest_path": str(imported_manifest_path.relative_to(ROOT)),
        "sync_manifest_path": str(sync_manifest_path.relative_to(ROOT)),
        "combined_sample_manifest_path": (
            str(combined_sample_manifest_path.relative_to(ROOT)) if combined_sample_manifest_path else None
        ),
        "public_audio_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--sample-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = run_import(book_slug=args.book_slug, chapter=args.chapter, sample_dir=args.sample_dir)
    except Exception as exc:  # noqa: BLE001 - CLI should produce a concise validation error.
        print(f"ElevenLabs internal sample import failed: {exc}", file=sys.stderr)
        return 2

    print(
        "ElevenLabs internal sample import complete: "
        f"status={result['status']} sync={result['sync_status']} "
        f"chunks={result['chunk_count']} audio_hash={result['audio_hash']} public_audio_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
