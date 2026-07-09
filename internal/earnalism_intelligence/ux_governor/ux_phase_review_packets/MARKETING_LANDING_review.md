# MARKETING_LANDING Review

Generated: 2026-07-08T12:45:05Z

## Objective

Make the public marketing surfaces feel premium, calm, literary, and conversion-clear while preserving release-gate truth. This phase does not approve launch, preview/deploy, paid Listen campaigns, paid TTS, release-gate mutation, or FINAL_INTEGRATION.

## Source Changes

- `frontend/src/hooks/useSEO.js`
- `frontend/src/pages/About.jsx`
- `frontend/src/pages/Pricing.jsx`
- `frontend/src/pages/Journal.jsx`
- `frontend/src/lib/controlledLaunch.js`
- `frontend/src/components/ShelfTwoSlideshow.jsx`
- `frontend/src/lib/marketingLandingTruth.test.js`
- `frontend/scripts/visual-luxury-smoke.mjs`

## Visible Changes

- Focused contact-truth correction: public contact, footer, social mailto, pricing copy, tests, smoke checks, and SEO evidence now use owner-confirmed `sales@reoenterprise.org`.
- Default SEO now positions Earnalism as a Bengali and English digital library, not a Dracula-first room.
- About page now frames Earnalism as a bilingual literary reading room with source care, graphical editions, and evidence-gated audiobooks.
- Pricing copy remains reading-time based but no longer over-centers Dracula in explanatory copy.
- Journal SEO now references Bengali and English literature.
- Controlled-launch fallback copy no longer says an audiobook is in private review; it says audio availability is evidence-gated and hidden unless approved.
- Pricing support contact now matches Contact/Footer/social links using the owner-confirmed address: `sales@reoenterprise.org`.
- Shelf II queued cards now use `Request Update` to `/contact?interest=...` instead of a fake `Notify Me` button.

## Evidence

- DOM evidence: `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/MARKETING_LANDING_dom_evidence.json`
- SEO evidence: `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/MARKETING_LANDING_seo_evidence.json`
- Release-gate evidence: `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/MARKETING_LANDING_release_gate_evidence.json`
- Visual smoke summary: `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/MARKETING_LANDING_visual_smoke_summary.json`
- Screenshots: `/tmp/earnalism-ux-review/MARKETING_LANDING/`
- Contact sheet: `/tmp/earnalism-ux-review/MARKETING_LANDING/MARKETING_LANDING_contact_sheet.png`

## Validation

- `npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund`: PASS.
- `npm test --prefix frontend -- --watchAll=false`: PASS, 10 suites / 53 tests.
- `REACT_APP_BACKEND_URL=/api npm run build --prefix frontend`: PASS. Existing SEO generator warnings remain for missing local controlled publication JSON files; build completed.
- `node frontend/scripts/audit-book-covers.mjs`: PASS, 0 typographic-only covers.
- `EARNALISM_VISUAL_PHASE=MARKETING_LANDING node frontend/scripts/visual-luxury-smoke.mjs`: PASS, 24/24 route-viewport checks, 0 blockers.
- Contact-truth scan for the previous incorrect `.in` address and mailto variant: PASS, no public-facing matches.
- `node --check frontend/scripts/visual-luxury-smoke.mjs`: PASS.
- `python3 internal/earnalism_intelligence/ux_governor/run_ux_governor_check.py`: PASS.
- `git diff --check`: PASS.

## Visual Smoke Notes

MARKETING_LANDING phase support uses the requested four viewport sizes: `1440x900`, `1536x864`, `430x932`, and `390x844`.

The phase has local static SPA fallback and harmless marketing API mocks for `/api/payments/packs`, `/api/payments/config`, and `/api/blog` so locally routable marketing pages can be reviewed from the static build. Full/default smoke behavior is unchanged.

## Owner Checklist

- Not Dracula-first: PASS.
- Bengali and English literary positioning visible: PASS.
- Reader-first titles remain premium, not incomplete: PASS.
- Audiobook language is release-truth-safe: PASS.
- No unapproved Listen CTA: PASS.
- No AudioObject for non-approved audio: PASS.
- No static `/audio/...` path introduced: PASS.
- No word-level sync claim introduced: PASS.
- Support email/domain consistent: PASS.
- Notify Me fake functionality removed: PASS.
- Mobile marketing routes show no horizontal overflow: PASS.
- paid_tts.lock remains active: PASS.

## Approval Choices

1. `APPROVE_MARKETING_LANDING_AND_PROCEED_TO_FINAL_INTEGRATION`
2. `REQUEST_MARKETING_LANDING_CHANGES`
3. `HOLD_UX_WORK`

## Blockers

- Owner approval is required before FINAL_INTEGRATION.
- Full preview/production validation remains not proven.
- Paid Listen campaigns remain blocked.
- paid_tts.lock remains active and no paid audio work is authorized.
