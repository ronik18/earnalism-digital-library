# Legacy Surface Tombstone Report

Generated: 2026-06-21

This report documents the read-only public-surface audit and tombstone hardening for stale demo, ecommerce, fashion, template, and legacy route families. No deployment, book publication, audio enablement, Razorpay setting change, or production data mutation was performed.

## Audited Route Categories

- Frontend React routes in `frontend/src/App.js`.
- Vercel rewrites, redirects, headers, and SPA fallback in `frontend/vercel.json`.
- Removed-content handler in `frontend/api/removed-content.js`.
- Sitemap and robots generation in `frontend/scripts/generate-seo-assets.mjs`.
- Static sitemap and robots behavior in `frontend/public/sitemap.xml` and `frontend/public/robots.txt`.
- Launch/readiness removed-route canaries in `scripts/launch_readiness_audit.py` and `scripts/post_deploy_route_canary.py`.
- Public catalog audit policy in `scripts/audit-public-content.mjs`.
- Regression coverage in `regression/modules/13-public-content-governance.test.js` and `regression/modules/14-ux-conversion-static.test.js`.
- Social preview raw HTML audit policy in `scripts/social_preview_audit.py`.
- Static public assets under `frontend/public`.
- Public About and Journal page copy.
- Public blog API endpoints in `backend/server.py`.
- Current product truth in `PRODUCT_TRUTH_LEDGER.md`.

## Stale Routes Found

Already covered before this pass:

- `/shop`, `/shop/`, `/shop/*`
- `/product`, `/product/*`
- `/products`, `/products/*`
- `/product-category`, `/product-category/*`
- `/fashion`, `/fashion/*`
- `/clothing`, `/clothing/*`
- `/apparel`, `/apparel/*`
- known demo terms such as `patterned-wrap-dress`, `denim-jacket`, `denim-jackets`, `woocommerce`, `sample-product`, `placeholder-product`, and `lorem-ipsum`

Gaps closed in this pass:

- `/blog`, `/blog/*`
- `/post`, `/post/*`
- `/category`, `/category/*`
- `/tag`, `/tag/*`
- `/cart`, `/cart/*`
- `/checkout`, `/checkout/*`
- `/my-account`, `/my-account/*`
- `/woocommerce`
- `/sample-product`
- `/placeholder-product`
- `/lorem-ipsum`
- `/wp-admin`, `/wp-admin/*`
- `/wp-content`, `/wp-content/*`
- `/wp-json`, `/wp-json/*`
- `/journal/the-quiet-power-of-a-premium-bookstore-brand`
- `/api/blog/the-quiet-power-of-a-premium-bookstore-brand`

## Behavior Before

- Some stale route families were already routed to `frontend/api/removed-content.js` and returned `410 Gone` with `X-Robots-Tag: noindex, nofollow, noarchive`.
- Several old blog, WordPress, root WooCommerce, cart, checkout, and tag/category-style URLs could still fall through to the SPA shell or had weaker coverage than product/shop/fashion routes.
- The tombstone response included a library link, which was safe but less neutral than a retired-route page should be.
- About, Journal, and the base HTML template still contained older `online bookstore` / `self-publishing house` / `bookstore` positioning.
- The backend public blog API could still expose the stale `the-quiet-power-of-a-premium-bookstore-brand` seed/article if present in data.

## Behavior After

- Retired route families listed above are routed to the removed-content handler before the SPA fallback.
- Known stale demo/ecommerce/template paths return `410 Gone`.
- Unknown retired paths continue to return branded `404` through the same noindex handler.
- Tombstone responses carry `X-Robots-Tag: noindex, nofollow, noarchive`.
- Tombstone responses include `<meta name="robots" content="noindex,nofollow,noarchive">`.
- Tombstone responses do not emit Open Graph product metadata.
- Tombstone responses do not expose `Start Reading`, `Listen Now`, `Buy Now`, `Add to Cart`, or checkout-like CTAs.
- Tombstone responses do not reflect raw path/query input.
- Robots intentionally does not disallow retired routes so crawlers can observe 410/noindex during deindexing.
- Sitemap generation blocks the expanded stale route prefixes and terms.
- The stale bookstore journal slug is blocked in Vercel routing and excluded from backend public blog list/detail responses.
- The stale bookstore seed post is marked unpublished for future seed runs.
- About, Journal, and the base HTML template now use Dracula-first digital reading-room positioning.

