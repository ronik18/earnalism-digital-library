# SEO Blocked For Book SEO Diagnosis

Status before this PR: `BLOCKED_FOR_BOOK_SEO`.

`npm run launch:seo-audit` reported one high-severity blocker: the CRA book detail page generated book-specific metadata only after client-side API loading. That meant crawlers could receive the generic app shell instead of Dracula-specific title, description, canonical, social cards, and Book JSON-LD.

## Failed URL

| URL | Before fix |
| --- | --- |
| `/book/dracula` | Book metadata depended on React hydration and API data. |

## Raw HTML Findings Before Fix

| Requirement | Before fix |
| --- | --- |
| Dracula-specific title before JS | Not durable. |
| Meta description before JS | Not durable. |
| Canonical `/book/dracula` before JS | Not durable. |
| Open Graph tags before JS | Not durable. |
| Twitter card tags before JS | Not durable. |
| Book JSON-LD before JS | Not durable. |
| Homepage static HTML | Older broad-library language existed in the static shell. |
| `/reader/dracula` policy | Should be `noindex,follow` with canonical `/book/dracula`. |

## Corrective Direction

This PR adds static HTML snapshots after the CRA build for `/`, `/book/dracula`, `/library`, `/pricing`, `/journal`, `/contact`, and `/reader/dracula`.

`/book/dracula` is the indexable landing page. `/reader/dracula` is noindex and canonicalized to `/book/dracula`.
