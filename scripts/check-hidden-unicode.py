#!/usr/bin/env python3
"""Fail when source files contain hidden Unicode controls or CR-only lines."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BLOCKED_CODEPOINTS = {
    **{codepoint: "bidirectional control" for codepoint in range(0x202A, 0x202F)},
    **{codepoint: "bidirectional isolate" for codepoint in range(0x2066, 0x206A)},
    0x200B: "zero-width space",
    0x200C: "zero-width non-joiner",
    0x200D: "zero-width joiner",
    0xFEFF: "byte-order mark / zero-width no-break space",
}


def changed_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    column = index + 1 if last_newline == -1 else index - last_newline
    return line, column


def scan_file(path: Path) -> list[str]:
    problems: list[str] = []
    data = path.read_bytes()

    index = 0
    while index < len(data):
        if data[index : index + 1] == b"\r" and data[index + 1 : index + 2] != b"\n":
            problems.append(f"{path}: CR-only line ending near byte {index}")
        index += 1

    text = data.decode("utf-8", errors="replace")
    for position, char in enumerate(text):
        codepoint = ord(char)
        reason = BLOCKED_CODEPOINTS.get(codepoint)
        if reason:
            line, column = line_column(text, position)
            problems.append(f"{path}:{line}:{column}: U+{codepoint:04X} {reason}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Files to scan. Defaults to changed files.")
    args = parser.parse_args()

    files = args.files or changed_files()
    problems: list[str] = []
    for path in files:
        if path.is_file():
            problems.extend(scan_file(path))

    if problems:
        print("Hidden Unicode / line-ending check failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print(f"Hidden Unicode / line-ending check passed for {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
