#!/usr/bin/env python3
"""Create a self-contained owner-review package for public-page visual work.

Composite design boards are kept at native proportions. The package labels
derived heatmaps as diagnostic so they cannot be mistaken for a full-viewport
pixel certification.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont


STATES = ("home-desktop", "home-mobile", "library-desktop", "library-mobile", "commerce-desktop", "commerce-mobile")

CANONICAL_CROPS = {
    "home-desktop": {"x": 10, "y": 18, "width": 540, "height": 747},
    "library-desktop": {"x": 560, "y": 18, "width": 518, "height": 747},
    "commerce-desktop": {"x": 0, "y": 0, "width": 1536, "height": 1024},
    "home-mobile": {"x": 24, "y": 792, "width": 198, "height": 232},
    "library-mobile": {"x": 265, "y": 792, "width": 222, "height": 232},
    "commerce-mobile": {"x": 793, "y": 792, "width": 193, "height": 232},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def safe_copy(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copy2(source, destination)


def reference_panel(root: Path, capability: dict, state: str) -> Image.Image:
    item = capability["states"][state]
    crop = CANONICAL_CROPS[state]
    source = Image.open(root / "docs/design-references" / item["source_file"]).convert("RGB")
    panel = source.crop((crop["x"], crop["y"], crop["x"] + crop["width"], crop["y"] + crop["height"]))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((1, 1, panel.width - 2, panel.height - 2), outline="#d6ad55", width=max(1, panel.width // 120))
    return panel


def diagnostic_heatmap(panel: Image.Image, current: Image.Image) -> Image.Image:
    # This intentionally preserves the native reference panel size and labels
    # the result elsewhere. It is a diagnostic image, never a pass/fail score.
    actual = current.convert("RGB").resize(panel.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(panel.convert("RGB"), actual)
    return diff.point(lambda value: min(255, value * 4))


def build_html(records: list[dict], controlled: Optional[dict]) -> str:
    buttons = "".join(f'<button data-state="{item["state"]}">{item["state"]}</button>' for item in records)
    product_truth = """<section class=\"product-truth\"><h2>OWNER PRODUCT-TRUTH AMENDMENT</h2><p><b>TEXT:</b> exactly the first 3 immutable server-defined canonical pages are public; page 4 and later require a signed-in paid Reading Pass entitlement.</p><p><b>AUDIO:</b> public preview duration is exactly 0 seconds. Catalog and reader manifests may show locked metadata, but expose no playable URL or public audio bytes. Playback requires an approved audiobook and an active paid Reading Pass from the first byte, including range requests.</p><p><b>APPROVED COPY:</b> Read the first 3 pages free. Listening requires an active Reading Pass.</p></section>"""
    panels = "".join(
        f'''<section id="{item["state"]}" class="panel"><h2>{item["state"]}</h2><p><b>REFERENCED REGION</b> uses the native composite panel. <b>RESPONSIVE EXTRAPOLATION</b> applies outside it. <b>DYNAMIC DATA</b> includes covers, text, prices, and release labels. <b>NOT PIXEL-CERTIFIABLE FROM CURRENT REFERENCE</b> applies to the full mobile viewport.</p><div class="grid"><figure><img src="{item["reference"]}"><figcaption>Approved composite reference</figcaption></figure><figure><img src="{item["before"]}"><figcaption>Original-main capture</figcaption></figure><figure><img src="{item["current"]}"><figcaption>Current PR capture</figcaption></figure><figure><img src="{item["heatmap"]}"><figcaption>Diagnostic heatmap, not full-viewport certification</figcaption></figure></div></section>'''
        for item in records
    )
    controlled_section = ""
    if controlled:
        aggregate = controlled["controlled_base_current"]
        commerce = controlled["commerce_three_way"]
        controlled_section = f'''<section class="product-truth"><h2>CONTROLLED MEASUREMENT RECONCILIATION</h2><p><b>HISTORICAL PRODUCTION FIXTURE:</b> {controlled["historical_production_fixture"]["raw_aggregate_score"]:.6f}; retained as historical evidence only because its live catalogue fixture differs.</p><p><b>CONTROLLED BASE/CURRENT:</b> {aggregate["base_raw_aggregate"]:.6f} to {aggregate["current_raw_aggregate"]:.6f}; {aggregate["mismatch_pixel_reduction"]:,} fewer mismatched pixels across {aggregate["comparable_pixels"]:,} comparable pixels.</p><p><b>CONTROLLED COMMERCE BASE/CHECKPOINT/CURRENT:</b> {commerce["base"]["raw_score"]:.6f} / {commerce["checkpoint"]["raw_score"]:.6f} / {commerce["current"]["raw_score"]:.6f}; non-regression {commerce["non_regression"]}; masks {commerce["mask_coverage_percent"]}%.</p><p><b>STRUCTURAL:</b> {controlled["structural_contract"]["aggregate"]["passed"]}/{controlled["structural_contract"]["aggregate"]["total"]}. <b>TRUTH-SAFE CONTENT:</b> {controlled["truth_safe_content_score"]:.6f}. <b>PRODUCT TRUTH:</b> {controlled["product_truth_score"]:.6f}.</p><p>See <code>controlled-reconciliation.json</code> and <code>primary-visual-owner-asset-gaps.md</code> for the full immutable-snapshot contract and owner-input decision.</p></section>'''
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Earnalism public pages owner review</title><style>body{{margin:0;background:#f6f1e8;color:#15201a;font:16px system-ui,sans-serif}}header{{position:sticky;top:0;padding:12px 20px;background:#07100f;color:#fff8e9;z-index:2}}button{{margin:3px;padding:7px 10px;border:1px solid #d6ad55;background:#10251f;color:#fff8e9}}main{{padding:24px;max-width:1600px;margin:auto}}.product-truth{{margin:0 0 32px;padding:20px;border:1px solid #d6ad55;background:#fffdf8}}.product-truth h2{{margin-top:0}}.panel{{margin:0 0 48px}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}figure{{margin:0;border:1px solid #d7c69f;background:#fffdf8;padding:8px}}img{{width:100%;height:auto;display:block}}figcaption{{margin-top:8px;font-size:12px}}@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}</style></head><body><header><strong>Earnalism public pages owner review</strong><div>{buttons}</div></header><main>{controlled_section}{product_truth}{panels}</main><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>document.getElementById(b.dataset.state).scrollIntoView({{behavior:'smooth'}}));</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--before", default="uat/evidence/actual-redesign/before")
    parser.add_argument("--current", default="uat/evidence/actual-redesign/convergence-v2/current")
    parser.add_argument("--output", default="uat/evidence/actual-redesign/owner-review-final")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    capability = load(root / "docs/design-references/primary-experience-reference-capability.json")
    controlled_path = root / "uat/evidence/primary-visual-convergence/controlled-reconciliation.json"
    controlled = load(controlled_path) if controlled_path.exists() else None
    records = []
    pdf_pages = []
    for state in STATES:
        panel = reference_panel(root, capability, state)
        reference_name = f"{state}-reference-region.png"
        panel.save(output / reference_name)
        before = root / args.before / f"{state}.png"
        current = root / args.current / f"{state}.png"
        if not current.exists():
            current = root / "uat/evidence/actual-redesign/after" / f"{state}.png"
        before_name = f"{state}-before.png"; current_name = f"{state}-current.png"
        safe_copy(before, output / before_name); safe_copy(current, output / current_name)
        heatmap_name = f"{state}-diagnostic-heatmap.png"
        if current.exists():
            diagnostic_heatmap(panel, Image.open(current)).save(output / heatmap_name)
        records.append({
            "state": state, "reference": reference_name, "before": before_name,
            "current": current_name, "heatmap": heatmap_name,
            "reference_capability": capability["states"][state],
            "labels": ["REFERENCED REGION", "RESPONSIVE EXTRAPOLATION", "DYNAMIC DATA", "NOT PIXEL-CERTIFIABLE FROM CURRENT REFERENCE"],
        })
        page = Image.new("RGB", (1600, 1120), "#f6f1e8")
        draw = ImageDraw.Draw(page); draw.text((40, 30), f"{state} - REFERENCED REGION / OWNER REVIEW", fill="#15201a", font=ImageFont.load_default())
        draw.text((40, 50), "Product truth: 3 public canonical pages; 0 public audio seconds; active Reading Pass required to listen.", fill="#15201a", font=ImageFont.load_default())
        if controlled:
            aggregate = controlled["controlled_base_current"]
            commerce = controlled["commerce_three_way"]
            draw.text((40, 70), f"Controlled base/current: {aggregate['base_raw_aggregate']:.6f} -> {aggregate['current_raw_aggregate']:.6f}; Commerce base/checkpoint/current: {commerce['base']['raw_score']:.6f} / {commerce['checkpoint']['raw_score']:.6f} / {commerce['current']['raw_score']:.6f}", fill="#15201a", font=ImageFont.load_default())
        thumbnail = panel.copy(); thumbnail.thumbnail((700, 930)); page.paste(thumbnail, (40, 110))
        if current.exists():
            actual = Image.open(current).convert("RGB"); actual.thumbnail((700, 930)); page.paste(actual, (840, 110))
        pdf_pages.append(page)
    manifest = {
        "schema_version": "earnalism-public-pages-owner-review-v1",
        "product_truth_amendment": {
            "text_public_page_limit": 3,
            "audio_public_preview_seconds": 0,
            "approved_copy": "Read the first 3 pages free. Listening requires an active Reading Pass.",
        },
        "records": records,
        "status": "OWNER_VISUAL_APPROVAL_REQUIRED",
    }
    (output / "public-pages-owner-review.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "public-pages-owner-review.html").write_text(build_html(records, controlled))
    pdf_pages[0].save(output / "public-pages-owner-review.pdf", save_all=True, append_images=pdf_pages[1:])
    print(json.dumps({"output": str(output), "states": len(records), "status": manifest["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
