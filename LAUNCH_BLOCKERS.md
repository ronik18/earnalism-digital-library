# Launch Blockers

| Area | Severity | Blocker | Fix |
| --- | --- | --- | --- |
| seo | HIGH | Book detail metadata is generated client-side after API load in the CRA app. | For 9.7+ launch SEO, prerender/SSR/static-snapshot priority book pages so crawlers receive book-specific metadata. |
| rights_source_readiness | HIGH | First batch has no approved real source metadata in the dry-run evidence. | Backfill source_url, source_license, source_hash, content_hash, and provenance_hash before publication. |
