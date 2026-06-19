# SEO Crawlability Report

Status: `PASS_WITH_WARNINGS_DRACULA_FIRST`

| Check | Value |
| --- | --- |
| Sitemap URL count | Pending regeneration after Dracula-first UX merge |
| Book URL count | 1 approved live book intended: `/book/dracula` |
| Demo URL count | 0 |
| Robots sitemap present | True |
| Retired routes crawlable for deindexing | True |
| Homepage Dracula launch copy | True |
| Library controlled-launch copy | True |
| Dracula Book JSON-LD gated | True |
| Unapproved Book JSON-LD blocked | True |
| Client-side book metadata risk | True |

The public UX and client-side metadata now match the Dracula-first controlled publication state. SEO remains `PASS_WITH_WARNINGS` because the frontend is still a CRA SPA and dynamic route metadata is client-rendered.

## Priority Routes For Prerender/SSR Review

| Route |
| --- |
| / |
| /library |
| /pricing |
| /book/dracula |
| /reader/dracula |

Warning reason: `Client-rendered CRA book pages need prerender/SSR/static snapshots for durable Dracula social/search previews.`

No unsafe/fake Book schema is emitted by this audit. Book SEO must use available data only.

Book JSON-LD rights gated: `True`
Unsafe Book schema emitted: `False`
Unapproved reader routes public-gated: `True`

See `BOOK_SEO_PRERENDER_PLAN.md` for the controlled plan to close book-specific SEO without fake metadata.
