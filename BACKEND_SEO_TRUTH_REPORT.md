# Backend SEO Truth Report

## Decision

The backend and generated SEO assets must agree that Dracula is the only live approved
book route during the controlled launch.

## Verified Policy

- Public sitemap includes `/book/dracula`.
- Public sitemap excludes `/reader/*`.
- Public sitemap excludes Kshudhita Pashan and other pipeline/unapproved book routes.
- Public API projections mark only Dracula as `public_json_ld_enabled=true`.
- Pipeline candidates must not produce public Book JSON-LD from backend data.
- Removed demo ecommerce/fashion URLs remain excluded from sitemap.

## Backend Guardrail

`backend/catalog_truth.py` is the backend source of truth for:

- live approved status
- pipeline candidate status
- reader exposure
- preview exposure
- audio exposure
- public metadata projection

`scripts/catalog_truth_audit.py --mode api` also compares backend live approved
slugs against the shared controlled launch config in `data/controlled_launch.json`.
`frontend/scripts/generate-seo-assets.mjs` reads the same config when generating
sitemap book routes.

## Remaining SEO Limitation

CRA/client-rendered metadata can still limit crawler-visible per-page metadata.
This remains a separate prerender/SSR/static-snapshot recommendation and is not
changed by this backend catalog truth PR.

## Result

SEO truth is aligned for the controlled launch: Dracula may be indexed as the live
approved core reading page; unapproved/pipeline titles must not be indexed as public
reading products.

Post-deploy, `npm run launch:backend-catalog-truth-canary` must pass before SEO or
growth expansion proceeds. If Dracula is not classified as `LIVE_APPROVED`, then
`/book/dracula` must be treated as an unapproved sitemap entry until fixed.
