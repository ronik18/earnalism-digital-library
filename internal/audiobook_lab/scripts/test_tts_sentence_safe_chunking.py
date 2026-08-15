#!/usr/bin/env python3
"""Regression checks for sentence-safe OpenAI TTS chunking."""

from __future__ import annotations

import sys
from pathlib import Path


HOOK_DIR = Path(__file__).resolve().parent / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from common import normalize_text  # noqa: E402
from tts_hook import chunk_text  # noqa: E402


def main() -> int:
    wrapped = (
        "I felt a faint tug,\n\n"
        "and took a fresh grip. The pull stopped.\n\n"
        "Then I became conscious that the room was quiet."
    )
    chunks = chunk_text(wrapped, max_chars=50)
    rebuilt = " ".join(item["text"] for item in chunks)
    assert normalize_text(rebuilt) == normalize_text(wrapped), chunks
    assert all(len(item["text"]) <= 50 for item in chunks), chunks
    assert chunks[0]["text"].endswith("grip."), chunks
    assert not any(item["text"].startswith("and took") for item in chunks[1:]), chunks
    assert all(item["text"][-1] in ".!?।" for item in chunks), chunks

    quoted = (
        '“How far is it?” Farquhar asked. '
        '“About thirty miles.” “Is there no force?” '
        '“Put it back!” He thought he shouted.'
    )
    quoted_chunks = chunk_text(quoted, max_chars=25)
    rebuilt_quoted = " ".join(item["text"] for item in quoted_chunks)
    assert normalize_text(rebuilt_quoted) == normalize_text(quoted), quoted_chunks
    assert len(quoted_chunks) == 6, quoted_chunks
    assert quoted_chunks[0]["text"] == '“How far is it?”', quoted_chunks
    assert quoted_chunks[2]["text"] == '“About thirty miles.”', quoted_chunks
    assert quoted_chunks[4]["text"] == '“Put it back!”', quoted_chunks
    print("TTS sentence-safe chunking regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
