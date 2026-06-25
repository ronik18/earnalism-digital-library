#!/usr/bin/env python3
"""Prepare clean chunk files for owner-run ElevenLabs manual generation.

This script never calls ElevenLabs, generates audio, opens a browser, or writes
audio into frontend/public or frontend/build. It only exports already-validated
chunk narration text and a checklist for the owner to use in the ElevenLabs UI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audiobook_chapter_pipeline import run_chapter_pipeline  # noqa: E402
from scripts.validate_elevenlabs_narration_text import (  # noqa: E402
    NarrationValidationError,
    sha256_text,
    validate_sample_dir,
    validate_text,
)


INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
DEFAULT_PROVIDER = "elevenlabs"
DEFAULT_VOICE_NAME = "Rachel"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def chapter_dir(book_slug: str, language: str, chapter: int | str) -> Path:
    return INTERNAL_AUDIOBOOK_ROOT / safe_slug(book_slug) / language.lower() / f"chapter-{int(chapter)}"


def ensure_internal_path(path: Path, label: str) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay under {relative_path(INTERNAL_AUDIOBOOK_ROOT)}") from exc

    public_roots = [ROOT / "frontend" / "public", ROOT / "frontend" / "build"]
    for public_root in public_roots:
        try:
            resolved.relative_to(public_root.resolve())
        except ValueError:
            continue
        raise ValueError(f"{label} must not be under {relative_path(public_root)}")


def load_chunk_manifest(sample_dir: Path) -> dict[str, Any]:
    path = sample_dir / "chunk_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"chunk_manifest.json not found: {relative_path(path)}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    chunks = manifest.get("chunks") if isinstance(manifest, dict) else None
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"{relative_path(path)} must contain a non-empty chunks list")
    return manifest


def parse_chunk_selection(manifest: dict[str, Any], *, chunks: str | None, all_chunks: bool) -> list[dict[str, Any]]:
    manifest_chunks = manifest["chunks"]
    by_id = {str(chunk.get("chunk_id")): chunk for chunk in manifest_chunks}
    ordered_ids = [str(chunk.get("chunk_id")) for chunk in manifest_chunks]

    if all_chunks:
        selected_ids = ordered_ids
    elif chunks:
        selected_ids = []
        for raw_token in chunks.split(","):
            token = raw_token.strip()
            if not token:
                continue
            range_match = re.fullmatch(r"(c\d{3})-(c\d{3})", token, re.IGNORECASE)
            if range_match:
                start = int(range_match.group(1)[1:])
                end = int(range_match.group(2)[1:])
                if end < start:
                    raise ValueError(f"chunk range must be ascending: {token}")
                selected_ids.extend(f"c{index:03d}" for index in range(start, end + 1))
            else:
                if not re.fullmatch(r"c\d{3}", token, re.IGNORECASE):
                    raise ValueError(f"invalid chunk selector: {token}")
                selected_ids.append(token.lower())
    else:
        raise ValueError("pass --chunks c001-c003 or --all")

    deduped_ids: list[str] = []
    for chunk_id in selected_ids:
        if chunk_id not in by_id:
            raise ValueError(f"unknown chunk_id: {chunk_id}")
        if chunk_id not in deduped_ids:
            deduped_ids.append(chunk_id)
    return [by_id[chunk_id] for chunk_id in deduped_ids]


def assert_clean_chunk(chunk: dict[str, Any]) -> None:
    chunk_id = str(chunk.get("chunk_id") or "unknown")
    text = str(chunk.get("narration_text") or "")
    failures = validate_text(f"{chunk_id}.narration_text", text)
    if failures:
        raise NarrationValidationError(failures)


def audio_filename_for(book_slug: str, chapter: int | str, chunk: dict[str, Any]) -> str:
    existing = str(chunk.get("audio_filename") or "").strip()
    if existing:
        return existing
    chunk_id = str(chunk.get("chunk_id"))
    return f"{safe_slug(book_slug)}-chapter-{int(chapter)}-elevenlabs-rachel-{chunk_id}.mp3"


def expected_audio_payload(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    sample_dir: Path,
    manual_dir: Path,
    imported_audio_dir: Path,
    selected_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    for chunk in selected_chunks:
        chunk_id = str(chunk["chunk_id"])
        audio_filename = audio_filename_for(book_slug, chapter, chunk)
        chunks.append(
            {
                "chunk_id": chunk_id,
                "audio_filename": audio_filename,
                "expected_audio_path": relative_path(imported_audio_dir / audio_filename),
                "chunk_text_path": relative_path(manual_dir / f"{chunk_id}.txt"),
                "sentence_ids": chunk.get("sentence_ids", []),
                "text_hash": chunk.get("text_hash") or sha256_text(str(chunk.get("narration_text") or "")),
                "settings_hash": chunk.get("settings_hash"),
                "estimated_duration_seconds": chunk.get("estimated_duration_seconds"),
                "generation_status": "PENDING_MANUAL_UI_GENERATION",
                "public": False,
            }
        )

    return {
        "generated_by": "scripts/prepare_elevenlabs_manual_generation.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "language": language.lower(),
        "chapter": chapter,
        "provider": "ElevenLabs",
        "voice_name": DEFAULT_VOICE_NAME,
        "voice_id": DEFAULT_VOICE_ID,
        "source_chunk_manifest": relative_path(sample_dir / "chunk_manifest.json"),
        "manual_chunk_dir": relative_path(manual_dir),
        "imported_audio_dir": relative_path(imported_audio_dir),
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": "PRODUCTION_BLOCKED",
        "production_approved": False,
        "chunks": chunks,
    }


def readme_text(book_slug: str, language: str, chapter: int) -> str:
    return "\n".join(
        [
            "# Manual ElevenLabs Chunk Exports",
            "",
            f"- Book: `{safe_slug(book_slug)}`",
            f"- Language: `{language.lower()}`",
            f"- Chapter: `{chapter}`",
            "- These `.txt` files are clean narration text only.",
            "- Copy one chunk at a time into the ElevenLabs UI.",
            "- Download generated audio into `../imported_audio/` using the expected filenames manifest.",
            "- Do not upload generated audio to `frontend/public` or `frontend/build`.",
            "- This workflow does not call the ElevenLabs API or generate audio from the repo.",
            "",
        ]
    )


def checklist_text(expected: dict[str, Any]) -> str:
    chunk_lines = [
        f"{index}. `{chunk['chunk_id']}.txt` -> `{chunk['audio_filename']}`"
        for index, chunk in enumerate(expected["chunks"], start=1)
    ]
    return "\n".join(
        [
            "# Manual ElevenLabs Generation Checklist",
            "",
            "## Settings",
            "",
            "- Voice: Rachel",
            "- Voice ID: `21m00Tcm4TlvDq8ikWAM`",
            "- Model: Eleven Multilingual v2 or same stable non-beta model used in approved sample",
            "- Speed: 0.85",
            "- Stability: 60-65%",
            "- Similarity: 75-80%",
            "- Style Exaggeration: 5-10%",
            "- Speaker Boost: On",
            "- No beta services",
            "- No voice cloning",
            "- No ElevenReader",
            "",
            "## Copy Order And Expected Filenames",
            "",
            "- Use the ElevenLabs UI/Studio manually; this repo must not call the ElevenLabs API.",
            "- Generate one chunk at a time, in the exact order below.",
            "- Use voice Rachel / `21m00Tcm4TlvDq8ikWAM` for every chunk.",
            "- Use no beta services, no voice cloning, and no ElevenReader.",
            "- Download each generated audio file using the exact expected filename shown below.",
            "- Regenerate only failed chunks after QA; do not regenerate chunks that already pass.",
            "",
            *chunk_lines,
            "",
            "## Save Location",
            "",
            f"- Save downloads only under `{expected['imported_audio_dir']}/`.",
            "- Do not upload generated audio to `frontend/public` or `frontend/build`.",
            "- Keep this as internal review audio until every release gate is explicitly approved.",
            "- Do not publish audio, add public listening calls to action, add structured audio metadata, or mark production approved.",
            "",
        ]
    )


def prepare_manual_generation(
    *,
    book_slug: str,
    language: str,
    chapter: int | str,
    chunks: str | None = None,
    all_chunks: bool = False,
    run_pipeline: bool = True,
) -> dict[str, Any]:
    chapter_number = int(chapter)
    sample_dir = chapter_dir(book_slug, language, chapter_number)
    ensure_internal_path(sample_dir, "chapter directory")

    if run_pipeline:
        run_chapter_pipeline(
            book_slug=book_slug,
            language=language,
            chapter=chapter_number,
            provider=DEFAULT_PROVIDER,
            voice_id=DEFAULT_VOICE_ID,
            voice_name=DEFAULT_VOICE_NAME,
            mode="dry-run",
            write_root_reports=False,
        )

    validation_summary = validate_sample_dir(sample_dir)
    manifest = load_chunk_manifest(sample_dir)
    selected_chunks = parse_chunk_selection(manifest, chunks=chunks, all_chunks=all_chunks)
    for chunk in selected_chunks:
        assert_clean_chunk(chunk)

    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    imported_audio_dir = sample_dir / "imported_audio"
    ensure_internal_path(manual_dir, "manual chunk directory")
    ensure_internal_path(imported_audio_dir, "imported audio directory")
    manual_dir.mkdir(parents=True, exist_ok=True)
    imported_audio_dir.mkdir(parents=True, exist_ok=True)

    selected_ids = {str(chunk["chunk_id"]) for chunk in selected_chunks}
    for stale_path in manual_dir.glob("c*.txt"):
        if stale_path.stem not in selected_ids:
            stale_path.unlink()

    exported: list[str] = []
    for chunk in selected_chunks:
        chunk_id = str(chunk["chunk_id"])
        chunk_path = manual_dir / f"{chunk_id}.txt"
        chunk_path.write_text(str(chunk["narration_text"]).rstrip() + "\n", encoding="utf-8")
        exported.append(relative_path(chunk_path))

    expected = expected_audio_payload(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        sample_dir=sample_dir,
        manual_dir=manual_dir,
        imported_audio_dir=imported_audio_dir,
        selected_chunks=selected_chunks,
    )
    expected_path = manual_dir / "expected_audio_filenames.json"
    expected_path.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme_path = manual_dir / "README.md"
    checklist_path = manual_dir / "generation_checklist.md"
    readme_path.write_text(readme_text(book_slug, language, chapter_number), encoding="utf-8")
    checklist_path.write_text(checklist_text(expected), encoding="utf-8")

    return {
        "status": "MANUAL_ELEVENLABS_CHUNKS_READY",
        "chapter_dir": relative_path(sample_dir),
        "manual_chunk_dir": relative_path(manual_dir),
        "imported_audio_dir": relative_path(imported_audio_dir),
        "exported_chunks": exported,
        "exported_chunk_count": len(exported),
        "readme_path": relative_path(readme_path),
        "checklist_path": relative_path(checklist_path),
        "expected_audio_filenames_path": relative_path(expected_path),
        "validation_summary": validation_summary,
        "provider_api_called": False,
        "audio_generated_by_repo": False,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--chapter", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--chunks", help="Chunk selector such as c001-c003 or c001,c003")
    selection.add_argument("--all", action="store_true", help="Export all chunks from chunk_manifest.json")
    args = parser.parse_args()

    try:
        result = prepare_manual_generation(
            book_slug=args.book_slug,
            language=args.language,
            chapter=args.chapter,
            chunks=args.chunks,
            all_chunks=args.all,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should print concise actionable failure.
        print(f"Manual ElevenLabs preparation failed: {exc}", file=sys.stderr)
        return 2

    print(
        "Manual ElevenLabs chunk preparation complete: "
        f"status={result['status']} exported_chunks={result['exported_chunk_count']} "
        f"manual_chunk_dir={result['manual_chunk_dir']} "
        f"checklist={result['checklist_path']} "
        f"expected_audio={result['expected_audio_filenames_path']} "
        "provider_api_called=false audio_generated_by_repo=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
