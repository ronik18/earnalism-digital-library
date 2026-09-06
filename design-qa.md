# Quiet Heritage design QA

**Final result: blocked**

## Comparison evidence

- Source visual truth: owner-supplied `editorial-house.png` reference board (1672 × 941); it is a three-page art-direction board, not an in-product background.
- Rendered implementation: local production-build captures of `/`, `/library`, and `/pricing` after the Quiet Heritage foundation change. The available browser capture was a narrow responsive viewport; no comparable desktop browser viewport was available in this pass.
- State: public, signed-out, release-safe catalogue data. The local pricing API had no configured offers, so its honest no-offer state was rendered rather than mock prices.
- Full-view comparison: Home and Pricing use a maroon literary hero with real still-life/library art; Library uses the required light-beige editorial surface, compact masthead, search, and cover-led grid.
- Focused region comparison: Home hero typography/art and Library masthead/search were inspected. The source board's baked controls, placeholder titles, and prices were intentionally not reproduced.

## Findings

- [P2] Comparable desktop and wide-tablet QA remains unverified.
  Location: `/`, `/library`, `/pricing` responsive compositions.
  Evidence: the board is desktop-oriented, while this pass captured the live production build only at a narrow browser surface.
  Impact: card density, hero crop, offer ledger alignment, and long Bengali wrapping have not had direct visual acceptance at the specified desktop widths.
  Fix: capture the same public states at 1280 × 800 and 1440 × 900, then repeat this comparison before merge.

- [P2] Dynamic offer-ledger state remains unverified locally.
  Location: `/pricing`.
  Evidence: the local API returned no offers, leaving the deliberate no-offer state; the reference board's offer rows are illustrative only.
  Impact: dynamic pack labels, prices, and disabled/busy purchase states need a permitted non-production fixture or deployed read-only observation.
  Fix: run the existing pricing fixture or authorized read-only environment check without initiating checkout.

## Required fidelity surfaces

- Typography: locally served EB Garamond 400 and genuine italic 400 are now used only by the scoped Quiet Heritage layer; Outfit and Noto Bengali remain UI/fallback faces.
- Spacing/layout: Home retains asymmetric copy/art; Library has a paper catalog and small-radius cards; narrow layout stacks controls without duplicating controls.
- Colors/tokens: scoped Burgundy `#651D32`, Maroon `#461322`, Beige `#EEE1C9`, Light beige `#F6EDDC`, Gold `#BE9854`, and Ink `#2A171B` map to the approved direction.
- Image quality: Home uses the supplied 1672 × 941 still-life only as a bounded crop; board-derived image crops were removed from product heroes.
- Copy/content: dynamic title, offer, entitlement, and audio-safe copy remains sourced from existing contracts. Account no longer invents a Dracula continuation.

## Comparison history

1. Initial narrow Library capture had dark inherited variables and inadequate title contrast. The scoped stylesheet import was moved after the reference surface CSS and its Library variables were made explicit.
2. Revised narrow Library capture showed the required light surface, readable ink title, search, and release-safe live cards.

## Implementation checklist

1. Run wide desktop/tablet visual capture and 200%/400% zoom checks.
2. Exercise the dynamic Reading Pass fixture or authorized read-only offer state.
3. Complete the remaining route-family and reader/listener state QA before release review.
