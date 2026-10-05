# Earnalism performance budgets

Baseline revision: c33faa0b52134d74a174e4cd1f424fccd87a0b56. Audit date: 2026-10-05.

Field targets (real users, p75): LCP <= 2500 ms, INP <= 200 ms, CLS <= 0.1.
Lab shell measurements cannot establish these field targets. Field collection
must report device class, geography, sample count, and observation window.

| Scope | Budget | Enforcement / evidence |
| --- | --- | --- |
| Initial main JS | <=165000 gzip bytes | `node scripts/check_performance_budgets.mjs` after production build; measured 155583 |
| Any JS chunk | <=170000 gzip bytes | Same guard; covers optional admin/editor code too |
| Idle anonymous Home route code | No timed speculative Reader/Login/Pricing downloads | Intent-prefetch unit test and browser resource trace |
| Global hero preload | No unused retired hero art | Built HTML guard; current hero remains high priority in component |
| Desktop Home route JS, 7 seconds | <=580000 decoded resource bytes | Controlled loopback shell baseline 682502; optimized 552178 |
| Browser shell CLS | <=0.1; investigate higher | Field target independent; anonymous account redirect already above 0.1 |
| Public catalogue API | provisional warm isolated p95 <=50 ms sequential, <=1000 ms at 40-request burst | Measured 25.045 / 877.002; not a production SLO |
| Offers API | provisional isolated p95 <=20 ms | Measured 1.482; do not alter pricing or entitlement semantics |
| Protected Reader page API | provisional isolated p95 <=25 ms | Existing real Mongo/auth fixture measured 4.899 across 20 requests |
| Redis loopback GET | provisional p95 <=2 ms | Measured 0.134; this is not application cache hit-rate evidence |
| Reader first readable page / repagination / page turn | Not yet calibrated | Requires current true-pagination integration and authorized browser fixtures; no invented budget |
| Auth bootstrap / catalogue navigation | Not yet calibrated | Requires successful data-backed journeys; auth changes belong to PR517 |
| Above-fold image bytes | Not yet calibrated | Shell trace includes below-fold discovery; collect viewport-specific image resources before enforcing |
| Repeated navigation | No monotonic growth in DOM/listeners after warmup | 5 anonymous SPA cycles: nodes 671, listeners 210 each cycle |

For repeatable timings, use at least five runs with unchanged browser, device,
viewport, CPU/network settings, fixture, and build mode. Investigate a >10%
median regression on critical routes. Do not fail timing CI from one local sample.
Byte-size guards are deterministic and can be enforced now. Run the same matrix
before and after each future optimization. Do not label observer event timing as
field INP or sum overlapping coverage ranges as unique unused JavaScript bytes.

## Commands

```sh
npm run build --prefix frontend
node scripts/check_performance_budgets.mjs
node scripts/platform_performance_benchmark.mjs /tmp/earnalism-performance.json
PERF_VIEWPORT='{"width":844,"height":390}' PERF_ROUTES='["/","/reader/a-ghost-story"]' node scripts/platform_performance_benchmark.mjs /tmp/earnalism-performance-landscape.json
```

The browser harness prevents production requests and captures Chromium traces.
Its empty API responses deliberately measure anonymous route shells. They cannot
validate content rendering, full-access Reader, real catalogue cardinality,
Google sign-in, or production analytics delivery. Backend benchmarks require the
repository's disposable loopback Mongo replica set and Redis on port 27019.

Backend command (local fixture signing values only):

```sh
PYTHONPATH=. ENVIRONMENT=uat MONGODB_URL='mongodb://127.0.0.1:27018/?replicaSet=earnalism-uat-rs0' JWT_SECRET=local-performance-fixture-secret-not-production READING_PASS_TOKEN_SECRET=local-performance-fixture-lease-secret-not-production /tmp/earnalism-main-approved-integration/.venv-uat/bin/python scripts/platform_backend_benchmark.py
```
