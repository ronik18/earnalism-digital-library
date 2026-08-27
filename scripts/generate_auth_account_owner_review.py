#!/usr/bin/env python3
"""Create a sanitized, downloadable owner-review package for auth/account UI."""

from __future__ import annotations

import json
import shutil
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


STATES = (
    "login-desktop", "login-mobile", "signup-desktop", "signup-mobile",
    "account-desktop", "account-mobile",
)


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def copy(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    shutil.copy2(source, destination)


def review_html(records: list[dict]) -> str:
    sections = "".join(
        f'''<section id="{item["state"]}"><h2>{item["state"].replace("-", " ").title()}</h2>
<p><strong>RESPONSIVE DESIGN-SYSTEM EXTENSION.</strong> Account uses a deterministic, sanitized fixture; no credentials, account identity, production balance, or transaction data appears in this package.</p>
<div class="comparison"><figure><img src="{item["before"]}" alt="Base screenshot"><figcaption>Base branch</figcaption></figure><figure><img src="{item["after"]}" alt="PR screenshot"><figcaption>PR #338</figcaption></figure></div>
<pre>{json.dumps(item["result"], indent=2)}</pre></section>'''
        for item in records
    )
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Earnalism auth and account owner review</title><style>
body{{margin:0;background:#f6f1e8;color:#1a211c;font:16px system-ui,sans-serif}}header{{padding:22px;background:#0b1512;color:#fff8ea}}main{{max-width:1480px;margin:auto;padding:28px}}section{{margin:0 0 44px;padding:20px;background:#fffdf8;border:1px solid #d5c59f;border-radius:14px}}h1,h2{{font-family:Georgia,serif}}.comparison{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}figure{{margin:0;border:1px solid #dfd2b4;padding:8px;background:white}}img{{width:100%;display:block}}figcaption{{margin-top:8px;font-size:13px}}pre{{overflow:auto;background:#0b1512;color:#fff8ea;padding:14px;font-size:12px}}@media(max-width:720px){{.comparison{{grid-template-columns:1fr}}}}</style></head><body><header><h1>Auth and Account visual owner review</h1><p>PR #338 · deterministic local fixtures · animation disabled · UTC / en-US</p></header><main><section><h2>Validation summary</h2><p>All captures must have status 200, required components present, zero console/page errors, and zero horizontal overflow. The product contract remains: <strong>Read the first 3 pages free. Listening requires an active Reading Pass.</strong></p></section>{sections}</main></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default="uat/evidence/auth-account-owner-review/before")
    parser.add_argument("--after", default="uat/evidence/auth-account-owner-review/after")
    parser.add_argument("--output", default="uat/evidence/auth-account-owner-review/final")
    args = parser.parse_args()
    root = Path(".").resolve()
    before_dir = (root / args.before).resolve()
    after_dir = (root / args.after).resolve()
    output = (root / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    before_results = {row["id"]: row for row in load(before_dir / "capture.json")}
    after_results = {row["id"]: row for row in load(after_dir / "capture.json")}
    records = []
    pages = []
    for state in STATES:
        before_name = f"{state}-before.png"
        after_name = f"{state}-after.png"
        copy(before_dir / f"{state}.png", output / before_name)
        copy(after_dir / f"{state}.png", output / after_name)
        result = after_results[state]
        records.append({"state": state, "before": before_name, "after": after_name, "result": result})
        page = Image.new("RGB", (1600, 1060), "#f6f1e8")
        draw = ImageDraw.Draw(page)
        font = ImageFont.load_default()
        draw.text((40, 28), f"{state} — base / PR #338", fill="#1a211c", font=font)
        for index, source in enumerate((before_dir / f"{state}.png", after_dir / f"{state}.png")):
            image = Image.open(source).convert("RGB")
            image.thumbnail((730, 940))
            page.paste(image, (40 + index * 790, 80))
        pages.append(page)
    summary = {
        "schema_version": "earnalism-auth-account-owner-review-v1",
        "status": "OWNER_AUTH_ACCOUNT_APPROVAL_REQUIRED",
        "sanitized_deterministic_fixture": True,
        "accessibility_and_overflow": {
            "status_200": all(record["result"]["status"] == 200 for record in records),
            "required_components": all(all(record["result"]["required"]) for record in records),
            "horizontal_overflow": [record["state"] for record in records if record["result"]["scrollWidth"] != record["result"]["clientWidth"]],
            "console_or_page_errors": [record["state"] for record in records if record["result"]["errors"]],
            "failed_requests": [record["state"] for record in records if record["result"]["failedRequests"]],
            "keyboard_focus_missing": [record["state"] for record in records if not record["result"]["keyboard_focus_target"]],
        },
        "records": records,
    }
    (output / "owner-review.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "owner-review.html").write_text(review_html(records))
    pages[0].save(output / "owner-review.pdf", save_all=True, append_images=pages[1:])
    (output / "accessibility-overflow-results.json").write_text(json.dumps(summary["accessibility_and_overflow"], indent=2) + "\n")
    print(json.dumps({"states": len(records), "output": str(output), "status": summary["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
