#!/usr/bin/env python3
"""Run the deterministic daily growth automation loop in dry-run mode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.daily_growth_loop import (  # noqa: E402
    daily_growth_report_csv,
    daily_growth_report_json,
    daily_growth_report_markdown,
    run_daily_growth_loop,
)


def sample_payload() -> dict[str, Any]:
    return {
        "report_date": "2026-06-18",
        "metrics": {
            "paid_readers": 42,
            "reading_starts": 320,
            "reading_completions": 86,
            "preview_listens": 58,
            "referrals": 19,
            "conversion_rate": 0.071,
            "school_institution_leads": 5,
        },
        "budgets": {
            "max_daily_llm_budget": 6,
            "max_daily_audio_budget": 2,
            "max_books_per_day": 3,
            "max_publish_actions_per_day": 0,
        },
        "catalog_truth": {
            "backend_live_approved_count": 1,
            "dracula_only_live_approved": True,
            "unapproved_reader_link_count": 0,
            "unapproved_audio_link_count": 0,
            "unapproved_sitemap_count": 0,
        },
        "books": [
            sample_ready_book("dracula", "Dracula", "gothic-fiction", page_views=1200),
            sample_ready_book("frankenstein", "Frankenstein", "gothic-fiction", page_views=960),
            sample_ready_book("calculus-made-easy", "Calculus Made Easy", "study-material", page_views=720),
        ],
    }


def sample_ready_book(slug: str, title: str, category_slug: str, *, page_views: int) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": title,
        "category_slug": category_slug,
        "language": "en",
        "page_views": page_views,
        "reading_starts": max(1, page_views // 4),
        "reading_completions": max(1, page_views // 14),
        "audiobook_enabled": category_slug != "study-material",
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "publication_region": "global",
        },
        "demand": {"action_status": "READY_FOR_GENERATION"},
        "ingestion_status": "CLEANED",
        "edition_generation_status": "QA_PASSED",
        "visual_status": "QA_PASSED",
        "audio_status": "QA_PASSED" if category_slug != "study-material" else "AUDIO_NOT_REQUIRED",
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 0, "budget": 100},
    }


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample or path is None:
        return sample_payload()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return payload


def write_reports(report, output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "daily_growth_report.json"
    csv_path = output_dir / "daily_growth_report.csv"
    md_path = output_dir / "daily_growth_report.md"
    json_path.write_text(json.dumps(daily_growth_report_json(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path.write_text(daily_growth_report_csv(report), encoding="utf-8")
    md_path.write_text(daily_growth_report_markdown(report), encoding="utf-8")
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local JSON metrics/books payload.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/daily_growth"))
    parser.add_argument("--sample", action="store_true", help="Run deterministic sample metrics.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write:
        parser.error("Phase 9 daily growth automation is dry-run only; commit/publish/write options are not supported.")

    report = run_daily_growth_loop(load_payload(args.input, sample=args.sample))
    json_path, csv_path, md_path = write_reports(report, args.output_dir)
    print(
        "Daily growth dry-run complete: "
        f"tasks={len(report.queued_tasks)} blocked={len(report.blocked_items)} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
