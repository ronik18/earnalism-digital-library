# SEO Crawlability Report

Status: `BLOCKED_FOR_BOOK_SEO`

| Check | Value |
| --- | --- |
| Sitemap URL count | 124 |
| Book URL count | 105 |
| Demo URL count | 0 |
| Robots sitemap present | True |
| Retired routes crawlable for deindexing | True |
| Homepage static meta complete | True |
| Book JSON-LD detected | True |
| Client-side book metadata risk | True |

Launch SEO should stay on HOLD until priority book pages are either prerendered or otherwise verified as crawlable beyond the generic CRA shell.

## Priority Routes For Prerender/SSR Review

| Route |
| --- |
| / |
| /library |
| /pricing |
| /book/the-principles-of-scientific-management |
| /book/acres-of-diamonds |
| /book/my-life-and-work |
| /book/the-science-of-getting-rich |
| /book/the-art-of-money-getting |

Blocked reason: `Client-rendered CRA book pages need prerender/SSR/static snapshots for durable book SEO.`

No unsafe/fake Book schema is emitted by this audit. Book SEO must use available data only.

Book JSON-LD rights gated: `True`
Unsafe Book schema emitted: `False`

See `BOOK_SEO_PRERENDER_PLAN.md` for the controlled plan to close book-specific SEO without fake metadata.
