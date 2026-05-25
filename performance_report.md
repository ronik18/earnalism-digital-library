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
- The default post-deploy smoke threshold is `p95 < 5000ms` with 1 VU and 3 iterations. Override `K6_HTTP_P95_THRESHOLD`, `K6_SMOKE_VUS`, or `K6_SMOKE_ITERATIONS` if you want a stricter load gate later.
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

## Low-Hanging Performance Pass — 2026-05-21

This pass focused on small, production-safe changes that preserve the current visual experience and reader flow.

### Production Timing Sample Before Deploy

Measured from the local development machine against the currently deployed production URLs:

| URL | Status | TTFB | Total | Size |
| --- | ---: | ---: | ---: | ---: |
| `https://theearnalism.com` | 200 | 0.193s | 0.198s | 6.0KB |
| `https://api.theearnalism.com/health` | 200 | 0.921s | 0.924s | 124B |
| `https://api.theearnalism.com/api/categories` | 200 | 0.868s | 0.870s | 2.3KB |
| `https://api.theearnalism.com/api/books` | 200 | 0.860s | 0.864s | 6.5KB |
| `https://api.theearnalism.com/api/payments/config` | 200 | 0.406s | 0.406s | 68B |

### Local Build After Changes

| Artifact | Result |
| --- | ---: |
| Build directory | 1.0MB |
| Source maps emitted | 0 |
| Main JS gzip | 111.33KB |
| Main CSS gzip | 11.81KB |

### Changes Applied

| Area | Change | Expected Gain |
| --- | --- | --- |
| App startup | Replaced two public settings requests with one `/api/settings/public` request, with fallback to old endpoints. | One fewer API round trip on every public page load. |
| Book shelf API | `/api/books` now omits chapter arrays entirely for list browsing. | Lower response memory and payload growth as catalogue size increases. |
| Book detail API | `/api/books/{slug}` now returns metadata + ToC only; chapter bodies are loaded through the reader endpoint. | Faster book detail and reader bootstrap for long books. |
| Reader API | `/api/reader/chapter/{slug}/{chapter_id}` now loads chapter metadata first and fetches only the requested chapter body only after access is allowed. | Lower MongoDB document transfer and memory usage for large multi-chapter books; locked users no longer trigger body reads. |
| Frontend bundle | Moved Google OAuth provider out of the main app shell and into the login route boundary. | Keeps Google auth wiring out of first-load routes that do not need it. |
| Build output | Disabled production source map emission. | Smaller deploy artifact, less source exposure, faster upload/deploy. |

### Verification

```bash
npm run build --prefix frontend
cd backend && python3 -m py_compile server.py
git diff --check
```

All checks passed.

## Production Load Test — 2026-05-21

### Method

`k6` and Docker were not available on the local machine, so this run used a custom `asyncio` + `httpx` GET-only staged load test from the project root. It intentionally avoided auth mutations, payments, uploads, imports, admin routes, and wallet writes.

Tested full public reader-browse journeys:

1. `GET https://theearnalism.com/`
2. `GET https://theearnalism.com/library`
3. `GET https://api.theearnalism.com/api/categories`
4. `GET https://api.theearnalism.com/api/books`
5. `GET https://api.theearnalism.com/api/books/the-architecture-of-intelligent-systems`
6. `GET https://api.theearnalism.com/api/reader/chapter/the-architecture-of-intelligent-systems/b5793ecb-36a1-4d62-823a-f0547690a084`
7. `GET https://api.theearnalism.com/api/payments/config`

Reader target: `The Architecture of Intelligent Systems` → `The Working Vocabulary`.

Important limit: the backend currently enforces `240` general API requests/minute/source IP. Stages were kept at or below this practical single-IP ceiling, with cooldown windows between stages, so the test measures app behavior rather than intentionally tripping rate limits.

Raw local artifacts:

- `output/performance/loadtest_20260521T034927Z/loadtest_report.json`
- `output/performance/loadtest_20260521T034927Z/loadtest_records.json`

### Stage Summary

| Stage | Concurrent journeys | Requests | Success rate | Throughput | Avg | P50 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Warmup | 10 | 70 | 100% | 15.69 req/s | 495ms | 327ms | 1,599ms | 2,172ms |
| Browse | 25 | 175 | 100% | 34.65 req/s | 564ms | 273ms | 1,639ms | 2,191ms |
| Reader | 45 | 315 | 100% | 68.92 req/s | 514ms | 282ms | 1,325ms | 2,236ms |

### Endpoint P95 At 45 Concurrent Journeys

| Endpoint group | P95 | Status |
| --- | ---: | --- |
| Frontend home | 279ms | 45/45 `200` |
| Frontend library | 296ms | 45/45 `200` |
| API categories | 1,601ms | 45/45 `200` |
| API books | 920ms | 45/45 `200` |
| API book detail | 663ms | 45/45 `200` |
| API reader preview | 847ms | 45/45 `200` |
| API payment config | 284ms | 45/45 `200` |

### Findings

- The public frontend is comfortably fast under this load; Vercel/CDN delivery stayed below `300ms` p95 for home/library.
- The full public reader-browse journey passed `45` concurrent users from a single source IP with `0` failures and no `429` responses.
- The slowest public API path in this test was `/api/categories` at about `1.6s` p95, likely because it still depends on backend/Railway round-trip and Mongo/cache state.
- Reader preview p95 was under `900ms` at 45 concurrent journeys, which is acceptable for the current catalogue size.
- This test does not prove paid-reader heartbeat capacity because it intentionally avoided authenticated wallet/session writes.

### Current Capacity Interpretation

| Traffic type | Evidence-based current comfort range |
| --- | ---: |
| Public browsing and discovery | At least 45 concurrent full journeys from one source IP passed cleanly. |
| Public preview reading | At least 45 concurrent preview journeys passed with reader preview p95 under 900ms. |
| Paid authenticated reading | Not measured in this GET-only run; previous estimate remains 75-200 active readers until heartbeat/write testing is performed. |

### Next Load-Test Step

To measure beyond the single-IP rate-limit ceiling, run a distributed k6/cloud test or temporarily raise `RATE_LIMIT_DEFAULT_PER_MINUTE` in a staging environment. The next meaningful test should include authenticated paid reading with `/reading/session/start`, `/reading/pulse`, and `/reading/session/end`, using test users with isolated wallet credits.
