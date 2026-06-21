#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "BENGALI_TEXT_NORMALIZATION_REPORT.md"
PRONUNCIATION_NOTES = ROOT / "data/audiobook_generation/kshudhita-pashan/pronunciation_notes.json"

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
QUOTE_TRANSLATION = str.maketrans(
    {
        "“": "\"",
        "”": "\"",
        "‘": "'",
        "’": "'",
        "«": "\"",
        "»": "\"",
    }
)


def normalize_bengali_text(text: str) -> str:
    normalized = text.translate(BENGALI_DIGITS).translate(QUOTE_TRANSLATION)
    normalized = normalized.replace("…", "...")
    normalized = re.sub(r"\s*--+\s*", " - ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\s+([,;:!?।])", r"\1", normalized)
    normalized = re.sub(r"([,;:!?।])(?=[^\s\"'])", r"\1 ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def punctuation_profile(text: str) -> dict[str, int]:
    return {
        "danda": text.count("।"),
        "comma": text.count(","),
        "question": text.count("?"),
        "exclamation": text.count("!"),
        "ellipsis": text.count("...") + text.count("…"),
        "dash": text.count("-") + text.count("—"),
        "quotes": sum(text.count(mark) for mark in ("\"", "'", "“", "”", "‘", "’")),
    }


def normalization_notes(original: str, normalized: str) -> list[str]:
    notes: list[str] = []
    if original != normalized:
        notes.append("Whitespace, punctuation, quote marks, or Bengali digits were normalized.")
    if re.search(r"[০-৯]", original):
        notes.append("Bengali digits were converted for model consistency while original text remains preserved.")
    if any(mark in original for mark in ("“", "”", "‘", "’", "…", "—")):
        notes.append("Curly quotes, ellipsis, or dash forms were normalized without changing literary wording.")
    if re.search(r"[\u0980-\u09FF]+", original):
        notes.append("Bengali script detected; preserve Tagore-era diction and Sanskritized compounds.")
    return notes or ["No destructive normalization required."]


def normalize_payload(text: str) -> dict[str, Any]:
    normalized = normalize_bengali_text(text)
    return {
        "original_text": text,
        "normalized_text": normalized,
        "original_character_count": len(text),
        "normalized_character_count": len(normalized),
        "punctuation_profile": punctuation_profile(normalized),
        "notes": normalization_notes(text, normalized),
    }


def write_report(payload: dict[str, Any], output_path: Path = DEFAULT_OUTPUT) -> None:
    lines = [
        "# Bengali Text Normalization Report",
        "",
        "Scope: `INTERNAL_REVIEW_ONLY`.",
        "",
        "No source text was rewritten destructively. Original and normalized text are kept side-by-side for operator review.",
        "",
        "## Counts",
        "",
        f"- Original characters: `{payload['original_character_count']}`",
        f"- Normalized characters: `{payload['normalized_character_count']}`",
        "",
        "## Punctuation Profile",
        "",
    ]
    for key, value in payload["punctuation_profile"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in payload["notes"])
    if PRONUNCIATION_NOTES.exists():
        lines.extend(["", f"Pronunciation notes: `{PRONUNCIATION_NOTES.relative_to(ROOT)}`"])
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize Bengali text for internal audiobook benchmarking.")
    parser.add_argument("--text", default="")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input:
        text = args.input.read_text(encoding="utf-8")
    else:
        text = args.text or "ক্ষুধিত পাষাণ। এক অদ্ভুত নীরবতা চারিদিকে।"
    payload = normalize_payload(text)
    write_report(payload, args.output)
    print(f"Bengali normalization report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