## Files Changed

- `frontend/api/removed-content.js`
- `frontend/vercel.json`
- `frontend/scripts/generate-seo-assets.mjs`
- `frontend/public/index.html`
- `frontend/public/sitemap.xml`
- `frontend/src/pages/About.jsx`
- `frontend/src/pages/Journal.jsx`
- `SEO_CRAWLABILITY_REPORT.md`
- `backend/server.py`
- `scripts/audit-public-content.mjs`
- `scripts/launch_readiness_audit.py`
- `scripts/post_deploy_route_canary.py`
- `regression/modules/13-public-content-governance.test.js`
- `regression/modules/14-ux-conversion-static.test.js`
- `LEGACY_SURFACE_TOMBSTONE_REPORT.md`

## Regression Tests Added

- Expanded removed-route fixtures to include legacy blog, post, category, tag, cart, checkout, account, WooCommerce root, sample/placeholder product roots, lorem ipsum, and WordPress-style public paths.
- Added Vercel rewrite assertions for root and wildcard legacy route families.
- Added removed-content assertions that tombstone responses contain no product Open Graph metadata and no commerce/reader/audio CTAs.
- Added backend static assertion that the retired bookstore journal slug is filtered from the public blog API and returns 410/noindex on detail.
- Added UX/static assertion that About, Journal, and the base HTML template no longer use stale bookstore/self-publishing positioning.
- Kept existing checks that demo routes do not redirect, do not return shell `200`, remain out of sitemap, and remain crawlable for deindexing.

## Sitemap And SEO Report Changes

- `frontend/public/sitemap.xml` now excludes `/journal/the-quiet-power-of-a-premium-bookstore-brand`.
- `SEO_CRAWLABILITY_REPORT.md` now reports 11 sitemap URLs instead of 12 because that stale journal URL is no longer indexable.
- `robots.txt` remains unchanged: retired URLs stay crawlable so crawlers can observe `410` plus `X-Robots-Tag`.

## Approved Product Truth Preserved

- Dracula remains the only approved core public reading release.
- Dracula reader/preview and pricing routes remain intact.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks remain non-public.
- Razorpay/live payment settings were not changed.
- `PRODUCT_TRUTH_LEDGER.md` was not weakened.

## Remaining Risks

- Current production may still serve stale behavior until this branch is merged and deployed.
- Static audio assets already present under `frontend/public/audio` remain outside the scope of this legacy ecommerce/template tombstone pass; public audiobook claims remain blocked by product-truth and launch-audio guardrails.
- Future legitimate route families under `/blog`, `/post`, `/category`, `/tag`, `/cart`, or `/checkout` would require an explicit policy change before they can be public.
- Search engines may take time to deindex retired URLs even after 410/noindex is deployed.
- If production data contains additional stale journal slugs not listed here, they require separate review and tombstone entries.

## Rollback Instructions

1. Revert the commit that adds this report and route hardening.
2. Restore the previous `frontend/vercel.json` rewrites.
3. Restore the previous blocked-term lists in `frontend/api/removed-content.js`, `frontend/scripts/generate-seo-assets.mjs`, `scripts/audit-public-content.mjs`, `scripts/launch_readiness_audit.py`, and `scripts/post_deploy_route_canary.py`.
4. Restore previous About, Journal, public index, backend public blog, and seed-post behavior if needed.
5. Restore the previous regression expectations in `regression/modules/13-public-content-governance.test.js` and `regression/modules/14-ux-conversion-static.test.js`.
6. Re-run:
   - `npm --prefix frontend run build`
   - `npm run launch:seo-audit`
   - `npm run launch:social-preview-audit`
   - `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
