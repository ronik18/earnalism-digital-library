# Home Curated Shelf Collage Review

## Scope

This evidence covers the replacement of the Home page's below-hero public section with a dynamic Curated Shelf Collage and Selected Listening rail. The implementation is driven by the existing `/api/home/curated` contract and the generated boot snapshot for offline-first rendering.

## Product decisions

- The collage uses five editorial paths: Bengali Life & Legacy; Gothic & the Uncanny; Love, Society & Human Nature; Adventure, Nature & Wonder; and Short Masterpieces.
- Every cover and CTA is sourced from a canonical reader-enabled book record.
- The listening rail is filtered through the existing approved public-audiobook predicate. The current repository truth yields four approved public audiobooks, not an inferred or hardcoded count.
- Duplicate visible cover slugs are removed across collage groups while keeping deterministic admin-pinned, ranked, popularity, and fallback ordering.
- Internal release-gate language is not shown in customer-facing Home, Library, or first-visit-tour copy.

## Visual review

The local production build was served with Playwright at `1440x900`, `1536x864`, `768x1024`, `430x932`, and `390x844`. The `/api/home/curated` request was intercepted with the generated canonical snapshot only because the static file server does not provide the backend API; this keeps the visual data identical to the client boot snapshot without inventing content.

Measured results:

- Five shelf tiles rendered at every target viewport.
- Four selected-listening cards rendered from approved audio truth.
- Seventeen collage cover images loaded successfully from their canonical sources.
- `document.documentElement.scrollWidth` matched the viewport width at all tested sizes.
- Desktop uses an asymmetric feature tile and supporting editorial cards; tablet uses a balanced two-column grid; mobile stacks the paths and keeps listening cards in a contained scroll rail.
- Focus-visible styling and `prefers-reduced-motion` behavior are present in the collage stylesheet.

Screenshots and the contact sheet are stored beside this report.

## Verification boundary

This pass does not claim a Lighthouse 10/10 or a live production score. Lighthouse/axe runs, production API validation, and deployment checks must be run after the focused branch is merged and deployed. The current local evidence supports the catalog, release-safety, layout, and build acceptance categories only.

## Follow-up

Run the production validation command after deployment:

```sh
BASE=/Users/ronikbasak/Documents/GitHub/earnalism-digital-library
cd "$BASE" && npm --prefix frontend run build && python3 -m pytest -q backend/tests/test_home_curation_truth.py
```
