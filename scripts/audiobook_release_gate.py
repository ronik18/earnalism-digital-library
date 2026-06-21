#!/usr/bin/env python3
"""Assert audiobook work remains internal and no public audio is exposed."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DRACULA_MANIFEST = ROOT_DIR / "data" / "controlled_publications" / "dracula" / "reader_manifest.json"
OUTPUT_DIR = ROOT_DIR / "output" / "audiobook_bakeoff" / "dracula"
PUBLIC_SOURCE_FILES = [
    ROOT_DIR / "frontend" / "src" / "pages" / "Home.jsx",
    ROOT_DIR / "frontend" / "src" / "pages" / "Library.jsx",
    ROOT_DIR / "frontend" / "src" / "pages" / "BookDetail.jsx",
    ROOT_DIR / "frontend" / "src" / "pages" / "Reader.jsx",
]


def load_reader_manifest() -> dict[str, Any]:
    return json.loads(DRACULA_MANIFEST.read_text(encoding="utf-8"))


def scan_public_audio_claims() -> list[str]:
    issues: list[str] = []
    forbidden_patterns = [
        re.compile(r"\bListen Now\b", re.IGNORECASE),
        re.compile(r"\bFull Audiobook\b", re.IGNORECASE),
        re.compile(r"data-testid=[\"'][^\"']*listen", re.IGNORECASE),
    ]
    for path in PUBLIC_SOURCE_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern.search(text):
                issues.append(f"{path.relative_to(ROOT_DIR)} contains forbidden audio claim: {pattern.pattern}")
    return issues


def scan_bakeoff_public_urls() -> list[str]:
    issues: list[str] = []
    for path in OUTPUT_DIR.glob("**/*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        encoded = json.dumps(payload)
        if re.search(r'"public_audio_url"\s*:\s*"https?://', encoded):
            issues.append(f"{path.relative_to(ROOT_DIR)} exposes public_audio_url")
        if re.search(r'"audio_published"\s*:\s*true', encoded):
            issues.append(f"{path.relative_to(ROOT_DIR)} marks audio_published=true")
    return issues


def run_release_gate() -> dict[str, Any]:
    manifest = load_reader_manifest()
    issues: list[str] = []
    if manifest.get("slug") != "dracula":
        issues.append("Reader manifest is not Dracula.")
    if manifest.get("audio_enabled") is not False:
        issues.append("Dracula reader_manifest audio_enabled must remain false.")
    if manifest.get("audiobook_enabled") is not False:
        issues.append("Dracula reader_manifest audiobook_enabled must remain false.")
    if manifest.get("audio_status") != "NOT_AVAILABLE":
        issues.append("Dracula reader_manifest audio_status must remain NOT_AVAILABLE.")
    if int(manifest.get("chapter_count") or 0) != 27:
        issues.append("Dracula reader_manifest chapter_count must remain 27.")
    issues.extend(scan_public_audio_claims())
    issues.extend(scan_bakeoff_public_urls())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not issues else "FAIL",
        "book_slug": "dracula",
        "dracula_audio_enabled": manifest.get("audio_enabled"),
        "dracula_audiobook_enabled": manifest.get("audiobook_enabled"),
        "chapter_count": manifest.get("chapter_count"),
        "issues": issues,
        "public_audio_exposed": bool(issues),
        "internal_review_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "release_gate.json")
    args = parser.parse_args()
    result = run_release_gate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Audiobook release gate: {result['status']} issues={len(result['issues'])} output={args.output}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

