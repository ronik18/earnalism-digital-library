#!/usr/bin/env python3
"""Generate deterministic dry-run observability and guardrail reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.automation_observability import (  # noqa: E402
    incident_report_csv,
    observability_logs_csv,
    observability_report_json,
    observability_report_markdown,
    run_observability_guardrails,
    structured_logs_json,
)


def sample_payload() -> dict[str, Any]:
    return {
        "dry_run": True,
        "kill_switch_active": False,
        "health": {
            "api": {"status": "OK"},
            "queue": {"status": "OK"},
            "storage": {"status": "OK"},
            "publishing": {"status": "OK"},
        },
    }


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample or path is None:
        return sample_payload()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return payload


def write_reports(report, output_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "observability_guardrails_report.json"
    logs_json_path = output_dir / "structured_logs.json"
    logs_csv_path = output_dir / "structured_logs.csv"
    incidents_csv_path = output_dir / "incident_report.csv"
    markdown_path = output_dir / "observability_guardrails_report.md"
    json_path.write_text(json.dumps(observability_report_json(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logs_json_path.write_text(json.dumps(structured_logs_json(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logs_csv_path.write_text(observability_logs_csv(report), encoding="utf-8")
    incidents_csv_path.write_text(incident_report_csv(report), encoding="utf-8")
    markdown_path.write_text(observability_report_markdown(report), encoding="utf-8")
    return json_path, logs_json_path, logs_csv_path, incidents_csv_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local JSON actions/health payload.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/observability"))
    parser.add_argument("--sample", action="store_true", help="Run deterministic sample guardrails.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write-production", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write_production:
        parser.error("Phase 10 observability guardrails are dry-run only; commit/publish/write-production options are not supported.")

    report = run_observability_guardrails(load_payload(args.input, sample=args.sample))
    json_path, logs_json_path, logs_csv_path, incidents_csv_path, markdown_path = write_reports(report, args.output_dir)
    print(
        "Observability guardrails dry-run complete: "
        f"status={report.status} logs={len(report.logs)} incidents={len(report.incidents)} "
        f"json={json_path} logs_json={logs_json_path} logs={logs_csv_path} "
        f"incidents={incidents_csv_path} markdown={markdown_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
