# Home Curated Shelf Collage V2 Review

## Root Cause

The previous implementation used implicit CSS Grid placement with unequal column spans and row spans. Browser auto-placement therefore pushed Short Masterpieces below the intended composition, left an unanchored lower-right area, and allowed the Bengali feature tile to absorb excessive height. Cover selection also trusted URL presence and rendered generic runtime/placeholder-looking assets.

## Implemented

- Replaced implicit placement with named, deterministic editorial grid areas.
- Added the required 12-column desktop composition and a two-column 768-1279px composition.
- Added a one-column mobile composition and a deterministic missing-short fallback that collapses the grid without an empty quadrant.
- Rebuilt the Bengali feature anatomy with metadata, description, editorial line, controlled cover zone, plinth, and CTA.
- Normalized supporting-card anatomy, title slots, counts, icons, accents, cover stage, CTA baseline, focus states, and reduced-motion behavior.
- Added a dynamic cover-truth contract backed by the checked-in cover-generation report.
- Disabled graphical fallback rendering inside the collage and listening rail.
- Added a dynamic Selected Listening rail that is omitted cleanly when no approved audiobook has a trustworthy canonical cover.
- Added a dark-to-parchment hero transition and restrained ornamental divider.

## Canonical Visual Result

The final render has no broken images, no placeholder covers, no repeated visible shelf cover, no audio controls for hidden titles, no horizontal overflow, and no orphaned card. The visible shelf selection is Bengali (`radharani`, `nishkriti`, `book-edfcf810c5`), Gothic (`dracula`), Love (`pride-and-prejudice`), and Adventure (`the-time-machine`, `the-call-of-the-wild`, `the-secret-garden`).

Short Masterpieces is intentionally omitted because every configured candidate is missing, a runtime fallback, or a visually reviewed generic template. The Selected Listening rail is also intentionally omitted because all four approved audiobook records currently fail the visual cover predicate: runtime fallback, title mismatch, or the same generic template. The approved records remain in the backend truth payload; only their Home visual cards are withheld. This is a catalog-art defect, not an audio release-gate change.

## Evidence

Captured at:

- 1440x900
- 1536x864
- 1180x900
- 984x1364
- 768x1024
- 430x932
- 390x844

Runtime metrics are recorded in `HOME_collage_v2_runtime_metrics.json`. The 984px and 768px captures use the two-column layout; the mobile captures use one-column placement. All captured viewports reported zero horizontal overflow and zero console errors.

## Score Decision

Measured score: **9.1/10**, not 10/10. A 10/10 claim is intentionally withheld because the current catalog does not provide enough trustworthy artwork to render all five shelves and the approved listening rail. The next unlock is to replace the eight omitted generic/mismatched cover assets with title-bound graphical covers, rerun `node frontend/scripts/audit-book-covers.mjs`, regenerate the Home snapshot, and recapture the matrix.

## Release Safety

No reader route, audiobook release gate, approved audio package, paid audio lock, TTS, ASR, upload, or publication state was changed. The collage only filters visual discovery candidates; canonical records remain available through their normal routes.
