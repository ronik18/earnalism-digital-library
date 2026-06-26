# SEO Revenue Readiness Report

Launch status: LIVE_VERIFIED  
Production base URL: https://theearnalism.com  
Launch scope: Dracula reading-only revenue launch  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED

## Decision

SEO revenue readiness: GO_MONITOR_AND_OPTIMIZE

The public SEO surface is intentionally narrow and revenue-focused: Dracula is the only approved public reading release, Chapter 1 is free, pricing is indexable, and the reader page is noindex/canonicalized back to the public Dracula book page. No public audiobook metadata, Listen Now CTA, AudioObject schema, Kshudhita live metadata, or broad catalog claim is approved.

## Indexed Routes

The generated sitemap currently contains 11 routes:

| Route | Revenue role | Status |
| --- | --- | --- |
| `/` | Dracula-first landing and hero CTA path | INDEX_ALLOWED |
| `/library` | Controlled library with Dracula live and future titles pipeline-only | INDEX_ALLOWED |
| `/journal` | Editorial discovery surface | INDEX_ALLOWED |
| `/about` | Brand trust surface | INDEX_ALLOWED |
| `/contact` | Support/refund trust surface | INDEX_ALLOWED |
| `/pricing` | Reading-time wallet/pass conversion surface | INDEX_ALLOWED |
| `/micro-story` | Lightweight discovery surface | INDEX_ALLOWED |
| `/library?category=gothic-fiction` | Dracula category discovery | INDEX_ALLOWED |
| `/book/dracula` | Primary Dracula search landing page | INDEX_ALLOWED |
| `/journal/how-reading-shapes-better-founders` | Editorial discovery | INDEX_ALLOWED |
| `/journal/why-every-small-business-needs-a-story-before-a-strategy` | Editorial discovery | INDEX_ALLOWED |

## Noindex Or Blocked Routes

| Route group | Behavior | Reason |
| --- | --- | --- |
| `/reader/dracula` | Noindex and canonicalized to `/book/dracula` in static snapshots; allowed in robots for user access. | Avoid duplicate/paid-content leakage while keeping reader reachable. |
| `/account`, `/login`, `/signup`, `/admin`, `/api/*` | Disallowed/noindex or authenticated. | Private/account/payment surfaces should not be indexed. |
| Legacy ecommerce/demo routes | Tombstone canary expects 404/410. | Avoid stale WooCommerce/fashion crawl surfaces. |
| Kshudhita/future titles | Excluded from sitemap as public reading/audio products. | Pipeline-only until rights, QA, and approval gates pass. |

## Metadata Audit

| Surface | Finding |
| --- | --- |
| Homepage metadata | Dracula-first title, description, canonical, Open Graph, Twitter card, and Organization/WebSite JSON-LD are present. |
| `/book/dracula` metadata | Dracula-specific title, description, canonical, Open Graph book type, Twitter card, Book JSON-LD, WebPage JSON-LD, and BreadcrumbList are generated. |
| `/pricing` metadata | Pricing route remains indexable and tied to reading-time wallet/pass copy. |
| `/reader/dracula` metadata | Reader snapshot is noindex/follow and canonicalized to `/book/dracula`. |
| Sitemap | 11 URLs, includes `/book/dracula`, excludes `/reader/*`, Kshudhita, audio files, and demo ecommerce URLs. |
| Robots | Blocks admin/account/api/private routes while allowing `/reader/dracula` access for users. |
| Social preview image | Uses local owner-designed Dracula cover artwork. No external hotlinking. |
| JSON-LD | Book schema is reading-only and rights-safe; no AudioObject metadata. |

## Quality Scores

| Area | Score | Notes |
| --- | ---: | --- |
| Metadata quality | 9.4/10 | Strong controlled surface; continue monitoring Search Console after launch. |
| Dracula search-preview quality | 9.5/10 | Clear title, source-truth wording, and local cover preview. |
| Social-preview quality | 9.5/10 | Strong cover image and truthful copy. |
| Paid-content leakage safety | 9.8/10 | Reader is noindex/canonicalized and sitemap excludes reader URLs. |
| Audiobook-claim safety | 9.9/10 | No public audiobook metadata, Listen Now CTA, or AudioObject schema. |

## Remaining SEO Blockers

No repo-level SEO blocker remains for Dracula reading-only launch monitoring.

Owner dashboard verification required:

- Confirm Google Search Console property, sitemap submission, and crawl status.
- Monitor indexed URL count for removed demo/ecommerce routes.
- Review real search snippets after recrawl.
- Run external rich-results validation for `/book/dracula`.
- Monitor Core Web Vitals after enough production traffic exists.

## Recommended Next SEO Actions

1. Submit or resubmit `https://theearnalism.com/sitemap.xml` in Search Console.
2. Request indexing for `/book/dracula`.
3. Watch for stale WooCommerce/fashion URLs and use removals only if tombstones are not enough.
4. Add one high-quality Dracula editorial/internal link if search impressions are low after crawl.
5. Keep audiobook metadata out of public SEO until highlighted-text sync QA, accessibility QA, rights/legal, and release gates pass.
