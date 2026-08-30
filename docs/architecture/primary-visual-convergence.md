# Primary visual convergence record

## Controlled-measurement reconciliation - 2026-08-29

The original live-production score (`49.340302`) is retained as historical evidence, but its live catalogue fixture differs from the controlled fixture and is therefore not a numeric non-regression threshold. A fresh three-way measurement used `fb77f75b`, Commerce checkpoint `f89cd71e`, and current head `189231301`, with the same catalog/offer/release fixture, references, crops, zero-mask contract, Playwright 1.60.0, Chromium 148.0.7778.96, Pixelmatch 7.2.0 at threshold 0.2, 1x scale, `en-IN`, and `Asia/Kolkata`.

- Controlled base/current aggregate: `48.858998` to `62.151249`; 392,744 fewer mismatched pixels across 2,954,684 comparable pixels.
- Commerce controlled base/checkpoint/current: `40.642512` / `62.477180` / `62.477180`; the current state therefore passes the controlled Commerce non-regression gate exactly, with zero mask coverage.
- Structural contract: 347/347 assertions passed. The per-state assertion distribution is retained in `uat/evidence/primary-visual-convergence/controlled-reconciliation.json`.
- Truth-safe content and product truth: `100.000000`. Reader and Listener remain excluded for their product-state reasons and are not aggregated.

The remaining literal differences are classified in [primary-visual-owner-asset-gaps.md](primary-visual-owner-asset-gaps.md). The correct owner decision is either truth-safe structural acceptance or supplying the listed production assets and licensed fonts for a separate ditto-visual continuation; neither path permits fabricated claims or composite reference images in production.

## Immutable baseline

- Baseline artifact: `/tmp/earnalism-live-mock-score-20260828T070033Z/`
- Measured production frontend: `e8eb187e81c33d36f846765195b51011293e69a0`
- Baseline aggregate: `49.340302`
- Baseline commerce-desktop: `40.841180` (`969,561` mismatched comparable pixels)
- Comparator: Playwright `1.60.0`, Chromium `148.0.7778.96`, pixelmatch `7.2.0`, threshold `0.2`

## Commerce desktop convergence

The production Commerce route now implements the dedicated Reading Pass composition: a dark conversion column, warm editorial rail, compact hero proof panel, four configured-pass cards, support pathways, a trust band, and a final conversion panel. It uses the current public offer response rather than mock prices or an invented recommended product.

The local deterministic comparison, using the pinned Chromium executable and the live public offer fixture, reduced the commerce mismatch from `969,561` to `585,966` comparable pixels (`40.841180` to `64.246647`). No visual masks were used.

### Commerce structural contract

The literal pixel score remains `64.246647`; it is not a 95% pixel pass. A
pinned Chromium DOM-geometry contract against the dedicated Commerce reference
role passed `14/14` assertions (`100.000000` structural conformance). It
measures the 63/37 desktop split, compact hero/proof hierarchy, aligned
four-card configured-offer row, pathway/trust rows, warm information rail,
canonical logo, and overflow. The truthful-content contract is also
`100.000000`: configured offers are rendered, unsupported mock claims are
absent, and the locked text/audio policy is retained.

## Documented reference limitation

The dedicated `Reading Pass.png` reference is a conceptual, `REGION_REFERENCE` board. Its most visually dominant regions contain a non-bundled chair-and-lamp hero photograph plus illustrative research statistics, reader counts, satisfaction ratings, testimonials, and fixed offer claims. Those elements cannot be reproduced by the production route: the product contract forbids fabricated statistics, testimonials, popularity, ratings, and unsupported prices, and no separately approved source asset exists for the reference hero photograph.

The implementation preserves that geometry with verified Reading Pass facts and the existing approved library artwork. Because structural visual masking is prohibited and dynamic masking may not cover backgrounds, cards, or typography blocks, this state cannot truthfully meet the `95.000000` pixel score until the owner supplies equivalent approved production assets and verified replacement content for those mock-only regions.

This is a limitation of the immutable conceptual reference, not a change to its crop, hash, threshold, mask policy, or authority.

## Home desktop convergence

