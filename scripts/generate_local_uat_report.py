#!/usr/bin/env python3
"""Generate the canonical local-UAT report from emitted evidence only."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--evidence-dir", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
evidence = Path(args.evidence_dir).resolve()
required = ["launcher.log", "pinned-browser-inventory.log", "contrast.log", "playwright.log", "report-generation.log"]
missing = [name for name in required if not (evidence / name).is_file()]
if missing:
    raise SystemExit(f"refusing to report incomplete UAT evidence: {', '.join(missing)}")
report = {
    "schema_version": "local-canonical-uat-v1",
    "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "environment": {"base_url": "http://127.0.0.1:3000", "api_base_url": "http://127.0.0.1:8000/api"},
    "evidence_path": str(evidence.relative_to(root)),
    "required_evidence": required,
}
target = root / "uat" / "final-report.json"
target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(target)
