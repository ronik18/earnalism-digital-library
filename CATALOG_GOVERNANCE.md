# Earnalism Public Content Governance Policy

## Allowed Public Content

- Homepage.
- Library and category shelves.
- Journal index and approved Earnalism journal articles.
- About and contact pages.
- Sign in, signup, account-entry, and payment/pricing pages.
- Reader pages for approved Earnalism books.
- Book detail pages for approved Earnalism books on `/book/*`.
- Approved paid or membership surfaces on `/pricing`, `/membership`, `/reading-pass`, `/institution`, or another explicitly approved non-WooCommerce route.
- School, creator, referral, and public-domain study-material pages.

## Blocked Public Content

- Fashion pages.
- Clothing pages.
- Apparel pages.
- Generic ecommerce demo products.
- WooCommerce sample products.
- Template blog posts.
- Unrelated lifestyle posts.
- Placeholder product pages.
- Test products.
- Sample posts.
- Lorem ipsum/template content.

## Current Enforcement

- `/product/*`, `/products/*`, `/product-category/*`, `/shop/*`, `/fashion/*`, `/clothing/*`, `/apparel/*`, and known demo terms are routed to a Vercel removed-content handler.
- `/product/*` is treated as legacy/demo WooCommerce residue for now. Approved Earnalism paid/book pages must use `/book/*`, `/pricing`, `/membership`, `/reading-pass`, `/institution`, or another explicitly approved non-WooCommerce route.
- Clearly irrelevant demo/ecommerce URLs return `410 Gone` through `frontend/api/removed-content.js`.
- The removed-content handler sets `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` intentionally does not block removed demo/ecommerce route families during deindexing, so crawlers can observe the `410` plus `X-Robots-Tag` response. Robots blocking can be reconsidered later after indexes have dropped the retired URLs.
- `frontend/scripts/generate-seo-assets.mjs` filters blocked route families and terms from `sitemap.xml`.
- `scripts/audit-public-content.mjs` produces dry-run JSON, CSV, and Markdown reports for public URL governance.

## Review Rule

If an item is ambiguous, do not delete it. Quarantine or noindex it first, record the reason in the audit report, then review manually before permanent removal.
