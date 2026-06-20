#!/usr/bin/env python3
"""Generate the Dracula-only backend catalog truth audit in dry-run mode."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import (  # noqa: E402
    LIVE_APPROVED_SLUG,
    catalog_truth_row,
    catalog_truth_summary,
    dracula_approval_evidence,
)


REPORT_FIELDS = [
    "slug",
    "title",
    "author",
    "classification",
    "is_published",
    "publication_status",
    "rights_tier",
    "verification_status",
    "qa_status",
    "approved_to_publish",
    "reader_enabled",
    "preview_enabled",
    "audio_enabled",
    "audiobook_enabled",
    "source_url_present",
    "source_hash_present",
    "content_hash_present",
    "provenance_hash_present",
    "public_route",
    "reader_route",
    "sitemap_inclusion",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def sitemap_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return set()
    urls: set[str] = set()
    for node in root.iter():
        if node.tag.endswith("loc") and node.text:
            urls.add(node.text.strip())
            parsed_path = "/" + node.text.split("theearnalism.com/", 1)[-1].strip("/")
            urls.add(parsed_path.rstrip("/") if parsed_path != "/" else "/")
    return urls


def dracula_record() -> dict[str, Any]:
    evidence = dracula_approval_evidence()
    rights_decision = evidence.get("rights_decision") if isinstance(evidence.get("rights_decision"), dict) else {}
    metadata = rights_decision.get("metadata") if isinstance(rights_decision.get("metadata"), dict) else {}
    ingestion = evidence.get("ingestion") if isinstance(evidence.get("ingestion"), dict) else {}
    return {
        "id": "dracula-controlled-launch",
        "slug": LIVE_APPROVED_SLUG,
        "title": "Dracula",
        "author": "Bram Stoker",
        "category_slug": "gothic-fiction",
        "short_description": "The only controlled live core reading release.",
        "is_published": True,
        "rights_metadata": {
            "rights_tier": metadata.get("rights_tier") or "A",
            "verification_status": metadata.get("verification_status") or "approved",
            "blocked_reason": metadata.get("blocked_reason") or "",
            "source_url": metadata.get("source_url") or evidence.get("source_url"),
            "source_name": metadata.get("source_name") or evidence.get("source_name"),
            "source_license": metadata.get("source_license") or evidence.get("source_license"),
        },
        "source_hash": evidence.get("source_hash") or ingestion.get("source_hash"),
        "content_hash": evidence.get("content_hash") or ingestion.get("content_hash"),
        "provenance_hash": evidence.get("provenance_hash") or ingestion.get("provenance_hash"),
        "qa_status": evidence.get("qa_status") or "QA_PASSED",
        "approved_to_publish": bool(evidence.get("approved_to_publish_artifact")),
        "publication_status": "LIVE_APPROVED",
    }


def pipeline_candidate_records() -> list[dict[str, Any]]:
    source_path = ROOT / "data" / "publication_candidates" / "kshudhita-pashan.source.json"
    candidate = load_json(source_path)
    title = candidate.get("title") or "Kshudhita Pashan"
    author = candidate.get("author") or "Rabindranath Tagore"
    return [
        {
            "id": "kshudhita-pashan-pipeline",
            "slug": "kshudhita-pashan",
            "title": title,
            "author": author,
            "category_slug": "gothic-fiction",
            "short_description": "Bengali gothic candidate held in the rights-safe pipeline.",
            "is_published": False,
            "pipeline_stage": "PIPELINE_ONLY",
            "rights_metadata": {
                "rights_tier": candidate.get("rights_tier") or "UNKNOWN",
                "verification_status": candidate.get("verification_status") or "pending",
                "blocked_reason": candidate.get("blocked_reason") or "",
            },
            "publication_status": "PIPELINE_CANDIDATE",
        }
    ]


def audit_records() -> list[dict[str, Any]]:
    return [dracula_record(), *pipeline_candidate_records()]


def csv_text(rows: list[dict[str, Any]]) -> str:
    output = []
    writer_buffer = CsvBuffer(output)
    writer = csv.DictWriter(writer_buffer, fieldnames=REPORT_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in REPORT_FIELDS})
    return "".join(output)


class CsvBuffer:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks

    def write(self, value: str) -> int:
        self.chunks.append(value)
        return len(value)


def markdown_report(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    blockers = summary.get("launch_blockers") or []
    lines = [
        "# Backend Catalog Truth Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "Mode: dry-run, local report only",
        "",
        "## Launch Truth",
        "",
        "- Dracula is the only live approved core reading candidate.",
        "- Dracula audio is disabled.",
        "- Kshudhita Pashan remains pipeline-only.",
        "- No Tier B, Tier C, or unapproved title may expose reader/audio CTAs.",
        "",
        "## Summary",
        "",
        f"- Live approved count: {summary['live_approved_count']}",
        f"- Dracula-only live approved: {summary['dracula_only_live_approved']}",
        f"- Pipeline candidate count: {summary['pipeline_candidate_count']}",
        f"- Unapproved reader link count: {summary['unapproved_reader_link_count']}",
        f"- Unapproved audio link count: {summary['unapproved_audio_link_count']}",
        f"- Unapproved sitemap count: {summary['unapproved_sitemap_count']}",
        "",
        "## Matrix",
        "",
        "| Slug | Classification | Reader | Preview | Audio | Sitemap |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {slug} | {classification} | {reader_enabled} | {preview_enabled} | "
            "{audio_enabled} | {sitemap_inclusion} |".format(**row)
        )
    lines.extend(["", "## Blockers", ""])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Owner Decision",
            "",
            "GO for Dracula-only backend catalog truth if validation remains green.",
            "HOLD for any unapproved reader link, audio link, or sitemap inclusion.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(output_dir: Path) -> tuple[Path, Path, Path]:
    urls = sitemap_urls(ROOT / "frontend" / "public" / "sitemap.xml")
    rows = [catalog_truth_row(record, sitemap_urls=urls) for record in audit_records()]
    summary = catalog_truth_summary(rows, sitemap_urls=urls)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "catalog_truth_report.json"
    md_path = output_dir / "catalog_truth_report.md"
    csv_path = output_dir / "catalog_truth_matrix.csv"
    json_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(markdown_report(rows, summary), encoding="utf-8")
    csv_path.write_text(csv_text(rows), encoding="utf-8")
    return json_path, md_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "daily" / date.today().isoformat(),
        help="Local output directory for dry-run reports.",
    )
    args = parser.parse_args()
    json_path, md_path, csv_path = write_reports(args.output_dir)
    print(f"Catalog truth audit complete: json={json_path} markdown={md_path} csv={csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
