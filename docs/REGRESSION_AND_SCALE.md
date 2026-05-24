# Earnalism Regression And Scale Gates

This repo now has a single regression command for source changes:

```bash
npm run regression
```

It runs:

- backend unit regression for content processing, Bengali rendering, and publishing-pipeline gates;
- frontend Jest regression;
- frontend production build against the production API URL;
- browser e2e regression against the built frontend with the live API proxied safely for localhost;
- optional live backend integration tests and optional 100-user k6 load tests.

## Optional Live Backend Regression

The live backend tests create users, adjust wallets, and exercise payment simulators. Run them only with test/admin credentials available:

```bash
RUN_LIVE_BACKEND=1 npm run regression
```

## 100 Concurrent User Load Gate

Use this after deploy, or any time you want to verify the public platform path under 100 simultaneous virtual users:

```bash
RUN_LOAD=1 npm run regression
```

Or run only the load test:

```bash
FRONTEND_URL=https://theearnalism.com \
API_URL=https://api.theearnalism.com \
K6_LOAD_VUS=100 \
K6_LOAD_DURATION=2m \
npm run load:100
```

The load profile covers:

- landing page render;
- cached `/api/home` payload;
- public book catalog;
- book detail metadata;
- preview chapter access;
- payment pack discovery.

Default thresholds:

- global HTTP failure rate below 1%;
- global p95 below 2.5s;
- catalog p95 below 1.2s;
- reader p95 below 1.8s.

Install k6 once on macOS:

```bash
brew install k6
```

## CI Enforcement

`.github/workflows/regression-suite.yml` runs the regression suite on pull requests and pushes to `main` and `production-deploy`.

`.github/workflows/post-deploy-k6.yml` runs after pushes to deployment branches and now includes both the existing smoke test and the 100-user k6 load test.

## Performance Changes Supporting 100 Concurrent Users

- `/api/home` combines categories, featured book, and live books into one cached payload, reducing landing-page API fanout.
- Public cache includes `/api/home`, catalog endpoints, free reader previews, payment pack metadata, and settings.
- Server-side public cache TTL defaults to `PUBLIC_CACHE_TTL_SECONDS=300` so normal reading bursts do not rebuild catalog payloads mid-session; admin writes still clear the cache immediately.
- MongoDB connection pooling defaults are raised and configurable:
  - `MONGODB_MAX_POOL_SIZE=200`
  - `MONGODB_MIN_POOL_SIZE=5`
  - `MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000`
- API rate-limit defaults are raised for 100-user bursts while remaining configurable by environment:
  - `RATE_LIMIT_PUBLIC_PER_MINUTE=30000` for cached catalog, home, public settings, and pack metadata.
  - `RATE_LIMIT_READER_PER_MINUTE=15000` for reader chapter checks and preview access.
  - Auth, upload, webhook, and payment mutation limits stay on separate tighter buckets.
- The frontend prefetches high-intent route bundles during idle time: library, book detail, reader, pricing, and login.

No finite test suite can mathematically prove every future use case forever. The gate is designed to cover the current critical Earnalism flows: browse, preview, read, account auth surfaces, payment entry, publishing pipeline safety, and production load capacity signals.
