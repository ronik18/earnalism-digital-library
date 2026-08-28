# Primary visual convergence record

## Immutable baseline

- Baseline artifact: `/tmp/earnalism-live-mock-score-20260828T070033Z/`
- Measured production frontend: `e8eb187e81c33d36f846765195b51011293e69a0`
- Baseline aggregate: `49.340302`
- Baseline commerce-desktop: `40.841180` (`969,561` mismatched comparable pixels)
- Comparator: Playwright `1.60.0`, Chromium `148.0.7778.96`, pixelmatch `7.2.0`, threshold `0.2`

## Commerce desktop convergence

The production Commerce route now implements the dedicated Reading Pass composition: a dark conversion column, warm editorial rail, compact hero proof panel, four configured-pass cards, support pathways, a trust band, and a final conversion panel. It uses the current public offer response rather than mock prices or an invented recommended product.

The local deterministic comparison, using the pinned Chromium executable and the live public offer fixture, reduced the commerce mismatch from `969,561` to `585,966` comparable pixels (`40.841180` to `64.246647`). No visual masks were used.

## Documented reference limitation

The dedicated `Reading Pass.png` reference is a conceptual, `REGION_REFERENCE` board. Its most visually dominant regions contain a non-bundled chair-and-lamp hero photograph plus illustrative research statistics, reader counts, satisfaction ratings, testimonials, and fixed offer claims. Those elements cannot be reproduced by the production route: the product contract forbids fabricated statistics, testimonials, popularity, ratings, and unsupported prices, and no separately approved source asset exists for the reference hero photograph.

The implementation preserves that geometry with verified Reading Pass facts and the existing approved library artwork. Because structural visual masking is prohibited and dynamic masking may not cover backgrounds, cards, or typography blocks, this state cannot truthfully meet the `95.000000` pixel score until the owner supplies equivalent approved production assets and verified replacement content for those mock-only regions.

This is a limitation of the immutable conceptual reference, not a change to its crop, hash, threshold, mask policy, or authority.
