# Quiet Heritage design QA

**Final result: blocked — foundation batch is visually validated; full site redesign remains incomplete.**

## Comparison evidence

- Source visual truth: owner-supplied `editorial-house.png` reference board (1672 × 941); it is a three-page art-direction board, not an in-product background.
- Rendered implementation: exact-head Chromium local production-build capture for `/book/dracula`, `/book/devdas`, and `/pricing`, with deterministic contract-shaped fixtures. The captured head was `b38b8aed2b1fb6008cc1703d7e71f33ff8d42674`, tree `a3780298c1252c100bcce612454a65a4f6fdd30a`.
- Responsive evidence: `/pricing` was captured at 1440 × 1000, 1280 × 800, 1024 × 768, 768 × 1024, 430 × 932, 390 × 844, and 320 × 568. Book-detail about and chapter states were captured at desktop, tablet, and mobile widths. All captures were stable and reported no horizontal overflow.
- Dynamic-offer fixture: `{ packs, config }` with four server-contract-shaped offers. At 1440 and 1280, the ledger has four equal cards and aligned 44px CTAs; narrower captures reflow without a duplicate purchase control. This is fixture evidence only, not live offer or payment availability.
- Typography: Cormorant, Outfit, Noto Serif Bengali, and Noto Sans Bengali each loaded at every captured state. EB Garamond regular and italic assets were requested by the scoped Quiet Heritage layer; the restored global `--font-display` preserves the header/shared display family.
- Full-view comparison: Pricing uses a maroon literary hero with real library art and a light-beige dynamic ledger. The source board's baked controls, placeholder titles, and prices were intentionally not reproduced.

## Findings

- [P1] The full route-family visual matrix remains incomplete.
  Location: Home, Library, reader/listener, authentication, account/My Library, editorial support pages, policies, and shared recovery states.
  Evidence: this exact-head capture covers Book Detail and Reading Passes only; the earlier Home/Library inspection was narrow and pre-dates the corrected full browser evidence pass.
  Impact: PR #360 is a foundation batch, not a complete Quiet Heritage release.
  Fix: continue sequential page-family PRs with comparable desktop/mobile screenshot and interaction evidence.

- [P2] Dynamic empty/error/browser retry states are unit-verified but not yet included in the exact-head browser capture.
  Location: `/pricing`.
  Evidence: `Pricing.test.jsx` verifies loading, empty, and error state bindings. The preceding browser capture predates this narrowly added recovery-state commit.
  Impact: no claim is made that the new recovery copy has cross-browser visual evidence.
  Fix: after the owner-authorized integrity-hash update, rebuild and capture the exact new head with delayed/empty/failing fixture responses.

## Required fidelity surfaces

- Typography: locally served EB Garamond 400 and genuine italic 400 are now used only by the scoped Quiet Heritage layer; Outfit and Noto Bengali remain UI/fallback faces.
- Spacing/layout: Home retains asymmetric copy/art; Library has a paper catalog and small-radius cards; narrow layout stacks controls without duplicating controls.
- Colors/tokens: scoped Burgundy `#651D32`, Maroon `#461322`, Beige `#EEE1C9`, Light beige `#F6EDDC`, Gold `#BE9854`, and Ink `#2A171B` map to the approved direction.
- Image quality: Home uses the supplied 1672 × 941 still-life only as a bounded crop; board-derived image crops were removed from product heroes.
- Copy/content: dynamic title, offer, entitlement, and audio-safe copy remains sourced from existing contracts. Account no longer invents a Dracula continuation.

## Comparison history

1. Initial narrow Library capture had dark inherited variables and inadequate title contrast. The scoped stylesheet import was moved after the reference surface CSS and its Library variables were made explicit.
2. Revised narrow Library capture showed the required light surface, readable ink title, search, and release-safe live cards.
3. Exact-head Chromium capture verified Book Detail interactions, 27 ordered Dracula chapters, Heading copy, loaded fonts, and pricing geometry across seven widths. No screenshot, fixture, or local evidence was published from this record.

## Implementation checklist

1. Capture Home and Library at the same wide and narrow states, plus 200%/400% zoom and short-landscape checks.
2. Capture the new dynamic Reading Pass loading, empty, error, selected, and busy states after the integrity hash is permitted and bound to the candidate.
3. Complete the remaining route-family and reader/listener state QA before release review.
