# Earnalism Public Content Governance Policy

## Allowed Public Content

- Homepage.
- Library and category shelves.
- Journal index and approved Earnalism journal articles.
- About and contact pages.
- Sign in, signup, account-entry, and payment/pricing pages.
- Reader pages for approved Earnalism books.
- Book/product pages for approved Earnalism books.
- Reading pass, membership, institution, school, creator, referral, and public-domain study-material pages.

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
- Clearly irrelevant demo/ecommerce URLs return `410 Gone` through `frontend/api/removed-content.js`.
- The removed-content handler sets `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` blocks crawler access to demo ecommerce and fashion route families as a fallback.
- `frontend/scripts/generate-seo-assets.mjs` filters blocked route families and terms from `sitemap.xml`.
- `scripts/audit-public-content.mjs` produces dry-run JSON, CSV, and Markdown reports for public URL governance.

## Review Rule

If an item is ambiguous, do not delete it. Quarantine or noindex it first, record the reason in the audit report, then review manually before permanent removal.
