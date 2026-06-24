#!/usr/bin/env python3
"""Validate owner-downloaded ElevenLabs chunk audio before internal import."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_elevenlabs_manual_generation import (  # noqa: E402
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    chapter_dir,
    ensure_internal_path,
    relative_path,
)


AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def expected_manifest_path(book_slug: str, language: str, chapter: int | str) -> Path:
    return chapter_dir(book_slug, language, chapter) / "manual_elevenlabs_chunks" / "expected_audio_filenames.json"


def load_expected_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"expected audio manifest not found: {relative_path(path)}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    chunks = manifest.get("chunks") if isinstance(manifest, dict) else None
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"{relative_path(path)} must contain a non-empty chunks list")
    return manifest


def list_audio_files(imported_audio_dir: Path) -> list[Path]:
    if not imported_audio_dir.exists():
        return []
    return sorted(
        path for path in imported_audio_dir.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS
    )


def markdown_report(report: dict[str, Any]) -> str:
    present_rows = [
        f"| {item['chunk_id']} | `{item['audio_filename']}` | `{item['audio_hash']}` |"
        for item in report["present_audio"]
    ]
    missing_rows = [
        f"| {item['chunk_id']} | `{item['audio_filename']}` |" for item in report["missing_audio"]
    ]
    unexpected_rows = [f"| `{item['path']}` | `{item['audio_hash']}` |" for item in report["unexpected_audio"]]
    blockers = [f"- {blocker}" for blocker in report["blockers"]]
    return "\n".join(
        [
            "# Manual ElevenLabs Download Validation Report",
            "",
            f"- Status: `{report['status']}`",
            f"- Expected chunks: `{report['expected_chunk_count']}`",
            f"- Present chunks: `{len(report['present_audio'])}`",
            f"- Missing chunks: `{len(report['missing_audio'])}`",
            f"- Unexpected audio files: `{len(report['unexpected_audio'])}`",
            f"- Public audio: `{report['public_audio_release']}`",
            f"- Production approved: `{str(report['production_approved']).lower()}`",
            "",
            "## Blockers",
            "",
            *(blockers or ["- None."]),
            "",
            "## Present Expected Audio",
            "",
            "| Chunk | File | SHA-256 |",
            "| --- | --- | --- |",
            *(present_rows or ["| None | None | None |"]),
            "",
            "## Missing Expected Audio",
            "",
            "| Chunk | File |",
            "| --- | --- |",
            *(missing_rows or ["| None | None |"]),
            "",
            "## Unexpected Audio",
            "",
            "| File | SHA-256 |",
            "| --- | --- |",
            *(unexpected_rows or ["| None | None |"]),
            "",
        ]
    )


def validate_manual_downloads(
    *,
    book_slug: str,
    language: str,
    chapter: int | str,
    public_audio_override: list[str] | None = None,
) -> dict[str, Any]:
    manifest_path = expected_manifest_path(book_slug, language, chapter)
    manifest = load_expected_manifest(manifest_path)
    manual_dir = manifest_path.parent
    sample_dir = manual_dir.parent
    imported_audio_dir = sample_dir / "imported_audio"
    ensure_internal_path(imported_audio_dir, "imported audio directory")
    imported_audio_dir.mkdir(parents=True, exist_ok=True)

    expected_by_name = {str(chunk["audio_filename"]): chunk for chunk in manifest["chunks"]}
    blockers: list[str] = []
    present_audio: list[dict[str, Any]] = []
    missing_audio: list[dict[str, Any]] = []

    for chunk in manifest["chunks"]:
        chunk_id = str(chunk["chunk_id"])
        audio_filename = str(chunk["audio_filename"])
        expected_path = imported_audio_dir / audio_filename
        manifest_expected_path = ROOT / str(chunk.get("expected_audio_path", ""))
        try:
            ensure_internal_path(manifest_expected_path, "expected audio path")
        except ValueError as exc:
            blockers.append(str(exc))
        if expected_path.exists():
            ensure_internal_path(expected_path, "downloaded audio file")
            present_audio.append(
                {
                    "chunk_id": chunk_id,
                    "audio_filename": audio_filename,
                    "path": relative_path(expected_path),
                    "audio_hash": sha256_file(expected_path),
                    "file_size_bytes": expected_path.stat().st_size,
                    "public": False,
                }
            )
        else:
            missing_audio.append(
                {
                    "chunk_id": chunk_id,
                    "audio_filename": audio_filename,
                    "expected_audio_path": relative_path(expected_path),
                }
            )

    unexpected_audio: list[dict[str, Any]] = []
    for audio_path in list_audio_files(imported_audio_dir):
        if audio_path.name in expected_by_name:
            continue
        ensure_internal_path(audio_path, "unexpected downloaded audio file")
        unexpected_audio.append(
            {
                "path": relative_path(audio_path),
                "audio_hash": sha256_file(audio_path),
                "file_size_bytes": audio_path.stat().st_size,
                "public": False,
            }
        )

    public_audio = public_audio_override if public_audio_override is not None else public_audio_files()
    if missing_audio:
        blockers.append("missing expected manual downloads")
    if unexpected_audio:
        blockers.append("unexpected audio files in imported_audio")
    if public_audio:
        blockers.append("audio files are present under frontend/public or frontend/build")

    status = "READY_FOR_INTERNAL_IMPORT" if not blockers else "HOLD_MANUAL_DOWNLOADS_REQUIRED"
    report = {
        "generated_by": "scripts/validate_elevenlabs_manual_downloads.py",
        "generated_at": utc_now(),
        "status": status,
        "book_slug": manifest.get("book_slug"),
        "language": manifest.get("language"),
        "chapter": manifest.get("chapter"),
        "expected_manifest_path": relative_path(manifest_path),
        "imported_audio_dir": relative_path(imported_audio_dir),
        "expected_chunk_count": len(manifest["chunks"]),
        "present_audio": present_audio,
        "missing_audio": missing_audio,
        "unexpected_audio": unexpected_audio,
        "public_audio_files": public_audio,
        "blockers": blockers,
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_approved": False,
    }

    json_path = manual_dir / "manual_download_validation_report.json"
    md_path = manual_dir / "manual_download_validation_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    report["manual_download_validation_report_json"] = relative_path(json_path)
    report["manual_download_validation_report_md"] = relative_path(md_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--chapter", required=True)
    args = parser.parse_args()

    try:
        report = validate_manual_downloads(book_slug=args.book_slug, language=args.language, chapter=args.chapter)
    except Exception as exc:  # noqa: BLE001 - CLI should print concise actionable failure.
        print(f"Manual ElevenLabs download validation failed: {exc}", file=sys.stderr)
        return 2

    print(
        "Manual ElevenLabs download validation complete: "
        f"status={report['status']} expected={report['expected_chunk_count']} "
        f"present={len(report['present_audio'])} missing={len(report['missing_audio'])} "
        f"unexpected={len(report['unexpected_audio'])} "
        f"public_audio_files={len(report['public_audio_files'])} "
        f"report={report['manual_download_validation_report_json']}"
    )
    return 0 if report["status"] == "READY_FOR_INTERNAL_IMPORT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
