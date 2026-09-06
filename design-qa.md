# Quiet Heritage design QA

**Final result: blocked — foundation batch is visually validated; full site redesign remains incomplete.**

## Comparison evidence

- Source visual truth: owner-supplied `editorial-house.png` reference board (1672 × 941); it is a three-page art-direction board, not an in-product background.
- Rendered implementation: exact-head Chromium local production-build capture for `/book/dracula`, `/book/devdas`, and `/pricing`, with deterministic contract-shaped fixtures. The captured head was `1b92b60cfef6144179ae98489e27cbd84bfeeed0`, tree `52f8931b20c78c5469cbb0c9a3ce81eedddbf732`.
- Responsive evidence: `/pricing` was captured at 1440 × 1000, 1280 × 800, 1024 × 768, 768 × 1024, 430 × 932, 390 × 844, and 320 × 568. Book-detail about and chapter states were captured at desktop, tablet, and mobile widths. All captures were stable and reported no horizontal overflow.
- Dynamic-offer fixture: `{ packs, config }` with four server-contract-shaped offers. At 1440 and 1280, the ledger has four equal cards and aligned 44px CTAs; narrower captures reflow without a duplicate purchase control. A separate 390px local-interception matrix verified loading, empty, failed/retry, selected long-name five-offer, and authenticated busy/disabled states without visible legacy purchase controls or horizontal overflow. This is fixture evidence only, not live offer or payment availability.
- Typography: Cormorant, Outfit, Noto Serif Bengali, and Noto Sans Bengali each loaded at every captured state. EB Garamond regular and italic assets were requested by the scoped Quiet Heritage layer; the restored global `--font-display` preserves the header/shared display family.
- Full-view comparison: Pricing uses a maroon literary hero with real library art and a light-beige dynamic ledger. The source board's baked controls, placeholder titles, and prices were intentionally not reproduced.

## Findings

- [P1] The full route-family visual matrix remains incomplete.
  Location: Home, Library, reader/listener, authentication, account/My Library, editorial support pages, policies, and shared recovery states.
  Evidence: this exact-head capture covers Book Detail and Reading Passes only; the earlier Home/Library inspection was narrow and pre-dates the corrected full browser evidence pass.
  Impact: PR #360 is a foundation batch, not a complete Quiet Heritage release.
  Fix: continue sequential page-family PRs with comparable desktop/mobile screenshot and interaction evidence.

- [P2] Cross-browser and enlargement coverage for the new recovery states remains incomplete.
  Location: `/pricing`.
  Evidence: the exact-head Chromium fixture matrix covers the recovery states at 390px. Firefox/WebKit and 200%/400% enlargement evidence remain pending.
  Impact: no cross-browser claim is made for the new recovery-state composition.
  Fix: include these states in the existing cross-browser matrix during a subsequent focused QA batch.

## Required fidelity surfaces

- Typography: locally served EB Garamond 400 and genuine italic 400 are now used only by the scoped Quiet Heritage layer; Outfit and Noto Bengali remain UI/fallback faces.
- Spacing/layout: Home retains asymmetric copy/art; Library has a paper catalog and small-radius cards; narrow layout stacks controls without duplicating controls.
- Colors/tokens: scoped Burgundy `#651D32`, Maroon `#461322`, Beige `#EEE1C9`, Light beige `#F6EDDC`, Gold `#BE9854`, and Ink `#2A171B` map to the approved direction.
- Image quality: Home uses the supplied 1672 × 941 still-life only as a bounded crop; board-derived image crops were removed from product heroes.
- Copy/content: dynamic title, offer, entitlement, and audio-safe copy remains sourced from existing contracts. Account no longer invents a Dracula continuation.

## Comparison history

1. Initial narrow Library capture had dark inherited variables and inadequate title contrast. The scoped stylesheet import was moved after the reference surface CSS and its Library variables were made explicit.
2. Revised narrow Library capture showed the required light surface, readable ink title, search, and release-safe live cards.
3. Exact-head Chromium capture verified Book Detail interactions, 27 ordered Dracula chapters, heading copy, loaded fonts, and pricing geometry across seven widths. A second exact-head local fixture matrix verified Pricing loading, empty, failed/retry, selected, and busy states at 390px. No screenshot, fixture, or local evidence was published from this record.

## Implementation checklist

1. Capture Home and Library at the same wide and narrow states, plus 200%/400% zoom and short-landscape checks.
2. Add Firefox/WebKit, 200%/400% zoom, and short-landscape coverage for Pricing recovery states.
3. Complete the remaining route-family and reader/listener state QA before release review.
