#!/usr/bin/env python3
"""Normalize English source text for internal audiobook model bake-offs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ABBREVIATION_REPLACEMENTS = {
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Dr.": "Doctor",
    "Prof.": "Professor",
    "St.": "Saint",
    "P. M.": "P M",
    "A. M.": "A M",
    "P.M.": "P M",
    "A.M.": "A M",
}

PRONUNCIATION_NOTES = {
    "Bistritz": "BIS-tritz",
    "Buda-Pesth": "BOO-duh Pest",
    "Carpathians": "kar-PAY-thee-uhns",
    "Harker": "HAR-ker",
    "Jonathan Harker": "JON-uh-thun HAR-ker",
    "Mina": "MEE-nuh",
    "Transylvania": "tran-sil-VAY-nee-uh",
    "Dracula": "DRAK-yoo-luh",
    "Szekely": "SAY-kay",
}


@dataclass(frozen=True)
class NormalizationResult:
    original_text: str
    normalized_text: str
    replacements: dict[str, int]
    punctuation_notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "replacements": self.replacements,
            "punctuation_notes": self.punctuation_notes,
        }


def normalize_english_text(text: str) -> NormalizationResult:
    original = text or ""
    normalized = original
    replacements: dict[str, int] = {}
    punctuation_notes: list[str] = []

    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    for source, replacement in ABBREVIATION_REPLACEMENTS.items():
        normalized, count = normalized.replace(source, replacement), normalized.count(source)
        if count:
            replacements[source] = count

    normalized, count = re.subn(r"(\d{1,2})-(\d{1,2})", r"\1 to \2", normalized)
    if count:
        replacements["numeric_range_hyphen"] = count

    normalized, count = re.subn(r"\b(\d{4})-(\d{4})\b", r"\1 to \2", normalized)
    if count:
        replacements["year_range_hyphen"] = count

    normalized, count = re.subn(r"(?<!\w)-(\d+)", r"negative \1", normalized)
    if count:
        replacements["negative_number"] = count

    normalized, count = re.subn(r"--+", " - ", normalized)
    if count:
        replacements["double_hyphen_pause"] = count
        punctuation_notes.append("Double hyphen was converted to a spoken pause marker.")

    normalized, count = re.subn(r"[–—]", " - ", normalized)
    if count:
        replacements["dash_pause"] = count
        punctuation_notes.append("En dash and em dash were converted to pause markers.")

    normalized, count = re.subn(r"\.\s*\.\s*\.", "...", normalized)
    if count:
        replacements["ellipsis"] = count
        punctuation_notes.append("Ellipsis was normalized for a quieter pause.")

    normalized = re.sub(r"\s+([,.;:?!])", r"\1", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized).strip()

    return NormalizationResult(
        original_text=original,
        normalized_text=normalized,
        replacements=replacements,
        punctuation_notes=punctuation_notes,
    )


def pronunciation_notes_for_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for term, pronunciation in PRONUNCIATION_NOTES.items():
        count = len(re.findall(re.escape(term), text, re.IGNORECASE))
        rows.append(
            {
                "term": term,
                "recommended_pronunciation": pronunciation,
                "count_in_sample": count,
                "requires_human_review": True,
            }
        )
    return rows


def write_normalization_report(results: list[NormalizationResult], output_path: Path) -> None:
    total_replacements: dict[str, int] = {}
    for result in results:
        for key, value in result.replacements.items():
            total_replacements[key] = total_replacements.get(key, 0) + value

    lines = [
        "# English Text Normalization Report",
        "",
        "Scope: Dracula internal English audiobook model bake-off.",
        "",
        "Status: INTERNAL_REVIEW_ONLY. No audio is published or exposed.",
        "",
        "## Normalization Rules",
        "",
        "- Preserve original text side-by-side with normalized text.",
        "- Expand common Victorian abbreviations for TTS clarity.",
        "- Convert double hyphen, en dash, and em dash into pause markers.",
        "- Preserve dialogue punctuation and diary-date headings.",
        "- Keep pronunciation notes as review metadata, not public claims.",
        "",
        "## Replacement Summary",
        "",
    ]
    if total_replacements:
        for key, value in sorted(total_replacements.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No replacements were needed.")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- No provider API calls were made.",
            "- No audio files were generated.",
            "- No public audiobook URL was created.",
            "- Dracula remains the only live controlled reading title and audio remains disabled.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = normalize_english_text(args.input.read_text(encoding="utf-8"))
    payload = result.as_dict()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

