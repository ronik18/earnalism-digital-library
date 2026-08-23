#!/usr/bin/env python3
"""Validate Earnalism's capability-aware public-page visual contract.

This rejects a structurally unsafe contract rather than pretending incomplete
composite design boards are full-viewport screenshots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED_STATES = {
    "home-desktop", "library-desktop", "commerce-desktop",
    "home-mobile", "library-mobile", "commerce-mobile",
}
ALLOWED_MASKS = {
    "cover artwork", "book title and author", "actual prices", "live release labels",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> dict:
    capabilities = load(root / "docs/design-references/public-pages-reference-capability.json")
    contract = load(root / "uat/contracts/public-pages-visual-contract-v2.json")
    states = capabilities.get("states", {})
    errors: list[str] = []

    if capabilities.get("historical_full_viewport_contract") != "HISTORICAL_INVALID_FOR_INCOMPLETE_COMPOSITE_REFERENCES":
        errors.append("historical invalid-gate finding is missing")
    if set(states) != REQUIRED_STATES:
        errors.append("capability matrix must contain exactly six public-page states")
    for state in sorted(REQUIRED_STATES):
        item = states.get(state, {})
        source = root / "docs/design-references" / item.get("source_file", "")
        if not source.exists():
            errors.append(f"{state}: reference source is missing")
        elif item.get("source_sha256") != sha256(source):
            errors.append(f"{state}: reference SHA-256 does not match")
        crop = item.get("source_crop", {})
        if not all(isinstance(crop.get(key), int) and crop[key] > 0 for key in ("width", "height")):
            errors.append(f"{state}: native crop dimensions are invalid")
        if state.endswith("mobile"):
            if item.get("full_mobile_pixel_match_status") != "NOT_APPLICABLE_REFERENCE_INCOMPLETE":
                errors.append(f"{state}: incomplete mobile panel must not claim full-viewport pixel certification")
            if item.get("responsive_extrapolation_required") is not True:
                errors.append(f"{state}: responsive extrapolation must be explicit")
        if item.get("complete_viewport_reference") is not False:
            errors.append(f"{state}: composite panel must not be declared a complete viewport")

    region_gate = contract.get("reference_region_fidelity_gate", {})
    if contract.get("historical_v1_status") != "HISTORICAL_INVALID_FOR_INCOMPLETE_COMPOSITE_REFERENCES":
        errors.append("v2 contract does not preserve the historical finding")
    if region_gate.get("uniform_scale_transform_required") is not True:
        errors.append("region gate must require a documented uniform scale transform")
    if set(region_gate.get("dynamic_masks", [])) != ALLOWED_MASKS:
        errors.append("dynamic mask categories differ from the approved set")
    if region_gate.get("maximum_total_mask_coverage_ratio", 1) > 0.2:
        errors.append("total mask coverage exceeds 20 percent")
    if region_gate.get("maximum_single_structural_region_coverage_ratio", 1) > 0.25:
        errors.append("single structural-region mask coverage exceeds 25 percent")
    responsive = contract.get("full_viewport_responsive_gate", {})
    if len(responsive.get("viewports", [])) != 9:
        errors.append("responsive gate must retain all nine required viewports")
    if responsive.get("mobile_full_pixel_match") != "NOT_APPLICABLE_REFERENCE_INCOMPLETE":
        errors.append("responsive gate must not falsely certify full mobile pixels")
    owner = contract.get("owner_visual_approval_gate", {})
    if owner.get("approval_phrase") != "APPROVE_PUBLIC_VISUALS":
        errors.append("owner approval phrase is missing")

    return {"valid": not errors, "errors": errors, "states": sorted(states)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = validate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
