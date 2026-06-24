#!/usr/bin/env python3
"""Copy a prepared ElevenLabs chunk to the macOS clipboard when available."""

from __future__ import annotations

import argparse
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
    parser.add_argument("--chunk", required=True)
    args = parser.parse_args()

    try:
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
