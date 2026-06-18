#!/usr/bin/env python3
"""Generate the first 10-product Earnalism dry-run batch reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.first_batch_dry_run import (  # noqa: E402
    first_batch_report_csv,
    first_batch_report_json,
    first_batch_report_markdown,
    run_first_batch_dry_run,
)


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample or path is None:
        return {"dry_run": True}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return payload


def write_reports(report, output_dir: Path) -> tuple[Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "first_batch_dry_run_report.json"
    csv_path = output_dir / "first_batch_dry_run_report.csv"
    markdown_path = output_dir / "first_batch_dry_run_report.md"
    root_markdown_path = ROOT_DIR / "FIRST_BATCH_DRY_RUN_REPORT.md"
    json_path.write_text(json.dumps(first_batch_report_json(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path.write_text(first_batch_report_csv(report), encoding="utf-8")
    markdown = first_batch_report_markdown(report)
    markdown_path.write_text(markdown, encoding="utf-8")
    root_markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, csv_path, markdown_path, root_markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local JSON batch payload.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/first_batch"))
    parser.add_argument("--sample", action="store_true", help="Use the built-in 10-product batch.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write-production", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write_production:
        parser.error("Phase 11 first batch is dry-run only; commit/publish/write-production options are not supported.")

    report = run_first_batch_dry_run(load_payload(args.input, sample=args.sample))
    json_path, csv_path, markdown_path, root_markdown_path = write_reports(report, args.output_dir)
    print(
        "First batch dry-run complete: "
        f"status={report.status} products={len(report.products)} "
        f"json={json_path} csv={csv_path} markdown={markdown_path} root_report={root_markdown_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
