# Clean performance candidate qualification

Baseline: `c33faa0b52134d74a174e4cd1f424fccd87a0b56`.
Runtime candidate: `edb59f2270b4a2ed3ca0eb5cb8e61651bf15620d`.
Documentation-only follow-up does not alter those runtime sources.

Three sequential main/candidate pairs used the same machine, Chromium, production
builds, 1440×900 viewport, fresh contexts, seven-second observation and harness.
Browser API shell responses were controlled empty fixtures; they measure delivery,
not data-backed catalogue performance or field CWV. Backend pairs used disposable
loopback Mongo replica set and Redis, real ASGI handlers, artifact-backed public
catalogue, identical requests, and no production traffic.

## Browser delivery

| Metric | Main runs | Candidate runs | Median delta | Percent |
| --- | --- | --- | --- | --- |
| Home requests | 34,34,34 | 24,24,24 | -10 | -29.41% |
| Home JS decoded bytes | 682491,682491,682491 | 552654,552654,552654 | -129837 | -19.02% |
| Logo bytes | 650122,650122,650122 | 15477,15477,15477 | -634645 | -97.62% |
| Home fonts bytes | 2378972,2378972,2378972 | 783968,783968,783968 | -1595004 | -67.05% |
| Library requests | 33,33,34 | 23,24,24 | -9 | -27.27% |
| Library JS decoded bytes | 682491,682491,682491 | 567993,567993,567993 | -114498 | -16.78% |
| Account CLS | .167839,.167839,.167632 | .043684,.043036,.043891 | -.124155 | -73.97% |

Byte metrics are decoded resource sizes, not compressed wire transfer. All listed
byte values were stable across three runs. Library request ranges were 33–34 and
23–24. CLS ranges were .167632–.167839 and .043036–.043891. No browser page errors
were reported in these route runs. Account measurements are anonymous redirects;
they are not proof of authenticated layout or OAuth behavior.

## Catalogue and Redis

| Redis warm concurrency | Main p95 runs (ms) | Candidate p95 runs (ms) | Median improvement |
| --- | --- | --- | --- |
| 1 | 48.232,18.465,17.208 | 5.443,5.436,5.274 | 70.56% |
| 8 | 126.073,126.883,127.614 | 32.568,31.622,31.265 | 75.08% |
| 40 | 623.758,989.395,652.541 | 179.964,183.708,178.388 | 72.42% |

Warm p50 main/candidate medians at 1/8/40: 18.465/5.436,
126.723/31.528,651.983/179.300 ms. Maximum median values:
18.465/5.436,126.883/31.622,652.680/180.143 ms.
Throughput median main/candidate: 53.56/178.43,62.65/246.68,60.90/217.55 req/s.
All requests returned success; full catalogue bytes remained 307769 in every run.
One burst/configuration/pair is diagnostic, not a production percentile SLO.

Eight cold requests rebuilt 8,8,8 times on main and 1,1,1 on candidate.
Candidate cold p95:130.610,131.596,127.321 ms; errors0 in every run.
Redis operations per candidate burst:31 GET,8 SET,2 EVAL. Native ownership tests
also cover equivalent results, invalidation during rebuild, cancellation, expiry,
outage fallback and owner-safe cleanup. No index or production Redis mutation.

## Reproduction and preserved evidence

Use `scripts/platform_performance_benchmark.mjs` with
`PERF_ROUTES='["/","/library","/account"]'`; point `PERF_BUILD_ROOT` to each
separately built baseline/candidate. Run three sequential pairs with otherwise
identical settings. Use `scripts/profile_catalogue_performance.py` under the
documented disposable UAT configuration, resolving `backend` from each checkout.
Run `PERF_REDIS_SINGLEFLIGHT_TEST=1 python3 -m pytest
backend/tests/test_catalogue_singleflight.py` against disposable Redis port27019.

Raw historical exports and separate Reader/worker history remain preserved by
`codex/performance-precleanup-snapshot`; they are deliberately not PR inputs.
This concise summary supersedes historical totals. No essential claim requires
private paths, screenshots, heap dumps or secrets.

## Runtime security observations

Native disposable signup/profile/logout endpoints: anonymous401, two sessions200,
distinct profile identities; logged-out session401 while other session200.
Four clients receive equal public catalogue representation with neither profile
ID nor balance/password fields. Authenticated catalogue responses are not public
HTTP-cacheable. Native analytics intake accepted page_view,homepage_view,
library_view,title_view and one authenticated library_view (five records).
The separate full production-build browser journey Home→Library→title forwarded
API calls to the disposable native backend. It emitted six accepted events:
one page_view per route plus exactly one homepage_view,library_view,title_view.
Hover and keyboard focus prefetch emitted no false views; guarded non-analytics
POST count0; browser errors0. Header logo retained its official accessible name.
Standalone Chromium native prefetch helper smoke: idle0,pointer1,keyboard1,
save-data0. Existing frontend tests cover focus, loading/account shell and
reduced-data behavior; this is lightweight qualification, not a full WCAG audit.

Reproduce native security intake/session checks using
`scripts/qualify_performance_security.py` with the disposable UAT variables in the
budget document. It creates and removes a uniquely named database and scoped
cache keys; never use a production database. To reproduce browser delivery, run
`PERF_UAT_API_ORIGIN=http://127.0.0.1:<disposable-api-port>
PERF_UAT_FRONTEND_ORIGIN=http://127.0.0.1:<disposable-frontend-port> node
scripts/qualify_performance_analytics.mjs` against the launcher-provided native
UAT frontend and API. This preserves the real disposable CORS path; external
requests are intercepted, non-analytics mutations are blocked, and safe GET plus
analytics traffic follows the normal loopback browser route. The operator owns
disposal of the supplied backend database/process.

Fresh validation: frontend99 suites/624 tests; catalogue/cache24 tests including
live disposable Redis; broad backend28 tests; profiler tooling9 tests. Production
build PASS; SEO172 snapshots/3647 assertions; initial main JS155716 gzip bytes
within165000 budget; syntax/compilation/diff checks PASS. No application source
changed during this qualification. No raw exports reintroduced.

Vercel Web Analytics and Speed Insights source remains unchanged. DNT/GPC policy
is unchanged and belongs to the separate privacy lane. Production CWV field
verification is deferred to platform/field follow-up, not a release claim.
