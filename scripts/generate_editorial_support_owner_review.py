#!/usr/bin/env python3
"""Build a sanitized visual owner-review package for Editorial/Support routes."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load(path):
    return {row["id"]: row for row in json.loads(path.read_text())}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default="uat/evidence/editorial-support-owner-review/before")
    parser.add_argument("--after", default="uat/evidence/editorial-support-owner-review/after")
    parser.add_argument("--output", default="uat/evidence/editorial-support-owner-review/final")
    args = parser.parse_args()
    root = Path.cwd()
    before, after, output = [root / value for value in (args.before, args.after, args.output)]
    output.mkdir(parents=True, exist_ok=True)
    before_data, after_data = load(before / "capture.json"), load(after / "capture.json")
    records, pages = [], []
    for state, after_result in after_data.items():
        if state not in before_data:
            raise RuntimeError("missing base capture: " + state)
        before_name, after_name = state + "-before.png", state + "-after.png"
        shutil.copy2(before / (state + ".png"), output / before_name)
        shutil.copy2(after / (state + ".png"), output / after_name)
        record = {"state": state, "before": before_name, "after": after_name, "before_sha256": digest(output / before_name), "after_sha256": digest(output / after_name), "result": after_result}
        records.append(record)
        board = Image.new("RGB", (1600, 1060), "#f8f4eb")
        draw = ImageDraw.Draw(board)
        draw.text((40, 28), state + " — base / proposed", fill="#231f1b", font=ImageFont.load_default())
        for index, image_path in enumerate((before / (state + ".png"), after / (state + ".png"))):
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((730, 940))
            board.paste(image, (40 + index * 790, 80))
        pages.append(board)
    summary = {
        "schema_version": "earnalism-editorial-support-owner-review-v1",
        "status": "OWNER_EDITORIAL_SUPPORT_APPROVAL_REQUIRED",
        "fixture_only": True,
        "product_truth": "Read the first 3 pages free. Listening requires an active Reading Pass.",
        "records": records,
        "responsive": {"overflow": [record["state"] for record in records if record["result"].get("overflow")], "errors": [record["state"] for record in records if record["result"].get("errors")]},
    }
    sections = "".join("<section><h2>" + row["state"] + "</h2><div><figure><img src='" + row["before"] + "'><figcaption>base</figcaption></figure><figure><img src='" + row["after"] + "'><figcaption>proposed</figcaption></figure></div><pre>" + json.dumps(row["result"], indent=2) + "</pre></section>" for row in records)
    html = "<!doctype html><meta charset='utf-8'><title>Earnalism editorial and support owner review</title><style>body{margin:0;background:#f8f4eb;color:#231f1b;font:16px system-ui}header{padding:28px;background:#0d1814;color:#fff8e8}main{max-width:1500px;margin:auto;padding:28px}section{margin:0 0 36px;padding:20px;background:#fffdf8;border:1px solid #d8c8aa;border-radius:16px}h1,h2{font-family:Georgia,serif}section>div{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0}img{width:100%;border:1px solid #d8c8aa}pre{overflow:auto;background:#0d1814;color:#fff8e8;padding:14px}@media(max-width:720px){section>div{grid-template-columns:1fr}}</style><header><h1>Editorial, support, and error-route owner review</h1><p>Deterministic local fixtures. Product truth is preserved.</p></header><main><p>Every capture requires a visible logo, no overflow, focusable controls, and zero page/console errors.</p>" + sections + "</main>"
    (output / "owner-review.html").write_text(html)
    (output / "owner-review.json").write_text(json.dumps(summary, indent=2) + "\n")
    pages[0].save(output / "owner-review.pdf", save_all=True, append_images=pages[1:])
    print(json.dumps({"states": len(records), "output": str(output), "status": summary["status"]}))


if __name__ == "__main__":
    main()
