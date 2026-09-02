#!/usr/bin/env python3
"""Build a portable owner-review packet for the P0 public-header hotfix."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


STATES = [
    ("home", 1440, 1000), ("home", 1280, 800), ("home", 390, 844),
    ("library", 1440, 1000), ("library", 1280, 800), ("library", 390, 844),
    ("commerce", 1440, 1000), ("commerce", 1280, 800), ("commerce", 390, 844),
    ("book-detail", 1440, 1000), ("book-detail", 390, 844),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Missing review capture: {filename}")
    return matches[0]


def records_for(root: Path) -> list[dict]:
    records: list[dict] = []
    for path in root.rglob("metrics-*.json"):
        records.extend(json.loads(path.read_text()).get("records", []))
    return records


def metric(records: list[dict], route_id: str, width: int, height: int) -> dict:
    return next((record for record in records if record.get("routeId") == route_id and record.get("width") == width and record.get("height") == height), {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="uat/evidence/p0-header-readability/20260831T000000Z")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    before, after = root / "before", root / "after"
    output = root / "owner-review"
    output.mkdir(parents=True, exist_ok=True)
    before_metrics, after_metrics = records_for(before), records_for(after)
    pages: list[Image.Image] = []
    items: list[dict] = []
    font = ImageFont.load_default()

    for route_id, width, height in STATES:
        name = f"{route_id}-{width}x{height}-chromium.png"
        before_image, after_image = find(before, name), find(after, name)
        before_copy, after_copy = output / f"before-{name}", output / f"after-{name}"
        before_copy.write_bytes(before_image.read_bytes())
        after_copy.write_bytes(after_image.read_bytes())
        before_record = metric(before_metrics, route_id, width, height)
        after_record = metric(after_metrics, route_id, width, height)
        items.append({
            "route": route_id, "viewport": {"width": width, "height": height},
            "before": before_copy.name, "after": after_copy.name,
            "before_metrics": before_record, "after_metrics": after_record,
        })
        canvas = Image.new("RGB", (1600, 1120), "#f6f1e8")
        draw = ImageDraw.Draw(canvas)
        draw.text((32, 24), f"{route_id} - {width}x{height} | P0 public-header readability", fill="#142019", font=font)
        before_panel = Image.open(before_image).convert("RGB"); before_panel.thumbnail((750, 970))
        after_panel = Image.open(after_image).convert("RGB"); after_panel.thumbnail((750, 970))
        canvas.paste(before_panel, (32, 92)); canvas.paste(after_panel, (818, 92))
        summary = (
            f"Before: header {(before_record.get('header') or {}).get('height')}px, nav {(before_record.get('nav') or {}).get('fontSize')} | "
            f"After: header {after_record.get('header', {}).get('height')}px, lockup {after_record.get('brand', {}).get('width')}px, "
            f"nav {(after_record.get('nav') or {}).get('fontSize')}, contrast {after_record.get('navContrast')}, "
            f"overflow {after_record.get('overflow')}, clipping {after_record.get('clipping')}"
        )
        draw.text((32, 64), summary, fill="#6b1020", font=font)
        pages.append(canvas)

    contact = Image.new("RGB", (1600, ((len(items) + 3) // 4) * 310), "#f6f1e8")
    draw = ImageDraw.Draw(contact)
    for index, item in enumerate(items):
        image = Image.open(output / item["after"]).convert("RGB"); image.thumbnail((380, 260))
        x, y = (index % 4) * 400 + 10, (index // 4) * 310 + 34
        draw.text((x, y - 18), f"{item['route']} {item['viewport']['width']}x{item['viewport']['height']}", fill="#142019", font=font)
        contact.paste(image, (x, y))
    contact.save(output / "contact-sheet.png")
    pages[0].save(output / "owner-review.pdf", save_all=True, append_images=pages[1:], resolution=144.0)

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    provenance = {
        "schema_version": "earnalism.p0_header_readability.owner_review.v1",
        "base_sha": subprocess.check_output(["git", "merge-base", "HEAD", "origin/main"], text=True).strip(),
        "worktree_head": head,
        "capture_engines": ["chromium", "firefox", "webkit"],
        "routes": ["/", "/library", "/pricing", "/book/dracula", "/about", "/login", "/account (sanitized fixture)"],
        "production_mutations": 0,
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (output / "metrics.json").write_text(json.dumps(items, indent=2) + "\n")
    body = "".join(
        f"<section><h2>{item['route']} - {item['viewport']['width']}x{item['viewport']['height']}</h2>"
        f"<p>Before nav: {(item['before_metrics'].get('nav') or {}).get('fontSize')}; after nav: {(item['after_metrics'].get('nav') or {}).get('fontSize')}; "
        f"after contrast: {item['after_metrics'].get('navContrast')}; overflow: {item['after_metrics'].get('overflow')}; clipping: {item['after_metrics'].get('clipping')}.</p>"
        f"<div><figure><img src='{item['before']}'><figcaption>Before</figcaption></figure><figure><img src='{item['after']}'><figcaption>After</figcaption></figure></div></section>"
        for item in items
    )
    (output / "owner-review.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Earnalism P0 header review</title>"
        "<style>body{margin:0;background:#f6f1e8;color:#142019;font:16px system-ui}header,section{max-width:1600px;margin:auto;padding:20px}section{border-top:1px solid #c9a75b}div{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}figure{margin:0}img{width:100%;border:1px solid #c9a75b}figcaption{margin-top:6px}@media(max-width:700px){div{grid-template-columns:1fr}}</style>"
        "<header><h1>Earnalism P0 public-header readability</h1><p>Read-only local UAT evidence. No production or product-truth mutation was made.</p></header>" + body
    )
    manifest = {"files": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(output.iterdir()) if path.is_file()]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(output), "states": len(items)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
