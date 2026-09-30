# Homepage Option B beige refinement — design QA

## Findings

No actionable P0, P1, or P2 visual findings remain after two correction passes. The refinement keeps the existing Option B composition, route links, official logo, Reader Pass messaging, and release-aware Listening Room. At 1440, 1024, 768, 390, and 360 CSS pixels, the page has no horizontal overflow; all captured images completed successfully and no image was broken.

## Comparison target and evidence

- Source visual: `/Users/ronikbasak/Documents/ChatGPT Image Sep 28, 2026, 09_31_05 AM.png` (copied to `/Users/ronikbasak/.codex/worktrees/optionb-release-review/earnalism-digital-library/uat/evidence/homepage-beige-refinement/reference/option-b-beige-source.png`). Source pixels: 941 × 1672. The mock is a single full-page desktop composition with no separate responsive files or declared CSS viewport/density.
- Baseline: clean branch before edits, screenshots at `/Users/ronikbasak/.codex/worktrees/optionb-release-review/earnalism-digital-library/uat/evidence/homepage-beige-refinement/before/`.
- Final implementation: `/Users/ronikbasak/.codex/worktrees/optionb-release-review/earnalism-digital-library/uat/evidence/homepage-beige-refinement/after/`.
- Browser: Chromium production build served locally at `http://127.0.0.1:3015/`; default unauthenticated state; `deviceScaleFactor=1`. Desktop CSS viewports were 1440 × 1000, 1024 × 1000, and 768 × 1000; mobile CSS viewports were 390 × 844 and 360 × 844. Full-page implementation pixels are 1440 × 3213, 1024 × 3574, 768 × 3856, 390 × 5983, and 360 × 5953.
- Full-view comparison: `/Users/ronikbasak/.codex/worktrees/optionb-release-review/earnalism-digital-library/uat/evidence/homepage-beige-refinement/before-reference-after-1024-contact-sheet.png` compares the 1024 baseline, original 941 px mock, and final 1024 render. Images were proportionally reduced only for contact-sheet display; no pixel-difference score was used.
- Responsive overview: `/Users/ronikbasak/.codex/worktrees/optionb-release-review/earnalism-digital-library/uat/evidence/homepage-beige-refinement/responsive-after-contact-sheet.png`.
- Focused evidence: full-page captures at each required width show the hero blend, cards, reading-feel section, Listening Room, Pass block, quote strip, newsletter, and footer. Viewport captures `home-390-viewport.png` and `home-360-viewport.png` show the mobile header, hero, and transition into discovery. Newsletter focus was also inspected in Chromium at 390 and 1024.

The source is a desktop mock rather than a responsive browser capture. It was compared for palette, surface rhythm, hero composition, card framing, burgundy/cream balance, quote/newsletter/footer transitions, and typography hierarchy. Its mock copy and unavailable product claims were not copied. The live implementation has an existing release-aware Listening Room, so that additional section remains present as requested.

## Fidelity review

The pre-change page canvas computed to `#FFF9EE`, with white-mixed quote and newsletter surfaces. The final page, header, hero, and discovery canvas compute to `#F3E7D1`; discovery cards and newsletter controls use `#FAF4E8`; no homepage surface computes to pure white.

- **Typography:** Existing bundled Cormorant Garamond display and Outfit UI fonts remain unchanged. Heading hierarchy, body sizes, and copy remain the approved Option B implementation.
- **Spacing and layout:** Major sections, order, links, and responsive breakpoints remain unchanged. Discovery cards gained a warm border and inner whitespace. The listening surface now has a distinct sand tone to keep it separate from the reading-feel band.
- **Colors and tokens:** Homepage-scoped semantic tokens are `--home-surface-page: #F3E7D1`, `--home-surface-section: #F5EBDD`, `--home-surface-panel: #FAF4E8`, `--home-surface-raised: #EADCC4`, `--home-text-primary: #2A1B17`, `--home-text-muted: #72645B`, and `--home-border-subtle: #D9C6A9`. Burgundy and gold map to existing Earnalism tokens. The muted text value is slightly darker than the requested `#75675E`: calculated contrast is 4.65:1 against page parchment, 4.83:1 against section cream, and 5.20:1 against raised cream. The focus gold (`--gold-700`) has 5.06:1 or better against these surfaces. The Reading Pass remains the strongest burgundy anchor and the footer remains burgundy.
- **Imagery:** Existing header logo, hero, discovery, Listening Room, portraits, quote, and newsletter artwork are unchanged. After scrolling through lazy content, every image completed with a non-zero natural width at all five viewports.
- **Copy and product truth:** No copy, route, or runtime control changed. `PUBLIC_AUDIO_EXPOSURE_ENABLED=false` still suppresses title-specific Listen controls. The local payment API returns 404 because this static preview has no backend; no numeric offer prices appear in the captured homepage, and the existing Pass messaging says purchases are not available yet. Live payment/catalogue endpoints were not verified from this local preview.
- **Inputs and focus:** Search and newsletter fields use warm cream/panel surfaces and warm borders. The newsletter wrapper focuses to the existing dark-gold token with a 3 px warm ring; submit shadow is `rgba(74, 49, 35, 0.08)`. The primary homepage CTA passed the repository contrast/responsive check at all six tested widths (320, 360, 390, 430, 768, 1024), with 12.45:1 measured contrast at 320 px. Captured home layouts have no overflow.

## Screenshot correction history

1. **Pass 1:** Initial render showed the Reading Feel and Listening Room sections sharing the same `#F5EBDD` background, so they read as a single band. Changed the Listening Room to the approved sand token `#EADCC4`. Final screenshots at all five widths show the separate tonal layer.
2. **Pass 2:** A closer newsletter review found the inherited field wrapper still mixed in white, and its submit button retained a black-heavy shadow. Set the wrapper to `#FAF4E8`, aligned its border/focus treatment to warm tokens, and replaced the submit shadow with the restrained warm shadow. Rebuilt and recaptured every required width. Focus inspection at 390 and 1024 confirmed the panel background, gold border, visible 3 px ring, and no overflow.

## Verification

- `npm ci --prefix frontend --legacy-peer-deps` — completed.
- Focused frontend suite — 11 suites passed, 62 tests passed: Home, public pages, header render/navigation, Listening Room, Reading Pass, homepage audio gate, audio release truth, static audio route safety, service-worker audio safety, and static SEO contract.
- `npm run build --prefix frontend` — compiled successfully. Static SEO verifier: 34 snapshots inspected, 703 assertions, 0 failures.
- `git diff --check` — passed.
- Homepage browser captures at 1440, 1024, 768, 390, and 360 — passed; no horizontal overflow, broken images, or incomplete images.
- `scripts/run_contrast_responsive_gate.mjs` — homepage CTA and pricing heading checks passed (12); 0 contrast/overflow failures. The overall script exits non-zero because it also reported 24 missing Reader and wallet-explainer elements on this local static preview, so those unrelated routes remain unverified here.
- Local browser console showed only `/api/payments/offers` and `/api/payments/packs` 404s from the static preview lacking an API server. No page exceptions or broken image requests were observed.

## Open implementation checklist

- [x] Warm parchment canvas and semantic homepage tokens.
- [x] Warm raised discovery cards and framed imagery.
- [x] Distinct Reading Feel and Listening Room tones.
- [x] Burgundy Reading Pass contrast and current availability copy preserved.
- [x] Newsletter fields, focus, and footer transition reviewed.
- [x] Five required viewport screenshots captured before and after; source mock retained.
- [x] At least one screenshot-driven correction pass completed.

final result: passed
