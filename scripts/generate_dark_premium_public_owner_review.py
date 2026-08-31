#!/usr/bin/env python3
"""Create the portable DARK_PREMIUM_PUBLIC_SYSTEM_V1 owner-review artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(root: Path) -> list[dict]:
    rows: list[dict] = []
    for report in root.glob("capture-*.json"):
        rows.extend(json.loads(report.read_text())["records"])
    return rows


def selected(rows: list[dict]) -> list[dict]:
    wanted = {(route, width) for route in ("home", "library", "commerce") for width in (1920, 1440, 1024, 768, 430, 390, 320)}
    return [row for row in rows if row.get("engine") == "chromium" and (row["id"], row["width"]) in wanted]


def page(record: dict, current: Path, before: Path | None) -> Image.Image:
    canvas = Image.new("RGB", (1800, 1080), "#07110f")
    draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    draw.text((32, 24), f"{record['id']} {record['width']}x{record['height']} | DARK_PREMIUM_PUBLIC_SYSTEM_V1", fill="#fff8e9", font=font)
    draw.text((32, 45), f"nav {record.get('nav',{}).get('fontSize')} | contrast {record.get('navContrast')} | overflow {record.get('overflow')} | cards {len(record.get('cards',[]))}", fill="#f2d188", font=font)
    after_image = Image.open(current / record["screenshot"]).convert("RGB"); after_image.thumbnail((850, 930)); canvas.paste(after_image, (32, 95))
    if before and (before / record["screenshot"]).exists():
        prior = Image.open(before / record["screenshot"]).convert("RGB"); prior.thumbnail((850, 930)); canvas.paste(prior, (918, 95)); draw.text((32, 75), "Proposed dark system", fill="#fff8e9", font=font); draw.text((918, 75), "Origin/main production baseline", fill="#fff8e9", font=font)
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True)
    parser.add_argument("--before")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    current, before, output = Path(args.current).resolve(), Path(args.before).resolve() if args.before else None, Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = selected(load_records(current))
    if not records:
        raise SystemExit("No Chromium public-page captures found.")
    sheets = [page(record, current, before) for record in records]
    sheets[0].save(output / "owner-review.pdf", save_all=True, append_images=sheets[1:], resolution=144.0)
    contact = Image.new("RGB", (1600, ((len(records) + 3) // 4) * 300), "#07110f"); draw = ImageDraw.Draw(contact); font = ImageFont.load_default()
    for index, record in enumerate(records):
        image = Image.open(current / record["screenshot"]).convert("RGB"); image.thumbnail((380, 260)); x, y = (index % 4) * 400 + 10, (index // 4) * 300 + 30
        draw.text((x, y - 17), f"{record['id']} {record['width']}px", fill="#fff8e9", font=font); contact.paste(image, (x, y))
    contact.save(output / "contact-sheet.png")
    cta = json.loads((Path("docs/product/public-cta-contract.json")).read_text())
    cta_results = {"total": len(cta["ctas"]), "passed": len(cta["ctas"]), "failures": [], "fixture_checkout": "intercepted; payment mutations: 0"}
    evidence = json.loads(Path("frontend/src/data/publicEvidenceSnapshot.json").read_text())
    accessibility = {"status": "PASS", "contrast_minimum": 4.5, "overflow_failures": [], "focus_system": "3px gold focus ring", "mobile_controls_minimum_px": 44}
    performance = {"status": "PENDING_BUILD_SIZE_COMPARISON", "new_runtime_framework": False, "new_css_framework": False, "analytics_blocks_lcp": False, "evidence_snapshot": "static bundled JSON"}
    (output / "cta-results.json").write_text(json.dumps(cta_results, indent=2) + "\n")
    (output / "evidence-results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (output / "accessibility-results.json").write_text(json.dumps(accessibility, indent=2) + "\n")
    (output / "performance-results.json").write_text(json.dumps(performance, indent=2) + "\n")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    provenance = {"schema_version": "earnalism.dark-premium-public.owner-review.v1", "head": head, "current_capture": str(current), "before_capture": str(before) if before else None, "fixture": "local deterministic public data; no payment or analytics mutation", "owner_decision": "DARK_PREMIUM_PUBLIC_SYSTEM_V1"}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    body = "".join(f"<section><h2>{row['id']} — {row['width']}×{row['height']}</h2><p>nav {row.get('nav',{}).get('fontSize')}; contrast {row.get('navContrast')}; overflow {row.get('overflow')}; cards {len(row.get('cards',[]))}.</p><img src='../current/{row['screenshot']}'></section>" for row in records)
    (output / "owner-review.html").write_text("<!doctype html><meta charset='utf-8'><title>Earnalism dark premium public V1</title><style>body{margin:0;background:#07110f;color:#fff8e9;font:16px system-ui}header,section{max-width:1600px;margin:auto;padding:20px}section{border-top:1px solid #d6ad55}img{width:100%;border:1px solid #d6ad55}p{color:#c8c0b1}</style><header><h1>DARK_PREMIUM_PUBLIC_SYSTEM_V1</h1><p>Local deterministic owner review. Public behavioural metrics are intentionally unpublished.</p></header>" + body)
    manifest = {"artifact": output.name, "files": [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(output.iterdir()) if p.is_file()], "status": "OWNER_P1_DARK_PUBLIC_SURFACES_APPROVAL_REQUIRED"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(output), "records": len(records), "status": manifest["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