The Home surface now consumes the already-present curated, release-safe Home
snapshot when the catalogue call is unavailable. This keeps the five-card
journey shelf visible without opening an unsafe reader or listener action. The
fresh local pixel result is `44.509396` against the immutable selected region
(`56.143587` production baseline); it is reported literally and is not treated
as a pass. The difference is dominated by the unbundled library-room hero art
and by the reference panel's full vertical crop, which is taller than the
normalized live viewport. Structural conformance is `100.000000` (10/10),
truth-safe content conformance is `100.000000`, and masks remain `0%`.

## Remaining mobile reference measurements

The existing owner-approved mobile Home, Library, Commerce, navigation, and
About shells retain their visual structure after the shared convergence work.
Fresh pinned-browser raw measurements are: Home `63.375131`, Library
`63.268872`, Commerce `78.113275`, mobile navigation `79.475281`, and About
`80.221958`. Their structural contracts passed (Home 5/5, Library 5/5,
Commerce 5/5, navigation 5/5, About 3/3), each yields
`100.000000` structural conformance, and each preserves a
`100.000000` truth-safe content result with 0% masking. The Home and Commerce
hero imagery, live cover artwork, and reference-region normalization remain
literal raw-score limitations; no illustrative claim or structural masking was
introduced to conceal them.

## Library filter mobile convergence

The mobile filter interaction is now a full-height dark reference panel with
the title/reset row, close action, Language, Format, Status, and route-driven
Genre groups, a sort field, internal scrolling, 44px-capable controls, and an
Apply filters action. It moved from the light bottom sheet to the reference
panel role without altering catalogue APIs or audio release truth. Its literal
raw score improved from `17.596125` to `76.968264`; the remaining literal
difference is the required Genre/sort content and the reference's smaller
illustrative panel crop. Structural conformance is `100.000000` (7/7),
truth-safe content conformance is `100.000000`, and masks remain `0%`.

## Library desktop convergence

The safe local fallback catalogue now carries the existing controlled
reader-ready fields for the three approved fallback titles while keeping audio
explicitly disabled. A transient catalogue failure therefore retains a
truthful Live now shelf instead of rendering all fallback books as Coming
soon. The local literal score is `38.823505` against the immutable selected
region (`63.021455` production baseline); this is recorded without adjustment.
The selected board uses a much taller editorial region than the normalized
live viewport and different live covers. Structural conformance is
`100.000000` (9/9), truth-safe content conformance is `100.000000`, and masks
remain `0%`.

## Book Detail desktop convergence

The desktop Book Detail shell now starts directly in the dark book room, using
the persistent Library navigation rather than a second desktop return row. The
compact vertical composition preserves the cover, controlled release/status
panel, Read action, secondary actions, and the fail-closed absence of a Dracula
Listen action. The literal local pixel score is `56.398820` against the
`56.194477` baseline; structural conformance is `100.000000` (10/10),
truth-safe content conformance is `100.000000`, and masks remain `0%`.

## PR #341 final comparable measurement

The historical production baseline remains immutable: `49.340302` raw,
`2,954,684` comparable pixels and `1,496,834` mismatched pixels. It used the
then-live production catalogue. That catalogue cannot be used to make a valid
per-state non-regression claim after release data changes, so this final pass
also preserves a controlled, release-safe source baseline at
`fb77f75b3799a5cb5257429f812d17ca781bde2d`. Both baseline and current sources
were rendered with the exact same fixture hashes, crop coordinates, pinned
browser, normalization, zero masks and two-identical-capture stability gate.
The comparison contract is checked in beside the run record.

The direct comparison reports `62.151486` raw current fidelity, `1,118,304`
mismatched pixels, and a reduction of `392,764` pixels from the controlled
baseline. The historical aggregate is retained for audit, not overwritten.
Home desktop is `55.137587 → 55.140810`; Library desktop is
`61.922335 → 62.434810`; Commerce desktop is `40.642512 → 62.477180`; Book
Detail is unchanged at `56.091167`; and the Library filter is
`17.683857 → 80.546231`. The small Commerce-mobile difference of `-0.096034`
is within the permitted `0.100000` stable-rasterization tolerance.

The structural contract was expanded from coarse presence checks to 347
region-level assertions covering component order, boxes, content widths,
grid/card geometry, type, colour, borders, radii, actions, clipping and
overflow. Every state passed: `347/347` (`100.000000`). This does not relabel
the literal raw score as a 95% pixel pass. Truth-safe content and product
truth remain `100.000000`; masks remain `0%`.
