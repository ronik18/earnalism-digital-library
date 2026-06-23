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
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"


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


def sentence_items(sample_text: str, *, book_slug: str, chapter: str, audio_hash: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, raw_line in enumerate(sample_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^\[(s\d{3})\]\s*(.+)$", line)
        sentence_id = match.group(1) if match else f"s{index:03d}"
        text = match.group(2).strip() if match else line
        items.append(
            {
                "text_fragment_id": f"{book_slug}-chapter-{int(chapter):03d}-{sentence_id}",
                "sentence_id": sentence_id,
                "chapter": int(chapter),
                "text": text,
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


def find_imported_audio(imported_audio_dir: Path) -> list[Path]:
    if not imported_audio_dir.exists():
        return []
    return sorted(
        path for path in imported_audio_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS
    )


def run_import(*, book_slug: str, chapter: str, sample_dir: Path) -> dict[str, Any]:
    sample_dir = sample_dir if sample_dir.is_absolute() else ROOT / sample_dir
    ensure_under(sample_dir, INTERNAL_AUDIOBOOK_ROOT, "sample-dir")
    public_audio = public_audio_files()
    if public_audio:
        raise ValueError("public audio files are present: " + ", ".join(public_audio))

    sample_text_path = sample_dir / "sample_text.txt"
    if not sample_text_path.exists():
        raise FileNotFoundError(f"sample_text.txt not found: {sample_text_path}")

    imported_audio_dir = sample_dir / "imported_audio"
    audio_files = find_imported_audio(imported_audio_dir)
    if not audio_files:
        raise FileNotFoundError(f"No imported audio file found under {imported_audio_dir.relative_to(ROOT)}")
    if len(audio_files) > 1:
        raise ValueError("Exactly one imported audio file is allowed for this internal sample.")

    audio_path = audio_files[0]
    ensure_under(audio_path, INTERNAL_AUDIOBOOK_ROOT, "imported audio")
    audio_hash = sha256_file(audio_path)
    sample_text = sample_text_path.read_text(encoding="utf-8")
    generated_at = utc_now()
    audio_relative = str(audio_path.relative_to(ROOT))

    imported_manifest = {
        "generated_by": "scripts/elevenlabs_internal_sample_import.py",
        "generated_at": generated_at,
        "book_slug": book_slug,
        "chapter": int(chapter),
        "provider": "ElevenLabs",
        "voice_name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "audio_status": INTERNAL_SAMPLE_ONLY,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_approved": False,
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "audio_path": audio_relative,
        "audio_hash": audio_hash,
        "text_hash": sha256_text(sample_text),
        "sample_dir": str(sample_dir.relative_to(ROOT)),
    }
    sync_manifest = {
        "generated_by": "scripts/elevenlabs_internal_sample_import.py",
        "generated_at": generated_at,
        "book_slug": book_slug,
        "chapter": int(chapter),
        "provider": "ElevenLabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "sync_level": "sentence",
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "audio_status": INTERNAL_SAMPLE_ONLY,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public": False,
        "items": sentence_items(sample_text, book_slug=book_slug, chapter=chapter, audio_hash=audio_hash),
    }

    imported_manifest_path = sample_dir / "imported_audio_manifest.json"
    sync_manifest_path = sample_dir / "sync_manifest.json"
    imported_manifest_path.write_text(json.dumps(imported_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_manifest_path.write_text(json.dumps(sync_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "status": INTERNAL_SAMPLE_ONLY,
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "audio_hash": audio_hash,
        "audio_path": audio_relative,
        "imported_audio_manifest_path": str(imported_manifest_path.relative_to(ROOT)),
        "sync_manifest_path": str(sync_manifest_path.relative_to(ROOT)),
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
        f"audio_hash={result['audio_hash']} public_audio_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
