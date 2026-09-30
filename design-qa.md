# Homepage Option B beige refinement — design QA

## Result

No actionable P0, P1, or P2 visual findings remain. The final comparison is against the original beige Option B mock and a fresh `origin/main` baseline after PR #471. The beige refinement is isolated to the homepage presentation and its Listening Room surface styling.

- Branch: `codex/homepage-option-b-beige-refinement`
- Base: `57237eb76c24022f02214ce08fd02b7869fe4114` (PR #471 merged)
- Exact screenshot source head: recorded in `uat/evidence/homepage-beige-refinement/owner-review-exact-head/owner-review-manifest.json`.
- PR #471 fixes preserved: yes; its Home, header, newsletter, library, and behavior files are unchanged by this branch.

## Comparison target and evidence

- Source of visual truth: `/Users/ronikbasak/Documents/ChatGPT Image Sep 28, 2026, 09_31_05 AM.png`, original size 941 × 1672 px. The same source is included in `uat/evidence/homepage-beige-refinement/owner-review-exact-head/reference-option-b-beige.png`.
- Fresh BEFORE implementation: `uat/evidence/homepage-beige-refinement/before-main/`, built from `origin/main` at `57237eb76c24022f02214ce08fd02b7869fe4114`.
- Exact-head AFTER implementation: `uat/evidence/homepage-beige-refinement/after-main-live/`.
- Browser: Playwright Chromium; unauthenticated homepage; device scale factor 1; reduced motion enabled. Desktop CSS viewports are 1440 × 1000, 1024 × 1000, and 768 × 1000. Mobile CSS viewports are 390 × 844 and 360 × 844.
- Final full-page AFTER pixels with verified live Reading Pass offers: 1440 × 3223, 1024 × 3584, 768 × 3867, 390 × 6155, and 360 × 6124. Viewport screenshots retain the CSS viewport pixel sizes above.
- Full-view comparison: `uat/evidence/homepage-beige-refinement/before-reference-after-1024-main-live-contact-sheet.png` puts the fresh base, original mock, and exact-head render together. The mock is a single desktop image, not five responsive source frames; it is shown at its original aspect ratio rather than implying mobile mockups exist.
- Five-width overview: `uat/evidence/homepage-beige-refinement/responsive-after-main-live-contact-sheet.png`.
- Focused region evidence: `after-main-live/home-1024-newsletter-focus.png` and `after-main-live/home-390-newsletter-focus.png`, with computed-state details in `after-main-live/focus-and-surfaces.json`. Both show the focused field on the correct warm panel, warm border, and visible 3 px focus ring.
- Capture health and image state: `uat/evidence/homepage-beige-refinement/capture-report-main-live.json`.

## Findings

- **No actionable visual findings.** Full-page and viewport captures show the same approved Option B section order, imagery, header/logo, links, and content as the fresh base, with the intended warm surface and elevation changes.
- **Palette and surfaces:** Homepage tokens are `--home-surface-page: #F3E7D1`, `--home-surface-section: #F5EBDD`, `--home-surface-panel: #FAF4E8`, `--home-surface-raised: #EADCC4`, `--home-text-primary: #2A1B17`, `--home-text-muted: #72645B`, and `--home-border-subtle: #D9C6A9`. Burgundy and gold continue to use existing Earnalism brand tokens. Muted text is slightly darker than the requested `#75675E` to maintain measured contrast (4.65:1 or better on the light surfaces). No normal homepage canvas/card/form rule uses sterile white.
- **Header and image fidelity:** The latest canonical header/logo remains in place. Its measured heights are 92 px at 1440, 84 px at 1024/768, and 72 px at 390/360. Existing hero, discovery, quote, newsletter, and Listening Room artwork is reused unchanged.
- **Spacing and layout:** No major section was moved. Discovery cards have warm borders, panel backgrounds, inset text, and restrained warm elevation. Reading Feel and Listening Room remain visually distinct through cream and sand backgrounds.
- **Accessibility and responsive behavior:** All five browser widths have `scrollWidth == viewport width`; captures show no clipped or broken images. Newsletter focus at 1024 and 390 uses `#FAF4E8`, a gold border, and a 3 px visible gold ring. Contrast/responsive checks passed the homepage CTA at 320/360/390/430/768/1024 (12.45:1) and the pricing heading at all six widths (13.67:1). Existing focus-visible behavior and reduced-motion preference are retained.
- **Copy and runtime truth:** No copy, route, CTA destination, or runtime flag changed. `PUBLIC_AUDIO_EXPOSURE_ENABLED=false` remains in control; the homepage Listening Room has no unapproved Listen control and retains “Audiobooks, thoughtfully arriving”. A read-only production check on 2026-09-30 confirmed `GET https://theearnalism.com/api/payments/offers` returns 200 with `configured: true`, `mode: live`, and four offers; the homepage displays those four live plans and `/pricing` renders four enabled pass buttons. No purchase control was clicked and no payment was attempted. Production purchase completion was not tested.
- **Static preview API limitation:** During the unmocked local audit, `/` sent `GET http://127.0.0.1:3015/api/payments/offers` (404; `Home.jsx:46`), then `GET http://127.0.0.1:3015/api/payments/packs` (404; fallback at `Home.jsx:50`). `/pricing` sent `GET .../api/payments/offers` (404; `Pricing.jsx:87`), then parallel `GET .../api/payments/packs` and `GET .../api/payments/config` (404; fallback at `Pricing.jsx:91`). CDP identified a script initiator in `/static/js/main.71f95993.js` (`1:409135`, Axios `xhr` at `1:407056`, caller `yt` at `1:420017`). `scripts/serve_frontend_build.js:16-17, 27-29, 50-52` serves only compiled static routes and returns 404 for `/api/*`. The source flag is `PUBLIC_PAID_COMMERCE_ENABLED=true`, so these are intentional offer-loading requests, not disabled-payment behavior. This is `EXPECTED_TEST_ENVIRONMENT_LIMITATION`.
- **Fail-closed purchase UI:** On the local 404 state, the homepage shows only links to `/pricing`; the pricing page shows “We couldn’t load Reading Passes just now” with Retry and has zero offer cards or purchase buttons. Production relevance was checked read-only on 2026-09-30: the home and pricing views each requested `GET https://theearnalism.com/api/payments/offers` (200; production bundle initiator `/static/js/main.41e459e6.js`, CDP script frame `1:409995`, Axios `xhr` at `1:407916`, caller `yt` at `1:420877`). A direct GET returned `configured: true`, `mode: live`, and four live offers. Production shows four homepage plans and four enabled pricing buttons. No purchase button was clicked, and no checkout or payment was initiated. The owner screenshots replay this same-day verified offer response, omit the public key, and make no checkout call.

## Screenshot correction history

1. **Reading/listening separation:** The initial implementation rendered Reading Feel and Listening Room with the same cream tone. Changed the Listening Room to the sand token `#EADCC4`; it now reads as a separate band.
2. **Newsletter focus surface:** The first focused screenshot showed a white-mixed input wrapper and a heavy inherited shadow. Changed it to the warm panel token, aligned border/focus colors to the warm palette, and replaced the shadow with the restrained warm shadow. Focus screenshots at 390 and 1024 confirm the visible state after the fix.
3. **Post-rebase exact-head review:** After replaying the beige commit on the PR #471 merge commit, compared the new base, reference mock, and exact-head implementation. The canonical 92/84/72 px header and search styling are preserved. No new P0/P1/P2 difference appeared, so no further screenshot-driven correction was necessary.

## Verification

- `npm ci --prefix frontend --legacy-peer-deps` — completed before this continuation; frontend dependencies available.
- Focused frontend tests — **10 suites passed, 55 tests passed**: Home, newsletter, header navigation/rendering, Listening Room, Reading Pass, homepage audio gate, audio release safety, static audio route safety, and service-worker audio safety.
- `npm run build --prefix frontend` — compiled successfully. Static SEO verifier inspected 34/34 snapshots; 703 assertions passed.
- `git diff --check origin/main..HEAD` — passed.
- Exact-head screenshot matrix: 5/5 widths captured with the verified live offer response replayed locally; all pages returned 200; no horizontal overflow, broken/incomplete images, console errors, page exceptions, or other failed responses. All five widths displayed four offers; `/pricing` displayed four offer cards and four enabled plan buttons. No purchase control was clicked.
- Contrast/responsive gate: homepage CTA and pricing heading passed all 12 measurements; 0 contrast/clipping/overflow failures. The broader script also reports 24 missing Reader and wallet-explainer elements outside this homepage scope in this static preview; disabled generated audio is correctly reported N/A at all six widths.
- `frontend/scripts/visual-luxury-smoke.mjs` HOME run — browser matrix completed 9/9 with zero browser blockers. The script's source phase reports six stale logo/header assertions (legacy `BrandHeaderLogo`/tricolor tokens) that do not match the canonical header present on `origin/main`; no runtime/header changes were made to work around those assertions.
- `npm run regression` — 8 suites passed, 2 skipped, 6 failed (112 passed, 11 failed, 4 skipped). Homepage-related static UX conversion and rendering/visual modules passed. The failures are dependent on the unavailable local backend (`/books`, `/home/books`, chapter APIs returned non-list error data), affecting migration, navigation, book integrity, MongoDB performance, legal data, and Redis cache suites; no backend/API behavior was changed.

## Owner review

- Production-surface authority: the old workflow fingerprint `211b1ce39a61ace6fe92d3a6162cd85b5e5009b6ac819f94b8e89cce966ce3c9` exactly matched PR #471 merged `origin/main`. This branch changes homepage CSS, so the derived current source fingerprint is `ce26abb38ce5d4a835c589c0b784ceaf91f4647373f4517bc7c96814b2bdffc7`; both workflow hash authorities were rebound to that computed value. The 46-case publication-workflow contract passes with its authority comparison intact; no semantic, browser, publication, merge, or deployment gates were weakened.

Exact-head owner package: `uat/evidence/homepage-beige-refinement/owner-review-exact-head/` and `uat/evidence/homepage-beige-owner-review-exact-head.zip`. The manifest records the exact reviewed branch head and base `57237eb76c24022f02214ce08fd02b7869fe4114`, five full-page/five viewport captures, the source mock, both comparison sheets, focus-state evidence, the payment API audit, and the production offers fixture. The final screenshots were refreshed from the branch after PR #471 was merged; `capture-report-main-live.json` records the screenshot head and all five widths. The local payment route is marked `EXPECTED_TEST_ENVIRONMENT_LIMITATION`.

Status: `READY_FOR_OWNER_VISUAL_APPROVAL`. Owner visual approval is **WAITING** for this exact head. The change has not been merged or deployed.

## Open implementation checklist

- [x] Homepage-only semantic parchment tokens and warm surfaces.
- [x] Preserve current Option B composition, header/logo, links/routes, and copy.
- [x] Preserve PR #471 functionality and reconcile onto its merge commit.
- [x] Capture fresh before/reference/after evidence and all five responsive widths.
- [x] Complete screenshot-driven correction passes and review the exact rebased head.
- [x] Verify production Reading Pass offers and prepare captures using that current product state without initiating checkout.
- [x] Prepare an exact-head owner visual review package.
- [ ] Record owner visual approval for the exact head recorded in `owner-review-manifest.json`.
- [ ] Merge only after approval and required checks; no merge or deployment performed.

final result: passed
