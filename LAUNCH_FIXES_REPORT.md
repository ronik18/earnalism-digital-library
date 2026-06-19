# Launch Fixes Report

## Corrective Fixes Applied In Phase 13

- Routed exact `/shop` and `/shop/` through the removed-content function instead of redirecting to `/library`.
- Added explicit audiobook remote action env guards for upload, provider calls, and production sync.
- Added read-only launch audit commands for production parity, SEO, performance, and audio readiness.

## Remaining Fixes

| Area | Fix |
| --- | --- |
| production_parity | Removed/demo URLs must return 410 or 404 with X-Robots-Tag for deindexing. |
| production_parity | Deploy current Vercel routing so /shop returns 410/noindex. |
| seo | For 9.7+ launch SEO, prerender/SSR/static-snapshot priority book pages so crawlers receive book-specific metadata. |
| rights_source_readiness | Backfill source_url, source_license, source_hash, content_hash, and provenance_hash before publication. |
