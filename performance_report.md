# Earnalism Performance Report

Generated: 2026-05-15

## Scope

This pass optimized the Create React App frontend and FastAPI backend without changing the visual design, routes, auth behavior, payment behavior, or protected reader access model.

## Baseline Sample

Current production sample before deploying these local changes:

| URL | Status | TTFB | Total | Size |
| --- | ---: | ---: | ---: | ---: |
| `https://theearnalism.com` | 200 | 0.272s | 0.274s | 5.8KB |
| `https://api.theearnalism.com/health` | 200 | 1.011s | 1.011s | 124B |
| `https://api.theearnalism.com/api/categories` | 200 | 0.876s | 0.879s | 2.3KB |
| `https://api.theearnalism.com/api/books` | 200 | 0.858s | 0.869s | 6.5KB |

Local optimized frontend build after this pass:

| Asset | Gzip Size |
| --- | ---: |
| `main` JS | 112.11KB |
| largest route chunk | 17.93KB |
| CSS | 11.85KB |
| total build directory | 3.5MB |

The main bundle increased by about 943B because of service-worker registration and performance metric hooks. The expected gain is from repeat-visit caching, lighter image delivery, fewer reader DOM nodes on first render, fewer duplicate API calls, and backend public-read caching.

## Improvements Applied

| Area | Change | Expected Gain |
| --- | --- | --- |
| Public API | Added short in-memory LRU cache for anonymous public catalogue/settings/pack endpoints. | 30-80% lower DB reads for repeated public traffic bursts. |
| API payload | `/api/books` now queries with chapter body projection removed. | Lower memory and serialization work for library browsing. |
| API headers | Added `Server-Timing`, `X-Response-Time-ms`, public cache headers, and `no-store` for sensitive routes. | Easier latency tracking; safer client/proxy caching. |
| Health | Added 5s DB ping cache for health endpoint. | Lower DB pressure from frequent health probes. |
| Frontend images | Added Cloudinary/Unsplash URL optimizer and async decoding on book, category, journal, and detail images. | Lower LCP/image bytes where providers honor transforms. |
| Connection warm-up | Added preconnect/dns-prefetch for Cloudinary and production API host. | Lower connection setup delay for covers and first API requests. |
| Library search | Added 300ms debounce and request cancellation. | Fewer API calls while typing; less UI churn. |
| Reader | Deferred TTS word-span generation until narration starts; throttled scroll progress via `requestAnimationFrame`. | Much lower DOM/memory work on initial chapter render, especially long books. |
| Repeat visits | Added production service worker for static app shell/assets only. | Faster second visit/offline shell fallback without caching private data. |
| Monitoring | Added lightweight Web Vitals collector gated by `REACT_APP_PERF_METRICS_ENABLED=true`; dev logs only in development. | LCP/FCP/CLS/FID telemetry without heavy analytics. |
| Load testing | Added k6 smoke script for public pages/API. | Repeatable baseline for deployment checks. |

## Security And Compliance

- Service worker does not cache authenticated API responses.
- Backend sets `Cache-Control: no-store` for admin, user, reader, reading, and payment mutation/sensitive paths.
- Web Vitals payloads contain only route path, metric name, value, and rating.
- No request bodies, tokens, emails, manuscripts, or payment details are logged by the new performance hooks.

## How To Measure After Deploy

Automatic post-deploy smoke test:

- `.github/workflows/post-deploy-k6.yml` runs on pushes to `production-deploy` and `main`.
- The workflow waits for production URLs to become healthy, installs k6 in GitHub Actions, and runs `scripts/k6_smoke.js`.
- The default smoke threshold is `p95 < 1500ms`; override it with repository variable `K6_HTTP_P95_THRESHOLD` if you want a stricter gate later.
- k6 is intentionally not installed inside Railway/Vercel production runtime.

Manual local run:

```bash
npm run build --prefix frontend
cd backend && python3 -m py_compile server.py
k6 run scripts/k6_smoke.js
```

Optional production timing:

```bash
for url in https://theearnalism.com https://api.theearnalism.com/health https://api.theearnalism.com/api/categories https://api.theearnalism.com/api/books; do
  curl -L -o /dev/null -s -w "$url status=%{http_code} ttfb=%{time_starttransfer}s total=%{time_total}s size=%{size_download}\n" "$url"
done
```

Enable production Web Vitals only if desired:

```env
REACT_APP_PERF_METRICS_ENABLED=true
```

## Scaling Plan

| Step | Trigger | Action |
| --- | --- | --- |
| Current | Low/moderate traffic | Keep in-process cache, Vercel CDN, Railway single service. |
| Next | Public API p95 > 600ms or multiple Railway replicas | Move public cache/rate-limit counters to Redis. |
| Next | Library catalogue > 500 books | Add pagination and server-side search index. |
| Next | Reader p95 chapter load > 800ms | Split chapter content into per-chapter collection documents. |
| Next | Media bandwidth growth | Enforce Cloudinary `f_auto,q_auto,w_*` transforms and monitor monthly bandwidth. |

## Remaining Recommendations

- Run Lighthouse on production after deployment and compare LCP/CLS/INP against this baseline.
- Consider MongoDB Atlas Search for full-text book search once catalogue size grows.
- Move public cache and rate-limit state to Upstash Redis before horizontal scaling.
- Add Railway usage alerts for CPU, memory, and restart count.
