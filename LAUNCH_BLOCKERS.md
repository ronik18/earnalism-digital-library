# Launch Blockers

| Area | Severity | Blocker | Fix |
| --- | --- | --- | --- |
| production_parity | HIGH | Production https://theearnalism.com/shop returned redirect HTTP 308. | Removed/demo URLs must return 410 or 404 with X-Robots-Tag for deindexing. |
| production_parity | HIGH | Production /shop returned HTTP 308; /shop must not redirect. | Deploy current Vercel routing so /shop returns 410/noindex. |
| seo | HIGH | Book detail metadata is generated client-side after API load in the CRA app. | For 9.7+ launch SEO, prerender/SSR/static-snapshot priority book pages so crawlers receive book-specific metadata. |
| rights_source_readiness | HIGH | First batch has no approved real source metadata in the dry-run evidence. | Backfill source_url, source_license, source_hash, content_hash, and provenance_hash before publication. |
