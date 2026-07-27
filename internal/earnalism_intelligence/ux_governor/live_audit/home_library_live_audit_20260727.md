# Production Home and Library UX Audit — 2026-07-27

Status: repair required; source changes prepared on `feature/home-premium-repair-v5`, not deployed.

## Executive finding

The supplied screenshot marks a white rectangle over the Home hero. The live DOM does not contain that rectangle; it is part of the screenshot annotation. The actual production defect is lower on the Home page: the compact editorial collage is being rendered as four full-width rows because the production payload uses long shelf IDs (`bengali-life-and-legacy`, `gothic-and-the-uncanny`, and so on) while the V4 grid resolver expected short CSS areas (`bengali`, `gothic`, `love`, `adventure`, `short`). Adventure currently has no visible books, so the resolver falls into its one-row-per-group fallback.

The Library cover concern is also a release-truth issue rather than a network failure. Production returned zero failed image requests for the inspected cards. Devdas and Pather Panchali have no canonical front-cover URL in the production API, so the UI correctly falls back to the Earnalism graphical fallback. That fallback was visually too generic to feel like a finished editorial shelf.

## Measured production state

- Home CSS viewport: `1280x720`.
- Home horizontal overflow: none observed.
- Listening Rooms: 3 cards (`a-ghost-story`, `sredni-vashtar`, `the-open-window`).
- Visible collage areas: Bengali, Gothic, Love, Short; Adventure has no visible books.
- Before repair, the collage computed as Bengali x12, Gothic x12, Love x12, Short x12.
- Library image failures observed: zero.
- Library canonical cover metadata missing for `devdas` and `pather-panchali`.

## Repair decisions

1. Normalize explicit `layout_area` values and long editorial IDs before grid composition.
2. Preserve the approved five-shelf composition when all shelves are present.
3. When a shelf is absent, pack the remaining shelves into occupied cells. The current four-shelf production state becomes Bengali 7/12 + Gothic 5/12, then Love 6/12 + Short 6/12. No empty Adventure area or stretched one-shelf rows are emitted.
4. Keep the mobile layout one shelf per row and the tablet layout in occupied two-column rows.
5. Keep canonical cover truth unchanged. Add content-bound vector motifs to the deterministic fallback so the missing Devdas and Pather Panchali assets read as intentional editorial artwork while remaining auditable as fallbacks.
6. Do not claim a 10/10 score until the repaired bundle is deployed and browser-verified at desktop, tablet, and mobile widths.

## Required follow-up

- Obtain and approve canonical front/back art for Devdas and Pather Panchali through the cover acceptance process.
- Deploy the repair branch through the normal PR path.
- Re-run production browser smoke for Home, Library, Book Detail, Reader, and representative reader-only routes.
- Confirm the collage uses compact occupied rows and no public audio or stale asset regressions.
