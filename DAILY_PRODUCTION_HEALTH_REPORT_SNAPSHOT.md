# Daily Production Health Report Snapshot

This is a committed sample snapshot from the 2026-06-20 IST owner audit. Recurring daily reports should be generated locally with `npm run owner:daily-growth-audit`, which writes dated artifacts under `output/daily/YYYY-MM-DD/`.

Date: 2026-06-20 IST

Overall production health score: 9.4 / 10

Recommendation: GO for keeping current production online; HOLD for broader launch expansion until SEO and public CTA safety fixes are merged and deployed.

## Checks Run

- `npm run launch:post-deploy-route-canary`: PASS
- `npm run launch:production-parity`: PASS
- `npm run launch:readiness`: HOLD_FOR_FIXES
- Direct backend health: `https://api.theearnalism.com/healthz` returned 200
- Direct API health: `https://api.theearnalism.com/api/health` returned 200
- Frontend home, library, pricing, Dracula book, and Dracula reader routes returned 200

## Removed Route Safety

All sampled retired/demo routes returned 410 with `X-Robots-Tag: noindex, nofollow, noarchive`.

- `/product/patterned-wrap-dress`: 410
- `/denim-jackets`: 410
- `/shop`: 410
- `/fashion`: 410

No removed route redirected. No removed route served a generic homepage shell.

## Top Wins

- Backend and frontend are reachable.
- Removed ecommerce/fashion/template URLs are correctly gone from public 200 surfaces.
- Production route canary and production parity both passed.

## Top Risks

- Full launch readiness remains HOLD because the SEO audit flags client-rendered book metadata.
- Public API still exposes many published books, so frontend CTA gating must be strict.
- Raw HTML remains generic because the frontend is CRA/client-rendered.

## Exact Fixes Needed

- Merge and deploy the CTA safety branch so only Dracula has live reader CTAs.
- Add prerender, SSR, or static-snapshot metadata for priority book pages.
- Keep route-canary checks running after every deploy.

Rollback needed today: No.
