#!/usr/bin/env python3
"""Copy a prepared ElevenLabs chunk to the macOS clipboard when available."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_elevenlabs_manual_generation import (  # noqa: E402
    chapter_dir,
    ensure_internal_path,
    relative_path,
)


def chunk_text_path(book_slug: str, language: str, chapter: int | str, chunk: str) -> Path:
    chunk_id = chunk.lower()
    if not chunk_id.startswith("c"):
        chunk_id = f"c{int(chunk_id):03d}"
    path = chapter_dir(book_slug, language, chapter) / "manual_elevenlabs_chunks" / f"{chunk_id}.txt"
    ensure_internal_path(path.parent, "manual chunk directory")
    return path


def manual_chunks_dir(book_slug: str, language: str, chapter: int | str) -> Path:
    path = chapter_dir(book_slug, language, chapter) / "manual_elevenlabs_chunks"
    ensure_internal_path(path, "manual chunk directory")
    return path


def list_manual_chunks(*, book_slug: str, language: str, chapter: int | str) -> list[dict[str, str | int]]:
    manual_dir = manual_chunks_dir(book_slug, language, chapter)
    expected_path = manual_dir / "expected_audio_filenames.json"
    if not expected_path.exists():
        raise FileNotFoundError(
            f"Expected audio manifest not found: {relative_path(expected_path)}. "
            "Run the manual preparation command first."
        )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    chunks = expected.get("chunks", [])
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"{relative_path(expected_path)} does not contain a non-empty chunks list.")

    rows: list[dict[str, str | int]] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = str(chunk.get("chunk_id") or "")
        text_path = ROOT / str(chunk.get("chunk_text_path") or "")
        ensure_internal_path(text_path.parent, "manual chunk text directory")
        if not text_path.exists():
            raise FileNotFoundError(f"Prepared chunk file not found: {relative_path(text_path)}")
        rows.append(
            {
                "order": index,
                "chunk_id": chunk_id,
                "text_path": relative_path(text_path),
                "expected_audio_filename": str(chunk.get("audio_filename") or ""),
            }
        )
    return rows


def copy_chunk_to_clipboard(
    *,
    book_slug: str,
    language: str,
    chapter: int | str,
    chunk: str,
    pbcopy_path: str | None = None,
) -> dict[str, str | bool]:
    path = chunk_text_path(book_slug, language, chapter, chunk)
    if not path.exists():
        raise FileNotFoundError(
            f"Prepared chunk file not found: {relative_path(path)}. "
            "Run the manual preparation command first."
        )
    text = path.read_text(encoding="utf-8")
    pbcopy = pbcopy_path if pbcopy_path is not None else shutil.which("pbcopy")
    if pbcopy:
        subprocess.run([pbcopy], input=text, text=True, check=True)
        return {"copied_to_clipboard": True, "chunk_path": relative_path(path), "text": text}
    return {"copied_to_clipboard": False, "chunk_path": relative_path(path), "text": text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--chunk")
    parser.add_argument("--list", action="store_true", help="List prepared manual chunks instead of copying one.")
    args = parser.parse_args()

    try:
        if args.list:
            rows = list_manual_chunks(book_slug=args.book_slug, language=args.language, chapter=args.chapter)
            print("order\tchunk_id\ttext_path\texpected_audio_filename")
            for row in rows:
                print(
                    f"{row['order']}\t{row['chunk_id']}\t{row['text_path']}\t"
                    f"{row['expected_audio_filename']}"
                )
            return 0
        if not args.chunk:
            raise ValueError("--chunk is required unless --list is passed.")
        result = copy_chunk_to_clipboard(
            book_slug=args.book_slug,
            language=args.language,
            chapter=args.chapter,
            chunk=args.chunk,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should print concise actionable failure.
        print(f"Copy helper failed: {exc}", file=sys.stderr)
        return 2

    if result["copied_to_clipboard"]:
        print(f"Copied {result['chunk_path']} to clipboard.")
    else:
        print(f"pbcopy unavailable. Printing {result['chunk_path']}:\n")
        print(str(result["text"]).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
