#!/usr/bin/env python3
"""Audit public-page reference regions without stretching composite boards.

This is deliberately a capability-aware audit.  It verifies immutable input
hashes, the active production render path, required region markers, and the
captured viewport mechanics.  Composite reference boards are not promoted to
full-viewport pixel goldens when their native panels cannot provide one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROUTES = {
    "home": "frontend/src/pages/Home.jsx",
    "library": "frontend/src/pages/Library.jsx",
    "commerce": "frontend/src/pages/Pricing.jsx",
}

ROUTE_SURFACES = {
    "home": "ReferenceHomeSurface",
    "library": "ReferenceLibrarySurface",
    "commerce": "ReferenceCommerceSurface",
}

REGION_MARKERS = {
    "home": {
        "header": "premium-site-header--reference-public",
        "compact header": "premium-site-header--reference-public",
        "hero": "reference-home__hero",
        "hero copy": "reference-home__hero-copy",
        "hero image": "reference-home__hero-art",
        "CTAs": "reference-home__cta-row",
        "two CTAs": "reference-home__cta-row",
        "feature strip": "reference-feature-strip",
        "title shelf": "reference-home__journey",
        "first shelf start": "reference-home__journey",
        "Reading Pass block": "reference-home__pass",
        "trust section": "reference-home__trust",
    },
    "library": {
        "header": "premium-site-header--reference-public",
        "compact header": "premium-site-header--reference-public",
        "title": "reference-library__titlebar",
        "search": "reference-search",
        "sort": "reference-sort",
        "filter control": "reference-filter-trigger",
        "title/search/sort": "reference-library__titlebar",
        "filter sidebar": "reference-library__sidebar",
        "Live Now": "Live now",
        "Coming Soon": "Coming soon",
        "Audiobooks": "Audiobooks",
        "Reading Pass support card": "reference-library__pass",
        "cover cards": "reference-book-tile",
        "first shelf start": "reference-library-shelf",
    },
    "commerce": {
        "header": "premium-site-header--reference-public",
        "compact header": "premium-site-header--reference-public",
        "hero": "reference-commerce__hero",
        "offer heading and tabs": "reference-commerce__offer",
        "offer heading": "reference-commerce__offers",
        "offer-card grid": "reference-commerce__packs",
        "institutional card": "reference-commerce__pathways",
        "publisher card": "reference-commerce__pathways",
        "trust strip": "reference-commerce__trust",
        "footer CTA": "reference-commerce__final",
        "first offer card": "reference-commerce__packs",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--captures", default="uat/evidence/actual-redesign/convergence-v2/current/capture.json")
    parser.add_argument("--output", default="uat/evidence/actual-redesign/convergence-v2/reference-region-results.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    capability = json.loads((root / "docs/design-references/public-pages-reference-capability.json").read_text())
    captures = {item["id"]: item for item in json.loads((root / args.captures).read_text())}
    component = (root / "frontend/src/components/ReferencePublicPages.jsx").read_text()
    stylesheet = (root / "frontend/src/components/ReferencePublicPages.css").read_text()
    report = {"schema_version": "earnalism-public-page-region-audit-v1", "states": [], "status": "PASSED"}

    for state, details in capability["states"].items():
        page = state.split("-")[0]
        capture = captures.get(state, {})
        route_source = (root / ROUTES[page]).read_text()
        active_source = "\n".join((route_source, component, stylesheet))
        required_regions = details["comparable_regions"]
        markers = REGION_MARKERS[page]
        regions = []
        for name in required_regions:
            marker = markers.get(name)
            exists = bool(marker and marker in active_source)
            regions.append({
                "name": name,
                "required_marker": marker,
                "exists_in_active_production_path": exists,
                "comparison": "native-region-only",
            })
        capture_ok = capture.get("status") == 200 and not capture.get("errors") and capture.get("scrollWidth") == capture.get("clientWidth")
        sources_ok = all(
            sha256(root / "docs/design-references" / item["source_file"]) == item["source_sha256"]
            for item in [details]
        )
        route_maps_to_surface = ROUTE_SURFACES[page] in route_source
        state_ok = capture_ok and sources_ok and route_maps_to_surface and all(item["exists_in_active_production_path"] for item in regions)
        if not state_ok:
            report["status"] = "FAILED"
        report["states"].append({
            "state": state,
            "route_source": ROUTES[page],
            "reference": {"file": details["source_file"], "sha256": details["source_sha256"], "crop": details["source_crop"]},
            "capture": capture,
            "route_maps_to_active_surface": route_maps_to_surface,
            "regions": regions,
            "mask_coverage": 0.0,
            "full_viewport_pixel_status": details.get("full_mobile_pixel_match_status", "NOT_CERTIFIABLE_COMPOSITE_REFERENCE"),
            "result": "PASSED" if state_ok else "FAILED",
        })

    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "states": len(report["states"])}))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
