#!/usr/bin/env python3
"""Generate deterministic dry-run publishing workflow reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.publishing_workflow import (  # noqa: E402
    workflow_report_csv,
    workflow_report_json,
    workflow_report_markdown,
)


def sample_book() -> dict[str, Any]:
    return {
        "slug": "alice-in-wonderland",
        "title": "Alice's Adventures in Wonderland",
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "publication_region": "global",
        },
        "demand": {"demand_score": 91.5, "action_status": "READY_FOR_GENERATION"},
        "ingestion_status": "CLEANED",
        "edition_generation_status": "QA_PASSED",
        "visual_status": "QA_PASSED",
        "audio_status": "QA_PASSED",
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 12.5, "budget": 100.0},
        "is_published": False,
    }


def load_book(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample:
        return sample_book()
    if path is None:
        raise ValueError("--input is required unless --sample is used.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return payload


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "publishing_workflow_report.json"
    csv_path = output_dir / "publishing_workflow_report.csv"
    md_path = output_dir / "publishing_workflow_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path.write_text(workflow_report_csv(report), encoding="utf-8")
    md_path.write_text(workflow_report_markdown(report), encoding="utf-8")
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Local JSON book/workflow payload.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/publishing_workflow"))
    parser.add_argument("--sample", action="store_true", help="Run a deterministic local fixture.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write:
        parser.error("Phase 8 publishing workflow is dry-run only; commit/publish/write options are not supported.")

    report = workflow_report_json(load_book(args.input, sample=args.sample))
    json_path, csv_path, md_path = write_reports(report, args.output_dir)
    print(
        "Publishing workflow dry-run complete: "
        f"state={report['state']} readiness={report['publish_readiness']} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
