#!/usr/bin/env python3
"""Scan files for hidden Unicode controls and CR-only line endings."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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

BENGALI_RANGE = range(0x0980, 0x0A00)

BINARY_SUFFIXES = {
    ".aac",
    ".avif",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".pdf",
    ".png",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
}


def is_binary_path(path: Path) -> bool:
    return path.suffix.lower() in BINARY_SUFFIXES


def blocked_reason(codepoint: int) -> str | None:
    for blocked_range in BLOCKED_RANGES:
        if codepoint in blocked_range:
            return "bidirectional Unicode control"
    return BLOCKED_POINTS.get(codepoint)


def has_bengali_neighbor(text: str, index: int) -> bool:
    """Allow ZWNJ only when it is part of Bengali-script source text."""
    start = max(0, index - 2)
    end = min(len(text), index + 3)
    return any(ord(character) in BENGALI_RANGE for character in text[start:index] + text[index + 1 : end])


def default_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def line_and_column(text: str, index: int) -> tuple[int, int]:
    line_number = text.count("\n", 0, index) + 1
    previous_newline = text.rfind("\n", 0, index)
    column_number = index + 1 if previous_newline == -1 else index - previous_newline
    return line_number, column_number


def scan_file(path: Path) -> list[str]:
    data = path.read_bytes()
    errors: list[str] = []

    for index, byte in enumerate(data):
        if byte == 0x0D and data[index + 1 : index + 2] != b"\n":
            errors.append(f"{path}: CR-only line ending near byte {index}")

    text = data.decode("utf-8", errors="replace")
    for index, character in enumerate(text):
        if ord(character) == 0x200C and has_bengali_neighbor(text, index):
            continue
        reason = blocked_reason(ord(character))
        if reason:
            line_number, column_number = line_and_column(text, index)
            errors.append(f"{path}:{line_number}:{column_number}: U+{ord(character):04X} {reason}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()

    paths = args.files or default_files()
    errors: list[str] = []
    scanned = 0
    skipped_binary = 0
    for path in paths:
        if path.is_file():
            if is_binary_path(path):
                skipped_binary += 1
                continue
            scanned += 1
            errors.extend(scan_file(path))

    if errors:
        print("Hidden Unicode / line-ending check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    suffix = f"; skipped {skipped_binary} binary file(s)" if skipped_binary else ""
    print(f"Hidden Unicode / line-ending check passed for {scanned} file(s){suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
