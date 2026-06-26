# Performance Revenue Readiness Report

Launch status: LIVE_VERIFIED  
Production base URL: https://theearnalism.com  
Launch scope: Dracula reading-only revenue launch  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED

## Decision

Performance readiness: GO_MONITOR_WITH_QUICK_WINS

The production launch can continue because local build succeeds, route canary passes, assets are static-cacheable, and no public audio binaries exist. Performance is good enough for post-launch monitoring, but not a perfect score: the largest shelf images and Create React App bundle should be optimized after the first 24-48 hour revenue read.

## Build Artifact Summary

Latest local build evidence:

| Artifact | Size | Notes |
| --- | ---: | --- |
| `frontend/build` total | 7.7 MB | Static CRA build with generated SEO snapshots. |
| `frontend/build/static/js/main.*.js` | 359 KB | Main application bundle. |
| `frontend/build/static/js/778.*.chunk.js` | 116 KB | Largest async chunk observed. |
| `frontend/build/static/css/main.*.css` | 95 KB | Main CSS bundle. |
| `frontend/build/assets/shelves/bengali.jpg` | 747 KB | Largest public image asset; candidate for compression/WebP/AVIF follow-up. |
| Dracula cover artwork | Local WebP | Used for hero/social preview without external hotlinking. |

## What Is Performance-Ready

- Route-level code splitting exists through `React.lazy` page imports.
- Static SEO snapshots are generated for crawler-critical routes.
- Nginx static configuration includes long cache headers for hashed assets when that deployment path is used.
- Vercel frontend build is static and should scale at CDN edge for public GET traffic.
- Reader code caches chapter responses in memory during the session.
- Backend public cache includes catalog/home/reader-preview/payment-pack surfaces where safe.
- Post-deploy canary is GET-only and mutation-free.

## Performance Risks

| Risk | Impact | Recommendation |
| --- | --- | --- |
| Largest shelf image is 747 KB | Mobile first-load and lower bandwidth users may pay extra cost. | Compress or generate modern responsive WebP/AVIF shelf images. |
| CRA main bundle remains 359 KB | Acceptable but not tiny; impacts first interactive time. | Continue route splitting and review heavy admin/editor code separation. |
| Third-party scripts | Razorpay and optional Google/PostHog can affect runtime if enabled. | Keep analytics opt-in; load Razorpay only from pricing/payment path. |
| Backend cold start | Railway worker startup can affect first request after idle if plan sleeps. | Owner dashboard verification required for plan and always-on settings. |
| Payment flow latency | Checkout and wallet credit rely on Razorpay plus backend verify/webhook. | Monitor checkout-start to wallet-credit time; keep idempotency checks. |
| Mobile reader speed | Long reader route can be heavy on older phones. | Monitor mobile canary/user reports; keep reader assets lean. |

## Caching And API Readiness

- Public static assets should be CDN-cacheable.
- `frontend/nginx.conf` caches static assets for one year and sitemap/robots for shorter windows if using that container path.
- Backend public cache TTL defaults are documented in `docs/REGRESSION_AND_SCALE.md`.
- Redis cache status requires owner/admin dashboard verification in production.
- Payment mutation endpoints must not be cached.
- Audio binaries are not public assets and are not part of performance launch scope.

## Quick Wins

1. Compress `frontend/public/assets/shelves/bengali.jpg` and other shelf images into responsive WebP/AVIF variants.
2. Add a bundle-size budget report after first production revenue week.
3. Keep first-time tour lightweight and avoid adding third-party pixels.
4. Use production canary response timing logs to identify route outliers.
5. Review mobile Core Web Vitals in Search Console once data is available.

## Recommended Thresholds

| Metric | Target | Action threshold |
| --- | ---: | --- |
| Homepage document response | < 800 ms from primary region | Investigate if repeated > 1500 ms. |
| Static JS transfer | Keep main JS < 450 KB uncompressed | Split if main crosses 500 KB. |
| Largest public image | < 350 KB where possible | Recompress if any non-hero image exceeds 500 KB. |
| Payment checkout start | User-visible checkout within 3 seconds after click | Investigate script/API latency if slower. |
| Wallet credit after success | Near-immediate or support-window documented | Escalate if credits are delayed or duplicated. |

## Performance Score

Performance readiness score: 8.8/10

This is launch-ready for monitoring, not a perfect score. The largest shelf images, dashboard-only cold-start verification, and production Core Web Vitals evidence remain follow-up work.
