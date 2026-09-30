#!/usr/bin/env python3
"""Package exact-head supplemental post-merge Option B owner evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source: Path, destination: Path, label: str) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"required owner evidence is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {"label": label, "filename": destination.name, "sha256": sha(destination), "bytes": destination.stat().st_size}


def image_contact_sheet(images: list[tuple[str, Path]], destination: Path) -> None:
    columns, tile_w, tile_h, label_h, pad = 4, 380, 260, 34, 18
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (tile_w + pad) + pad, rows * (tile_h + label_h + pad) + pad), "#f7f1e7")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
        small = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        font, small = ImageFont.load_default(), ImageFont.load_default()
    for index, (label, path) in enumerate(images):
        x = pad + (index % columns) * (tile_w + pad)
        y = pad + (index // columns) * (tile_h + label_h + pad)
        image = Image.open(path).convert("RGB")
        image.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
        draw.rounded_rectangle((x, y, x + tile_w, y + tile_h + label_h), radius=4, fill="#fffdf8", outline="#c7ad8c", width=1)
        sheet.paste(image, (x + (tile_w - image.width) // 2, y + (tile_h - image.height) // 2))
        draw.text((x + 10, y + tile_h + 5), label, fill="#431018", font=font)
        draw.text((x + 10, y + tile_h + 24), path.name, fill="#67594c", font=small)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior", required=True, help="Extracted exact-head PR469 owner-review artifact root")
    parser.add_argument("--library", required=True, help="Output directory from test_library_catalogue_recovery_journey.mjs")
    parser.add_argument("--supplemental", required=True, help="Output directory from capture_pr469_postmerge_recovery_states.mjs")
    parser.add_argument("--output", required=True, help="Evidence package output directory")
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args()

    prior, library, supplemental, output = map(Path, (args.prior, args.library, args.supplemental, args.output))
    output.mkdir(parents=True, exist_ok=True)
    images_dir = output / "owner-approval-images"
    images_dir.mkdir(parents=True, exist_ok=True)

    selections = [
        ("home-option-b-1440.png", prior / "screenshots/chromium/states/home-desktop/viewport.png", "Home · approved Option B · 1440"),
        ("library-normal-1440.png", prior / "screenshots/chromium/states/library-desktop/viewport.png", "Library · populated · 1440"),
        ("book-detail-live-1440.png", prior / "screenshots/chromium/states/book-detail-live-desktop-1440/viewport.png", "Live Book Detail · 1440"),
        ("book-detail-unavailable-1440.png", prior / "screenshots/chromium/states/book-detail-desktop/viewport.png", "Unavailable Book Detail · 1440"),
        ("reading-pass-four-offers-1440.png", prior / "screenshots/chromium/states/commerce-offers-desktop-1440/viewport.png", "Reading Pass · four offers · 1440"),
        ("account-populated-fixture-1440.png", prior / "screenshots/chromium/states/account-desktop/viewport.png", "Account · sanitized fixture · 1440"),
        ("my-library-empty-1440.png", prior / "screenshots/chromium/states/my-library-desktop/viewport.png", "My Library · truthful empty state · 1440"),
        ("reader-chrome-1440.png", prior / "screenshots/chromium/states/reader-desktop/viewport.png", "Reader · immersive brand chrome · 1440"),
        ("listener-unavailable-1440.png", prior / "screenshots/chromium/states/disabled-listener-dracula-desktop/viewport.png", "Listener · fail-closed state · 1440"),
        ("privacy-1440.png", prior / "screenshots/chromium/states/privacy-desktop/viewport.png", "Privacy · shared legal template · 1440"),
        ("not-found-1440.png", prior / "screenshots/chromium/states/error-404-desktop/viewport.png", "404 · 1440"),
        ("library-loading-1440.png", library / "library-loading-1440.png", "Library · loading · 1440"),
        ("library-no-results-1024.png", library / "library-no-results-1024.png", "Library · no results · 1024"),
        ("library-error-1440.png", library / "library-error-1440.png", "Library · API error + retry · 1440"),
        ("library-recovered-1440.png", library / "library-recovery-1440.png", "Library · recovered after retry · 1440"),
        ("reading-pass-unavailable-1440.png", supplemental / "reading-pass-api-unavailable-1440.png", "Reading Pass · API unavailable · 1440"),
        ("newsletter-success-1440.png", supplemental / "newsletter-success-1440.png", "Newsletter · local success fixture · 1440"),
        ("newsletter-error-1440.png", supplemental / "newsletter-error-1440.png", "Newsletter · local error fixture · 1440"),
        ("contact-success-1440.png", supplemental / "contact-success-1440.png", "Contact · synthetic success · 1440"),
        ("contact-error-1440.png", supplemental / "contact-error-1440.png", "Contact · synthetic error · 1440"),
        ("login-validation-1440.png", supplemental / "login-validation-1440.png", "Login · validation + continuation · 1440"),
        ("login-submitting-1440.png", supplemental / "login-submitting-1440.png", "Login · submitting · 1440"),
        ("signup-validation-1440.png", supplemental / "signup-validation-1440.png", "Signup · validation · 1440"),
        ("signup-submitting-1440.png", supplemental / "signup-submitting-1440.png", "Signup · submitting · 1440"),
    ]
    records = [copy(source, images_dir / filename, label) for filename, source, label in selections]
    for filename in sorted(library.glob("*.png")):
        if filename not in {source for _, source, _ in selections}:
            records.append(copy(filename, images_dir / f"library-recovery-{filename.name}", f"Library recovery evidence · {filename.stem}"))
    for filename in sorted(supplemental.glob("*.png")):
        records.append(copy(filename, images_dir / filename.name, f"Supplemental state · {filename.stem}"))

    contact_sheet = output / "owner-review-contact-sheet.png"
    image_contact_sheet([(label, images_dir / filename) for filename, _, label in selections], contact_sheet)
    exact_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    delta_selections = [
        ("delta-login-1440.png", supplemental / "login-validation-1440.png", "Login · release-safe copy · 1440"),
        ("delta-login-390.png", supplemental / "login-validation-390.png", "Login · release-safe copy · 390"),
        ("delta-signup-1440.png", supplemental / "signup-validation-1440.png", "Signup · release-safe copy · 1440"),
        ("delta-signup-390.png", supplemental / "signup-validation-390.png", "Signup · release-safe copy · 390"),
        ("delta-book-detail-a-ghost-story-1440.png", supplemental / "book-detail-a-ghost-story-1440.png", "A Ghost Story · audio release-safe · 1440"),
        ("delta-book-detail-a-ghost-story-390.png", supplemental / "book-detail-a-ghost-story-390.png", "A Ghost Story · audio release-safe · 390"),
        ("delta-book-detail-coming-soon-1440.png", supplemental / "book-detail-coming-soon-1440.png", "Coming-soon title · non-readable · 1440"),
        ("delta-book-detail-coming-soon-390.png", supplemental / "book-detail-coming-soon-390.png", "Coming-soon title · non-readable · 390"),
        ("delta-reader-default-no-focus-1440.png", supplemental / "reader-default-no-focus-1440.png", "Reader · default no-focus · 1440"),
        ("delta-reader-default-no-focus-390.png", supplemental / "reader-default-no-focus-390.png", "Reader · default no-focus · 390"),
        ("delta-reader-keyboard-focus-1440.png", supplemental / "reader-keyboard-focus-1440.png", "Reader · keyboard focus · 1440"),
        ("delta-reader-keyboard-focus-390.png", supplemental / "reader-keyboard-focus-390.png", "Reader · keyboard focus · 390"),
    ]
    for width in (1440, 390):
        for state, source_name, label in (
            ("api-error", f"library-api-error-{width}.png", "Library API error"),
            ("retry-visible", f"library-retry-visible-{width}.png", "Library retry visible"),
            ("recovered", f"library-recovery-{width}.png", "Library recovered catalogue"),
        ):
            delta_selections.append((f"delta-library-{state}-{width}.png", library / source_name, f"{label} · {width}"))
    for width in (1440, 1024, 390):
        delta_selections.append((f"delta-library-live-and-coming-soon-{width}.png", supplemental / f"library-canonical-live-and-coming-soon-{width}.png", f"Library · canonical live + coming soon · {width}"))
    delta_records = [copy(source, images_dir / filename, label) for filename, source, label in delta_selections]
    delta_contact_sheet = output / "owner-delta-contact-sheet.png"
    image_contact_sheet([(label, images_dir / filename) for filename, _, label in delta_selections], delta_contact_sheet)
    delta_manifest = {
        "schema_version": "earnalism.pr471-owner-delta-evidence.v1",
        "repository": "ronik18/earnalism-digital-library",
        "pr_number": args.pr,
        "repair_head": exact_head,
        "classification": "LOCAL_DETERMINISTIC_FIXTURES_NO_PRODUCTION_REQUESTS_OR_MUTATIONS",
        "reader_default_state": "The route initially focuses its non-interactive chapter heading for reading context; screenshots capture the default after blur. Interactive controls retain :focus-visible styling.",
        "canonical_release_state": "The Library fixture reads the canonical controlled-launch allowlist and A Ghost Story public package. It distinguishes canonical reader publication from the separate runtime Reading Pass manifest gate. The captured A Ghost Story detail remains in the truthful Reader-unavailable state because the fixture does not invent runtime segment readiness.",
        "library_recovery": "Error/retry captures show the active Retry action. Recovered state follows a successful local catalogue API fixture response for A Ghost Story, not bundled fallback inventory.",
        "screenshots": delta_records,
        "contact_sheet": {"filename": delta_contact_sheet.name, "sha256": sha(delta_contact_sheet)},
    }
    delta_manifest_path = output / "owner-delta-manifest.json"
    delta_manifest_path.write_text(json.dumps(delta_manifest, indent=2) + "\n")
    delta_zip = output / "owner-delta-images.zip"
    with zipfile.ZipFile(delta_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(delta_contact_sheet, delta_contact_sheet.name)
        archive.write(delta_manifest_path, delta_manifest_path.name)
        for filename, _, _ in delta_selections:
            archive.write(images_dir / filename, f"owner-delta-images/{filename}")
    prior_head = "b5d607a89ed756ab5efca058379ed1201b7d234b"
    library_summary = json.loads((library / "summary.json").read_text())
    supplemental_summary = json.loads((supplemental / "summary.json").read_text())
    manifest = {
        "schema_version": "earnalism.pr471-postmerge-recovery-owner-review.v1",
        "repository": "ronik18/earnalism-digital-library",
        "pr_number": args.pr,
        "repair_head": exact_head,
        "prior_owner_reviewed_head": prior_head,
        "prior_evidence_run_id": 36549307831,
        "prior_evidence_artifact_id": 11025247154,
        "prior_evidence_reuse": "Unchanged Option B/product states only; every affected PR471 auth, Book Detail, Reader, and Library recovery state is freshly captured against repair head.",
        "capture_classification": "LOCAL_DETERMINISTIC_FIXTURES_NO_PRODUCTION_REQUESTS_OR_MUTATIONS",
        "my_library": "NA_PRODUCT_STATE: current product has no saved-book or reading-history source; truthful empty state retained.",
        "library_journey_result": library_summary.get("result"),
        "supplemental_capture_result": supplemental_summary.get("result"),
        "owner_visual_approval": "OWNER_REVIEW_REQUIRED",
        "screenshots": records,
        "contact_sheet": {"filename": contact_sheet.name, "sha256": sha(contact_sheet)},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    readme = (
        f"PR {args.pr} post-merge production-readiness repair owner review\n"
        f"Exact repair head: {exact_head}\n"
        f"Prior approved Option B head: {prior_head}\n\n"
        "This packet contains approved exact-head PR469 imagery for unchanged states, plus fresh loopback-only captures for requested PR471 deltas. Interactions use synthetic local responses and fixtures. No production account, payment, customer record, catalogue state, or audio state was changed. My Library remains an honest empty state because no saved-book or reading-history API exists.\n\n"
        "Automated capture does not equal owner visual approval. Every owner checklist item remains OWNER_REVIEW_REQUIRED. See manifest.json for screenshot hashes and fixture classification.\n"
    )
    (output / "README.txt").write_text(readme)
    with zipfile.ZipFile(output / "owner-approval-images.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(contact_sheet, contact_sheet.name)
        archive.write(delta_contact_sheet, delta_contact_sheet.name)
        archive.write(output / "manifest.json", "manifest.json")
        archive.write(delta_manifest_path, delta_manifest_path.name)
        archive.write(output / "README.txt", "README.txt")
        for image in sorted(images_dir.iterdir()):
            if image.is_file():
                archive.write(image, f"owner-approval-images/{image.name}")
    print(json.dumps({"result": "PASS", "exact_head": exact_head, "screenshot_count": len(records), "delta_screenshot_count": len(delta_records), "contact_sheet": str(contact_sheet), "delta_contact_sheet": str(delta_contact_sheet), "delta_zip": str(delta_zip), "zip": str(output / "owner-approval-images.zip")}, indent=2))


if __name__ == "__main__":
    main()
