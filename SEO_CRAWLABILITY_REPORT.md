# SEO Crawlability Report

Status: `BLOCKED`

| Check | Value |
| --- | --- |
| Sitemap URL count | 94 |
| Book URL count | 77 |
| Demo URL count | 0 |
| Robots sitemap present | True |
| Retired routes crawlable for deindexing | True |
| Homepage static meta complete | True |
| Homepage static source | frontend/build/index.html |
| Dracula book static source | frontend/build/book/dracula/index.html |
| Book JSON-LD detected | True |
| Client-side book metadata risk | False |

Launch SEO remains HOLD only when the raw HTML checks below fail. Passing checks mean the priority pages are crawler-visible before React hydration.

## Raw HTML Checks

### /book/dracula
| Check | Pass |
| --- | --- |
| snapshot_available | True |
| title_dracula_bram_stoker | True |
| description_mentions_dracula | True |
| canonical_book_dracula | True |
| og_tags_complete | True |
| twitter_tags_complete | True |
| book_json_ld_present | True |
| webpage_json_ld_present | True |
| breadcrumb_json_ld_present | True |
| no_fake_rating_review | True |
| no_audio_claim | True |
| no_broad_catalog_claim | True |
| not_client_placeholder | True |

### /
| Check | Pass |
| --- | --- |
| dracula_first | False |
| no_broad_catalog_claim | True |
| organization_json_ld | True |
| website_json_ld | True |

### /reader/dracula
| Check | Pass |
| --- | --- |
| snapshot_available | True |
| noindex_follow | True |
| canonical_to_book | True |
| excluded_from_sitemap | True |

## Priority Routes For Prerender/SSR Review

| Route |
| --- |
| / |
| /library |
| /pricing |
| /book/a-ghost-story |
| /book/a-jury-of-her-peers |
| /book/a-mystery-of-heroism |
| /book/alices-adventures-in-wonderland |
| /book/bn-027 |

Blocked reason: `none`

No unsafe/fake Book schema is emitted by this audit. Book SEO must use available data only.

Book JSON-LD rights gated: `False`
Unsafe Book schema emitted: `False`

See `BOOK_SEO_PRERENDER_PLAN.md` for the controlled plan to close book-specific SEO without fake metadata.
