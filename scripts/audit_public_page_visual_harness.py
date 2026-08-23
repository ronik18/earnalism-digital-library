#!/usr/bin/env python3
"""Audit immutable public-page reference inputs without changing their authority.

The approved PNGs are composite design boards. A direct screenshot comparison is
valid only when the locked panel can supply a viewport-sized, aspect-preserving
window. This script rejects non-uniform stretching and records why a state is
not comparable instead of manufacturing a pixel score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


VIEWPORTS = {
    "home-desktop": (1440, 1000), "library-desktop": (1440, 1000), "commerce-desktop": (1440, 1000),
    "home-mobile": (390, 844), "library-mobile": (390, 844), "commerce-mobile": (390, 844),
}

REGIONS = {
    "home": ["header", "hero copy", "hero image", "CTAs", "feature strip", "title shelf", "Reading Pass block", "trust section", "footer"],
    "library": ["header", "title/search/sort", "filter sidebar or mobile drawer", "Live Now", "Coming Soon", "Audiobooks", "Reading Pass support card", "cover cards"],
    "commerce": ["header", "hero", "offer heading/tabs", "offer-card grid", "institutional card", "publisher card", "gift area when real", "trust strip", "footer CTA"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def average_rgb(image: Image.Image) -> list[int]:
    return [round(value) for value in ImageStat.Stat(image.convert("RGB")).mean]


def normalized_diff(expected: Image.Image, actual: Image.Image) -> float:
    diff = ImageChops.difference(expected.convert("RGB"), actual.convert("RGB"))
    channels = ImageStat.Stat(diff).mean
    return sum(channels) / (255 * len(channels))


def region_box(index: int, count: int, width: int, height: int) -> tuple[int, int, int, int]:
    # Deterministic vertical bands provide a complete, non-masked contribution
    # breakdown when no DOM-to-reference geometry mapping exists.
    top = round(index * height / count)
    bottom = round((index + 1) * height / count)
    return (0, top, width, bottom)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--lock", default="uat/contracts/public-pages-visual-lock.json")
    parser.add_argument("--captures", default="uat/evidence/actual-redesign/after")
    parser.add_argument("--output-dir", default="uat/evidence/actual-redesign/convergence")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    lock = json.loads((root / args.lock).read_text())
    references = root / "docs/design-references"
    captures = root / args.captures
    output = root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    audit_states = []
    region_rows = []
    for state, viewport in VIEWPORTS.items():
        crop = lock["reference_crops"][state]
        reference_path = references / crop["file"]
        actual_path = captures / f"{state}.png"
        actual = Image.open(actual_path).convert("RGB")
        reference = Image.open(reference_path).convert("RGB")
        panel = reference.crop((crop["x"], crop["y"], crop["x"] + crop["width"], crop["y"] + crop["height"]))
        scale = crop["width"] / viewport[0]
        required_height = viewport[1] * scale
        comparable = abs(actual.width - viewport[0]) <= 1 and abs(actual.height - viewport[1]) <= 1 and required_height <= crop["height"]
        reason = None
        expected = None
        if comparable:
            expected = panel.crop((0, 0, crop["width"], round(required_height))).resize(viewport, Image.Resampling.LANCZOS)
            diff_ratio = normalized_diff(expected, actual)
            alignment = {"x": 0, "y": 0, "mode": "top-viewport-window", "scale": scale}
        else:
            diff_ratio = None
            reason = "reference panel cannot supply the required viewport without non-uniform scaling or an out-of-bounds crop"
            alignment = {"x": 0, "y": 0, "mode": "rejected", "required_panel_height": round(required_height, 3), "available_panel_height": crop["height"]}

        audit_states.append({
            "state": state,
            "reference_source_file": crop["file"],
            "reference_sha256": sha256(reference_path),
            "reference_crop": crop,
            "implementation_screenshot": {"path": str(actual_path.relative_to(root)), "width": actual.width, "height": actual.height},
            "required_viewport": {"width": viewport[0], "height": viewport[1]},
            "device_scale_factor": "unattested-by-legacy-capture",
            "font_loaded_status": "unattested-by-legacy-capture",
            "animation_state": "unattested-by-legacy-capture",
            "deterministic_fixture_data": "unattested-by-legacy-capture",
            "mask_coverage_ratio": 0.0,
            "alignment_offset": alignment,
            "comparison_valid": comparable,
            "comparison_rejection_reason": reason,
            "current_diff_ratio": diff_ratio,
        })

        page = state.split("-")[0]
        for index, name in enumerate(REGIONS[page]):
            box = region_box(index, len(REGIONS[page]), actual.width, actual.height)
            actual_region = actual.crop(box)
            item = {
                "state": state,
                "region": name,
                "x": box[0], "y": box[1], "width": box[2] - box[0], "height": box[3] - box[1],
                "actual_background_rgb": average_rgb(actual_region),
                "actual_font_size": "not derivable from raster; see DOM capture required",
                "actual_line_height": "not derivable from raster; see DOM capture required",
                "actual_spacing": "not derivable from raster; see DOM capture required",
                "actual_border_radius": "not derivable from raster; see DOM capture required",
                "actual_grid_geometry": "not derivable from raster; see DOM capture required",
                "expected_background_rgb": None,
                "expected_font_size": None,
                "expected_line_height": None,
                "expected_spacing": None,
                "expected_border_radius": None,
                "expected_grid_geometry": None,
                "pixel_diff_contribution": None,
                "top_difference_causes": [
                    "reference panel is a scaled full-page composite rather than a viewport capture",
                    "legacy capture does not attest font readiness or device scale",
                    "dynamic source data differs from static design-board content",
                ],
            }
            if expected is not None:
                expected_region = expected.crop(box)
                item["expected_background_rgb"] = average_rgb(expected_region)
                item["pixel_diff_contribution"] = normalized_diff(expected_region, actual_region)
            region_rows.append(item)

    audit = {
        "schema_version": "earnalism-immutable-reference-harness-audit-v1",
        "lock": args.lock,
        "locked_threshold": lock["acceptance"]["max_diff_pixel_ratio"],
        "result": "HARNESS_INPUT_NOT_SUFFICIENT_FOR_FULL_VIEWPORT_CERTIFICATION",
        "states": audit_states,
    }
    region_rows.sort(key=lambda item: item["pixel_diff_contribution"] if item["pixel_diff_contribution"] is not None else -1, reverse=True)
    regions = {
        "schema_version": "earnalism-public-page-region-diffs-v1",
        "result": "NON_COMPARABLE_REGIONS_ARE_REPORTED_NOT_SCORED",
        "regions": region_rows,
    }
    (output / "harness-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (output / "region-diffs.json").write_text(json.dumps(regions, indent=2) + "\n")
    print(json.dumps({"audit": str(output / "harness-audit.json"), "regions": str(output / "region-diffs.json"), "valid_states": sum(state["comparison_valid"] for state in audit_states), "total_states": len(audit_states)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
