# BRAND_HEADER_LOGO Review

Generated: 2026-07-08T09:45:51Z

## Strategy

This is a separate `BRAND_HEADER_EXPERIMENT`, not part of AUDIOBOOK_PLAYER or SETTINGS. HOME, LIBRARY, BOOK_DETAIL, READER, and AUDIOBOOK_PLAYER approval state is unchanged. `paid_tts.lock` remains active and no audiobook or release-gate behavior is changed.

## Creative Direction

The implemented direction is `Editorial Proofreader`.

- Existing Earnalism icon asset remains the fixed left anchor.
- Base deterministic text remains `Earnalism`.
- A small caret appears before the E.
- A restrained handwritten `L` is inserted above the caret so the perceived read is `LEarnalism`.
- The tagline remains secondary: `Where Learning Becomes Earning`.
- The header lockup remains rectangular and compact.
- The public header uses the safer India-inspired tricolor literary badge by default.

## Canva Concept Notes

Canva generation was not used for final production because the connector did not have a safe way to preserve the exact local Earnalism icon as an immutable asset without redrawing it. These are source-ready concept directions for Canva review only:

1. `Editorial Proofreader`: refined serif wordmark, small correction caret, bold but restrained handwritten L, tricolor literary badge in the top-right.
2. `Literary Margin Note`: base wordmark framed like an annotated manuscript line, handwritten L reads like an editor note, quieter badge.
3. `Premium Scholar Badge`: more formal rectangular plaque, gold/espresso rules, proofreader L as a seal-like correction, badge kept separate.

Final website text is deterministic React/HTML/SVG, not Canva raster text.

## Variants Implemented

- `exact-flag`: compliance-review-only exact flag badge, vector 3:2 ratio, no inscription, no distortion.
- `tricolor`: safer India-inspired literary badge used in the public header by default.
- `none`: no badge fallback.

## Source Changes

- `frontend/src/components/BrandHeaderLogo.jsx`
- `frontend/src/components/BrandHeaderLogo.test.js`
- `frontend/src/components/Header.jsx`
- `frontend/src/index.css`
- `frontend/scripts/visual-luxury-smoke.mjs`

## Screenshot Evidence

- Screenshot directory: `/tmp/earnalism-ux-review/BRAND_HEADER_LOGO/`
- Contact sheet: `/tmp/earnalism-ux-review/BRAND_HEADER_LOGO/BRAND_HEADER_LOGO_contact_sheet.png`
- Header close crops included: Home desktop, Library desktop, Book Detail desktop, Home mobile, Library mobile, Book Detail mobile.
- Full context screenshots included: Home desktop, Library desktop, Book Detail desktop, Home mobile, Library mobile, Book Detail mobile.
- Reader route note: `/reader/:slug` is a standalone full-screen route in `frontend/src/App.js` and does not render the public header.

## Validation

- Focused brand header test: PASS
- `npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund`: PASS
- `npm test --prefix frontend -- --watchAll=false`: PASS, 8 suites / 42 tests
- `REACT_APP_BACKEND_URL=/api npm run build --prefix frontend`: PASS
- `node frontend/scripts/audit-book-covers.mjs`: PASS, 0 typographic-only customer covers
- `EARNALISM_VISUAL_PHASE=BRAND_HEADER_LOGO node frontend/scripts/visual-luxury-smoke.mjs`: PASS, 27/27 route-viewport checks, 0 blockers
- `python3 internal/earnalism_intelligence/ux_governor/run_ux_governor_check.py`: PASS
- `git diff --check`: PASS
- Missing npm aliases documented: `audit-book-covers`, `visual-smoke`

## Compliance Notes

The public header defaults to the safer tricolor literary badge. The exact Indian flag badge exists only as a component variant for owner/compliance review and is not used in the default header. It contains no text, is not distorted, and uses a 3:2 SVG ratio.

## Owner Checklist

- Existing icon unchanged: PASS
- Rectangular lockup: PASS in visual smoke, owner taste review pending
- LEarnalism reads clearly: PASS in deterministic label/source, owner visual review pending
- Proofreading missed-L idea is understandable: PASS in component/source, owner visual review pending
- Handwritten L is tasteful, not childish: owner visual review pending
- Tagline is secondary: PASS on desktop; intentionally hidden on small mobile to protect header width
- Flag/tricolor badge is small and separate: PASS; public default is safer tricolor
- Mobile header does not overflow: PASS
- Text is deterministic and accessible: PASS
- No audio/release-gate behavior changed: PASS

## Recommendation

`BRAND_HEADER_LOGO_READY_FOR_OWNER_REVIEW`.

Owner decision options:

1. `APPROVE_BRAND_HEADER_LOGO_TRICOLOR_VARIANT`
2. `REQUEST_BRAND_HEADER_LOGO_CHANGES`
3. `HOLD_BRAND_HEADER_LOGO_EXPERIMENT`

The exact Indian flag variant should remain compliance-review-only unless legal/owner approval explicitly allows it.
