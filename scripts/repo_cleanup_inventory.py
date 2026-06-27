#!/usr/bin/env python3
"""Inventory tracked repo files and flag conservative cleanup candidates.

The script intentionally does not delete or move anything. It produces evidence
for a human-reviewed cleanup pass where launch/payment/audio guardrails matter.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_REFERENCE_PREFIXES = (
    ".git/",
    "node_modules/",
    "frontend/node_modules/",
    ".venv/",
    "frontend/build/",
    "build/",
)
TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".txt",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".xml",
}
DUPLICATE_NAME_RE = re.compile(r"^(?P<base>.+) (?P<num>[23])(?P<suffix>\.[^./]+)$")


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def tracked_files() -> list[str]:
    return [line for line in run_git(["ls-files"]).splitlines() if line]


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    guessed, _encoding = mimetypes.guess_type(str(path))
    return bool(guessed and guessed.startswith("text/"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative_path: str) -> str:
    path = Path(relative_path)
    suffix = path.suffix.lower()
    parts = path.parts
    name = path.name
    if relative_path.startswith(".github/") or name in {"package.json", "package-lock.json", "pytest.ini", "playwright.config.js"}:
        return "script/tooling"
    if relative_path.startswith("frontend/src/"):
        return "frontend source"
    if relative_path.startswith("frontend/public/"):
        return "public asset" if suffix not in {".html", ".xml", ".txt", ".json"} else "SEO/static output"
    if relative_path.startswith("frontend/scripts/"):
        return "script/tooling"
    if relative_path.startswith("backend/tests/") or relative_path.startswith("regression/") or relative_path.startswith("tests/"):
        return "test/regression"
    if relative_path.startswith("backend/"):
        return "backend source"
    if relative_path.startswith("scripts/"):
        return "script/tooling"
    if relative_path.startswith("internal/"):
        return "internal evidence"
    if relative_path.startswith("output/"):
        return "generated artifact"
    if relative_path.startswith("onboarding/") or relative_path.startswith("book_import_manifests/"):
        return "onboarding artifact"
    if relative_path.startswith("audio_manifests/") or relative_path.startswith("audiobook/"):
        return "internal evidence"
    if suffix in {".md", ".csv"}:
        return "report/documentation"
    if suffix in {".json", ".yaml", ".yml"}:
        return "generated artifact" if "report" in name.lower() else "script/tooling"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return "public asset"
    return "unknown"


def counterpart_for_duplicate(relative_path: str, all_files: set[str]) -> str:
    path = Path(relative_path)
    match = DUPLICATE_NAME_RE.match(path.name)
    if not match:
        return ""
    counterpart = str(path.with_name(f"{match.group('base')}{match.group('suffix')}"))
    return counterpart if counterpart in all_files else ""


def load_text_corpus(files: list[str]) -> dict[str, str]:
    corpus: dict[str, str] = {}
    for relative in files:
        if relative.startswith(EXCLUDED_REFERENCE_PREFIXES):
            continue
        path = ROOT / relative
        if not path.is_file() or not is_text_file(path):
            continue
        try:
            corpus[relative] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return corpus


def reference_count(target: str, corpus: dict[str, str]) -> int:
    path = Path(target)
    tokens = {target, path.name}
    if target.startswith("frontend/public/"):
        tokens.add("/" + target.removeprefix("frontend/public/"))
    count = 0
    for source, text in corpus.items():
        if source == target:
            continue
        for token in tokens:
            if token and token in text:
                count += 1
                break
    return count


def package_script_references(target: str, package_text: str) -> bool:
    path = Path(target)
    tokens = {target, path.name}
    return any(token and token in package_text for token in tokens)


def policy_for_file(row: dict) -> str:
    path = row["path"]
    category = row["category"]
    if category in {"internal evidence", "report/documentation", "onboarding artifact"}:
        return "KEEP_EVIDENCE_OR_HISTORY"
    if category in {"SEO/static output", "generated artifact"}:
        return "KEEP_GENERATED_BUT_DOCUMENT"
    if row["duplicate_counterpart"] and row["reference_count"] == 0 and not row["package_script_reference"]:
        return "SAFE_TO_QUARANTINE_HIGH_CONFIDENCE"
    if category == "unknown" and row["reference_count"] == 0 and not row["package_script_reference"]:
        return "REVIEW_REQUIRED"
    if "audio" in path.lower() or "payment" in path.lower() or "launch" in path.lower() or "seo" in path.lower():
        return "KEEP_EVIDENCE_OR_HISTORY"
    return "REVIEW_REQUIRED" if row["reference_count"] == 0 and not row["package_script_reference"] else "KEEP_REFERENCED"


def main() -> int:
    files = tracked_files()
    file_set = set(files)
    corpus = load_text_corpus(files)
    package_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("package.json", "frontend/package.json")
        if (ROOT / path).exists()
    )
    rows = []
    for relative in files:
        path = ROOT / relative
        counterpart = counterpart_for_duplicate(relative, file_set)
        row = {
            "path": relative,
            "category": classify(relative),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256(path) if path.exists() and path.is_file() else "",
            "reference_count": reference_count(relative, corpus),
            "package_script_reference": package_script_references(relative, package_text),
            "duplicate_counterpart": counterpart,
        }
        row["policy"] = policy_for_file(row)
        rows.append(row)

    counts = Counter(row["category"] for row in rows)
    policies = Counter(row["policy"] for row in rows)
    output = {
        "generated_by": "scripts/repo_cleanup_inventory.py",
        "tracked_file_count": len(files),
        "text_file_count_indexed_for_references": len(corpus),
        "classification_counts": dict(sorted(counts.items())),
        "policy_counts": dict(sorted(policies.items())),
        "files": rows,
    }
    (ROOT / "REPO_CLEANUP_USAGE_INVENTORY.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
