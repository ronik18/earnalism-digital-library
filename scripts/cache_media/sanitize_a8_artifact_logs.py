#!/usr/bin/env python3
"""Create deterministic, non-mutating sanitized copies of A8 CI diagnostics."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


TEXT_SUFFIXES = {".log", ".txt", ".json", ".jsonl", ".md", ".csv", ".html", ".xml", ".yaml", ".yml"}
PATH_PATTERNS = (
    (re.compile(r"/home/runner/work/[^/]+/[^/]+"), "<REPO_ROOT>"),
    (re.compile(r"/__w/[^/]+/[^/]+"), "<GITHUB_WORKSPACE>"),
    (re.compile(r"/opt/hostedtoolcache"), "<TOOL_CACHE>"),
    (re.compile(r"/home/runner"), "<RUNNER_HOME>"),
    (re.compile(r"/private/(?:tmp|var/folders)(?:/[^\s:'\")]+)*"), "<TEMP_DIR>"),
    (re.compile(r"/tmp(?:/[^\s:'\")]+)*"), "<TEMP_DIR>"),
    (re.compile(r"/Users/[^/\s:'\")]+"), "<USER_HOME>"),
    (re.compile(r"(?i)file:///(?:[A-Z]:/)?[^\s'\")]+"), "<FILE_PATH>"),
    (re.compile(r"(?i)D:\\a\\[^\s:'\")]+"), "<GITHUB_WORKSPACE>"),
    (re.compile(r"(?i)C:\\Users\\[^\\\s:'\")]+"), "<USER_HOME>"),
)


def sanitize_text(value: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for pattern, marker in PATH_PATTERNS:
        value, replaced = pattern.subn(marker, value)
        if replaced:
            counts[marker] = counts.get(marker, 0) + replaced
    return value, counts


def sanitize_json(value):
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        counts = {}
        out = []
        for item in value:
            clean, child = sanitize_json(item); out.append(clean)
            for key, number in child.items(): counts[key] = counts.get(key, 0) + number
        return out, counts
    if isinstance(value, dict):
        counts = {}; out = {}
        for key, item in value.items():
            clean, child = sanitize_json(item); out[key] = clean
            for name, number in child.items(): counts[name] = counts.get(name, 0) + number
        return out, counts
    return value, {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    text = raw.decode("utf-8")
    if args.input.suffix.lower() == ".json":
        cleaned, counts = sanitize_json(json.loads(text)); rendered = json.dumps(cleaned, indent=2, sort_keys=True) + "\n"; mode = "json_recursive"
    else:
        rendered, counts = sanitize_text(text); mode = "text"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    remaining, _ = sanitize_text(rendered)
    report = {"schema_version": "a8-artifact-log-sanitization.v1", "result": "PASS" if remaining == rendered else "FAIL", "input_file_class": args.input.suffix.lower().lstrip(".") or "text", "output_file": args.output.name, "replacement_count": sum(counts.values()), "replacement_counts_by_placeholder": counts, "remaining_private_path_count": 0 if remaining == rendered else 1, "parse_mode": mode, "warnings": []}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["result"] != "PASS": raise SystemExit("sanitization left a private path")


if __name__ == "__main__":
    main()
