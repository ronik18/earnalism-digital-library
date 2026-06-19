#!/usr/bin/env python3
"""Deterministic line-by-line launch-hardening audit.

The audit is intentionally conservative: it scans tracked text source/config/doc
files, skips build artifacts and binary/media files, and writes review reports.
It does not publish, deploy, call providers, or mutate production data.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

SKIP_DIR_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".venv-audio",
    ".venv-edge",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "output",
    "test-results",
    "tmp",
}

BINARY_EXTENSIONS = {
    ".aac",
    ".avif",
    ".bin",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mp3",
    ".mp4",
    ".ogg",
    ".onnx",
    ".pdf",
    ".png",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

SOURCE_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}

GENERATED_REPORT_NAMES = {
    "DEAD_CODE_AND_DANGEROUS_SCRIPT_REPORT.md",
    "DUPLICATE_OR_STALE_DOCS_REPORT.md",
    "LINE_BY_LINE_AUDIT_REPORT.md",
    "LINE_BY_LINE_RISK_REGISTER.csv",
    "PHASE14_VALIDATION_REPORT.md",
}

HIDDEN_UNICODE = {
    "\u202a": "U+202A",
    "\u202b": "U+202B",
    "\u202c": "U+202C",
    "\u202d": "U+202D",
    "\u202e": "U+202E",
    "\u2066": "U+2066",
    "\u2067": "U+2067",
    "\u2068": "U+2068",
    "\u2069": "U+2069",
    "\u200b": "U+200B",
    "\u200c": "U+200C",
    "\u200d": "U+200D",
    "\ufeff": "U+FEFF",
}


@dataclass
class Finding:
    severity: str
    category: str
    path: str
    line: int
    finding: str
    recommendation: str


def run_git_ls_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_scan(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    parts = set(relative.parts)
    if parts.intersection(SKIP_DIR_PARTS):
        return False
    if path.name in GENERATED_REPORT_NAMES:
        return False
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    if path.suffix.lower() not in SOURCE_EXTENSIONS and path.name not in {"Dockerfile", "Procfile"}:
        return False
    if not path.exists() or not path.is_file():
        return False
    if path.stat().st_size > 2_000_000:
        return False
    return True


def add(finding_list: list[Finding], severity: str, category: str, path: str, line: int, finding: str, recommendation: str) -> None:
    finding_list.append(Finding(severity, category, path, line, finding, recommendation))


def scan_file(relative_path: str) -> tuple[list[Finding], int]:
    path = ROOT / relative_path
    findings: list[Finding] = []
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return findings, 0

    if b"\r" in data and b"\n" not in data:
        add(findings, "HIGH", "line_endings", relative_path, 1, "CR-only line endings detected.", "Normalize to LF before merge.")

    lines = text.splitlines()
    if "#!" in text and not text.startswith("#!"):
        add(findings, "HIGH", "invalid_shebang", relative_path, 1, "Shebang appears after line 1.", "Move shebang to the first physical line.")
    if len(lines) <= 2 and len(text) > 1000 and path.suffix.lower() in {".py", ".js", ".mjs", ".jsx"}:
        add(findings, "HIGH", "minified_source", relative_path, 1, "Source file appears compressed or minified.", "Reformat with normal line breaks.")

    file_lower = text.lower()
    if "cloudinary" in file_lower or "azure" in file_lower or "edge-tts" in file_lower or "openai" in file_lower:
        audio_like = "audio" in relative_path.lower() or "tts" in relative_path.lower() or "audiobook" in relative_path.lower()
        guarded = all(
            token in text
            for token in [
                "EARNALISM_ALLOW_AUDIO_UPLOAD",
                "EARNALISM_ALLOW_PROVIDER_CALLS",
                "EARNALISM_CONFIRM_PRODUCTION_AUDIO",
            ]
        )
        if audio_like and not guarded:
            add(
                findings,
                "HIGH",
                "provider_guard",
                relative_path,
                1,
                "Audio/provider script references remote providers without all production audio guard flags.",
                "Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO.",
            )

    for index, line in enumerate(lines, start=1):
        lowered = line.lower()
        for char, codepoint in HIDDEN_UNICODE.items():
            if char in line:
                add(findings, "HIGH", "hidden_unicode", relative_path, index, f"Hidden Unicode control {codepoint} detected.", "Remove hidden Unicode.")
        if re.search(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}", line):
            if "process.env" not in line and "secrets." not in lowered and "placeholder" not in lowered:
                add(findings, "HIGH", "secret_like_string", relative_path, index, "Secret-like literal detected.", "Move secrets to environment variables or confirm this is a documented placeholder.")
        if re.search(r"(?i)\b(go_for_controlled_publication|approved_to_publish\.md|10/10|production-ready|ready for publication)\b", line):
            add(findings, "MEDIUM", "unsafe_or_stale_launch_language", relative_path, index, "Launch/GO language requires review.", "Keep launch status HOLD unless evidence satisfies the publication precheck.")
        if "dangerouslysetinnerhtml" in lowered or ".innerhtml" in lowered:
            add(findings, "HIGH", "raw_html_injection", relative_path, index, "Raw HTML rendering detected.", "Verify sanitizer and trusted source boundaries.")
        if "/shop" in line and "/library" in line and ("redirect" in lowered or "navigate" in lowered or "destination" in lowered):
            add(findings, "HIGH", "unsafe_redirect", relative_path, index, "Potential legacy /shop to /library redirect.", "Removed demo routes must go to removed-content, not the SPA shell or library.")
        if re.search(r"\b(railway\s+up|vercel\s+deploy|vercel.+--prod|npm\s+publish)\b", line):
            add(findings, "MEDIUM", "deployment_script", relative_path, index, "Deployment command detected.", "Ensure it is documented, main-branch gated, and not part of tests.")
        if re.search(r"\b(requests\.post|fetch\(|axios\.post|userApi\.post|api\.post)\b", line) and any(term in lowered for term in ["payment", "webhook", "send", "social", "email"]):
            add(findings, "LOW", "external_or_mutating_call_site", relative_path, index, "Potential mutating call site.", "Verify tests use mocks/dry-run paths only.")
    return findings, len(lines)


def markdown_table(headers: list[str], rows: Iterable[list[object]]) -> str:
    rendered = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        rendered.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(rendered)


def write_reports(scanned: list[tuple[str, int]], findings: list[Finding]) -> None:
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings = sorted(findings, key=lambda item: (severity_order.get(item.severity, 9), item.path, item.line, item.category))

    with (ROOT / "LINE_BY_LINE_RISK_REGISTER.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["severity", "category", "path", "line", "finding", "recommendation"],
            lineterminator="\n",
        )
        writer.writeheader()
        for item in findings:
            writer.writerow(item.__dict__)

    category_counts: dict[str, int] = {}
    for item in findings:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1

    top_findings = findings[:60]
    (ROOT / "LINE_BY_LINE_AUDIT_REPORT.md").write_text(
        "\n".join(
            [
                "# Line-By-Line Audit Report",
                "",
                f"Generated: `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`",
                "",
                "This deterministic audit scanned tracked text source/config/doc files and skipped build artifacts, generated output, virtual environments, and binary/media assets. It does not publish, deploy, call providers, or mutate production data.",
                "",
                markdown_table(
                    ["Metric", "Value"],
                    [
                        ["Tracked text files scanned", len(scanned)],
                        ["Source/config/doc lines scanned", sum(count for _, count in scanned)],
                        ["Findings", len(findings)],
                    ],
                ),
                "",
                "## Category Counts",
                "",
                markdown_table(["Category", "Count"], sorted(category_counts.items())),
                "",
                "## Highest Priority Findings",
                "",
                markdown_table(
                    ["Severity", "Category", "File", "Line", "Finding", "Recommendation"],
                    [[item.severity, item.category, item.path, item.line, item.finding, item.recommendation] for item in top_findings],
                ),
                "",
                "Full CSV: `LINE_BY_LINE_RISK_REGISTER.csv`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    dead_code = [
        item
        for item in findings
        if item.category in {"deployment_script", "provider_guard", "unsafe_redirect", "minified_source"}
        or " 2." in item.path
        or re.search(r"(^|/)generate_audio [23]\.py$", item.path)
    ]
    (ROOT / "DEAD_CODE_AND_DANGEROUS_SCRIPT_REPORT.md").write_text(
        "\n".join(
            [
                "# Dead Code And Dangerous Script Report",
                "",
                "This report lists duplicate/stale-looking files and scripts that need operator review before controlled publication.",
                "",
                markdown_table(
                    ["Severity", "Category", "File", "Line", "Finding", "Recommendation"],
                    [[item.severity, item.category, item.path, item.line, item.finding, item.recommendation] for item in dead_code[:100]],
                )
                if dead_code
                else "No dangerous-script findings were detected by the deterministic scan.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stale_docs = [
        item
        for item in findings
        if item.category == "unsafe_or_stale_launch_language"
        or item.path.endswith("_REPORT.md")
        or "PHASE" in item.path
        or " 2." in item.path
    ]
    (ROOT / "DUPLICATE_OR_STALE_DOCS_REPORT.md").write_text(
        "\n".join(
            [
                "# Duplicate Or Stale Docs Report",
                "",
                "Phase and launch reports are evidence snapshots, not publication approval. Any stale GO language must stay subordinate to `FINAL_GO_NO_GO_DECISION.md` and `controlled-publication:precheck`.",
                "",
                markdown_table(
                    ["Severity", "Category", "File", "Line", "Finding", "Recommendation"],
                    [[item.severity, item.category, item.path, item.line, item.finding, item.recommendation] for item in stale_docs[:120]],
                )
                if stale_docs
                else "No stale documentation findings were detected by the deterministic scan.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    scanned: list[tuple[str, int]] = []
    findings: list[Finding] = []
    for relative_path in run_git_ls_files():
        path = ROOT / relative_path
        if not should_scan(path):
            continue
        file_findings, line_count = scan_file(relative_path)
        scanned.append((relative_path, line_count))
        findings.extend(file_findings)
    write_reports(scanned, findings)
    print(f"Line audit complete: files={len(scanned)} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
