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

## 10X Burst Readiness Gate

Use this before high-traffic launches to simulate a sudden 10X jump from the
100-user gate to 1,000 simultaneous virtual readers:

```bash
FRONTEND_URL=https://theearnalism.com \
API_URL=https://api.theearnalism.com \
npm run load:10x
```

Override the size or duration when needed:

```bash
K6_LOAD_VUS=1500 K6_LOAD_DURATION=5m npm run load:10x
```

The backend Railway start command now honors `WEB_CONCURRENCY` so every replica
can run multiple Uvicorn workers instead of one process. Suggested production
burst settings:

```bash
WEB_CONCURRENCY=4
UVICORN_KEEP_ALIVE=15
MONGODB_MAX_POOL_SIZE=100
MONGODB_MIN_POOL_SIZE=2
PUBLIC_CACHE_TTL_SECONDS=300
PUBLIC_CACHE_MAX_ENTRIES=512
RATE_LIMIT_PUBLIC_PER_MINUTE=300000
RATE_LIMIT_READER_PER_MINUTE=150000
```

For a true sudden 10X event, keep at least three Railway replicas warm before
the launch window and scale higher if the 10X k6 gate shows p95 pressure. The
CLI command is:

```bash
railway scale --service earnalism us-west=3
```

Do not raise auth, payment, webhook, or upload mutation limits without a
separate fraud and abuse review. If the backend runs more than one replica for
long periods, move rate-limit counters and public cache entries to Redis or an
edge/WAF layer so throttling and cache warmth are shared across replicas.
MongoDB pool settings are per worker process, so `WEB_CONCURRENCY=4` and
`MONGODB_MAX_POOL_SIZE=100` means up to 400 MongoDB connections per Railway
replica.

## CI Enforcement

`.github/workflows/regression-suite.yml` runs the regression suite on pull requests and pushes to `main` and `production-deploy`.

`.github/workflows/post-deploy-k6.yml` runs after pushes to deployment branches and now includes both the existing smoke test and the 100-user k6 load test.

## Performance Changes Supporting 100 Concurrent Users

- `/api/home` combines categories, featured book, and live books into one cached payload, reducing landing-page API fanout.
- Public cache includes `/api/home`, catalog endpoints, free reader previews, payment pack metadata, and settings.
- Server-side public cache TTL defaults to `PUBLIC_CACHE_TTL_SECONDS=300` so normal reading bursts do not rebuild catalog payloads mid-session; admin writes still clear the cache immediately.
- MongoDB connection pooling defaults are raised and configurable:
  - `MONGODB_MAX_POOL_SIZE=100`
  - `MONGODB_MIN_POOL_SIZE=2`
  - `MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000`
- Public reader chapter-list and session endpoints avoid shipping full chapter
  bodies, reducing MongoDB payload size during sudden reader bursts.
- API rate-limit defaults are raised for 100-user bursts while remaining configurable by environment:
  - `RATE_LIMIT_PUBLIC_PER_MINUTE=30000` for cached catalog, home, public settings, and pack metadata.
  - `RATE_LIMIT_READER_PER_MINUTE=15000` for reader chapter checks and preview access.
  - Auth, upload, webhook, and payment mutation limits stay on separate tighter buckets.
- The frontend prefetches high-intent route bundles during idle time: library, book detail, reader, pricing, and login.

No finite test suite can mathematically prove every future use case forever. The gate is designed to cover the current critical Earnalism flows: browse, preview, read, account auth surfaces, payment entry, publishing pipeline safety, and production load capacity signals.
