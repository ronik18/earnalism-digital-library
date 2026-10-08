# Earnalism performance audit — 2026-10-05

## Scope and readiness

Base: c33faa0b52134d74a174e4cd1f424fccd87a0b56. Local performance lane only.
PR517 owns the focused PR slot. No push, PR, deployment, production data mutation,
platform configuration change, or production load test occurred.

Two measured low-risk delivery improvements are implemented. The comprehensive
platform acceptance condition is **not complete**: authenticated browser Reader
pagination, production field metrics, worker contention, and production query
distributions remain unmeasured. Empty API shell fixtures are explicitly not
full-access or data-backed Reader performance evidence.

## Reproducibility

Production frontend build; Chromium 149.0.7827.55; 1440×900; one cold
browser context per route; 7-second observation; no CPU/network throttling;
uncompressed loopback static server. All external requests intercepted. Public
data fixtures are empty; anonymous auth returns 401. Traces referenced in the JSON
artifacts are local /tmp files. Single-sample timing differences are informational.
Deterministic byte/request improvements support the delivery changes.

Python 3.11.15 / existing UAT environment; MongoDB 8.2.7 disposable replica set on
127.0.0.1:27018; Redis 8.10.1 disposable server on 127.0.0.1:27019. The backend
benchmark uses generated data, real ASGI handlers, and dedicated database/key
namespaces. Reader API benchmark uses existing real auth/lease/Mongo fixture.

## Before/after browser scorecard

JS columns are uncompressed decoded response bytes, not gzip wire transfer.
LCP is lab observer timing, not field p75. No field INP claim.

| Route | JS bytes before → after | Requests before → after | Lab LCP ms before → after | Script ms before → after | Final CLS |
| --- | --- | --- | --- | --- | --- |
| / | 682502 → 552178 | 34 → 24 | 228 → 200 | 88.44 → 83.44 | 0.0394 |
| /library | 682502 → 567492 | 33 → 24 | 456 → 452 | 86.33 → 99.74 | 0.0396 |
| /book/a-ghost-story | 682502 → 584513 | 24 → 15 | 436 → 436 | 68.60 → 66.59 | 0.0929 |
| /reader/a-ghost-story | 682502 → 610996 | 18 → 10 | 388 → 380 | 60.14 → 54.55 | 0.0471 |
| /pricing | 682502 → 565701 | 33 → 25 | 444 → 436 | 81.65 → 77.24 | 0.0394 |
| /login | 685345 → 566182 | 24 → 18 | 452 → 436 | 84.81 → 73.10 | 0.0428 |
| /account | 712868 → 593705 | 27 → 20 | 432 → 444 | 72.42 → 73.69 | 0.1624 |
| /journal | 692805 → 562481 | 30 → 19 | 424 → 424 | 66.06 → 66.61 | 0.0989 |

Home JS: -130324 bytes (-19.1%); requests: -10 (-29.4%).
Main bundle: 551351 → 552178 raw;
155274 → 155583 gzip;
130206 → 130592 brotli.
The helper increases main JS slightly; route code deferred exceeds that overhead.
Total bundle code is not materially reduced. It is delivered when needed.
Library script timing increased in this single sample; no CPU win is claimed.
Follow-up: five interleaved cold-context pairs measured median Library LCP
492 → 488 ms and script duration 101.859 → 108.330 ms
(+6.35%, below the 10% regression investigation threshold). The earlier three-run
batch comparison showed larger regressions while machine load varied; it is not
used to establish a win. No Library latency improvement is claimed. Paired
raw results were archived outside the review scope. Reproduce route measurements
with `scripts/platform_performance_benchmark.mjs`; see the current qualification
summary for the main/candidate comparison and its limitations.
Image/lazy-load resource totals vary between runs and are not treated as a stable
latency or total-image-byte improvement. The removed retired image is a
deterministic 102973 desktop bytes / 104296 mobile bytes.

## Ranked bottlenecks and follow-up queue

Only rows 1–8 include measured costs. Other rows are audit observations or missing
measurements, not proven latency bottlenecks. Rank uses observed impact, frequency,
confidence, scope, and effort; no invented numerical precision.

| Rank | Area / cost | Consequence / frequency | Gain / risk / effort | Disposition |
| --- | --- | --- | --- | --- |
| 1 | Timed five-route imports; Home idle JS 682502 bytes | Unused downloads on every visit after 5.6s | 130324 fewer Home JS bytes; low risk; small helper | P1 DONE: intent prefetch |
| 2 | Retired global hero preload; 102973 desktop / 104296 mobile bytes | High-priority unused artwork on all routes | Exact wasted asset removed; low risk; HTML change | P1 DONE |
| 3 | Public catalogue burst p95 877.002ms, 40 concurrent ASGI calls | Material serialized catalogue overhead under burst | Gain unmeasured; needs stage profile; medium risk | P1 NEXT, catalogue owner coordination |
| 4 | Public catalogue payload 307769 bytes; p95 25.045ms sequential | Metadata serialization/network cost per list | Projection changes need consumer audit; medium effort | NEXT; no unsafe field removal |
| 5 | Account shell CLS 0.1624 | Anonymous route redirect crosses 0.1 lab target | Auth lane owns behavior; gain unmeasured | NEXT PR517 validation |
| 6 | Mobile Home estimated image RGBA footprint 50450208 bytes | Potential decoding/memory pressure | Derivatives need viewport assessment; preserve artwork | NEXT; estimate, not decoded heap measurement |
| 7 | Official lockup PNG 635 KiB source | Header/footer delivery cost | Reversible derivative possible; visual QA needed | NEXT, no brand asset change here |
| 8 | Main gzip 155583 bytes; largest optional chunk 147201 gzip | Initial parse / optional admin payload | Existing route splitting works; future dependency attribution | P2; budget added |
| 9 | Mobile Home 8 font requests | Download/render dependency | No measured font timing; Bengali quality must hold | DEFER until subset/usage trace |
| 10 | Public cache generation read plus value GET | At least two Redis operations in source path | Pipelining depends on invalidation contract | DEFER; no cache behavior change |
| 11 | First-party CWV flag gates production emission | Field evidence absent from this lane | Read deployment flag/log evidence; no new pipeline | BLOCKED field verification |
| 12 | Full-access Reader browser first page/map timing missing | Priority opening/repagination evidence gap | Requires pagination lane fixture integration | NEXT parallel profiling, no code overlap |
| 13 | Catalogue worker contention unmeasured | Foreground resource-pressure evidence gap | Needs worker fixture/metrics | NEXT worker-owned profiling |
| 14 | Retained SPA heap 3691612 → 4335060 after 5 cycles | Warmup growth; DOM/listeners stable | Longer soak needed; no leak demonstrated | DEFER; no cleanup rewrite without cause |
| 15 | API stage timings / production explain absent | Cannot attribute DB vs serialization vs cache cost | Low-overhead request-local instrumentation needs design | NEXT observability follow-up |

## Backend / Mongo / Redis / load

Endpoint timings are isolated ASGI observations. No production p95/p99 claim.
- /api/books: p50 22.067, p95 25.045, p99/max 223.027 ms; 30 calls; HTTP 200; max payload 307769 bytes.
- /api/payments/offers: p50 1.213, p95 1.482, p99/max 1.546 ms; 30 calls; HTTP 200; max payload 682 bytes.
- /api/users/me: p50 1.098, p95 1.637, p99/max 1.944 ms; 30 calls; HTTP 401; max payload 144 bytes.

Protected page API: median 4.649 ms;
p95 4.899; max 4.907;
20 calls. Guest page 4, invalid lease, revoked session, absent cookie, logout
denials verified; private no-store responses and hashes verified; no fixture
wallet debit. This is not a browser page-turn measurement.

Generated Mongo query: is_published=True, sort created_at descending, limit 500.
Without index: COLLSCAN, 1000 documents examined, 500 returned, sort.
With the **existing repository** compound index reproduced in test DB: IXSCAN,
500 keys / 500 documents examined, 500 returned. Millisecond explain timing is too
coarse here (0 vs 1 ms) to claim latency improvement. No production index added
or removed; no write amplification change. Complete production release predicate
and query distributions have not been explained.

Redis generated-key GET: p50 0.107, p95 0.134, p99 0.141 ms;
100 hits, 0 misses, TTL 60s. This is connectivity/round-trip evidence,
not application cache hit rate, stampede, or cross-replica invalidation evidence.
Public TTL in source is 300s; bounded process fallback exists. Personalized cache
policy tests pass. No cache or index implementation change.

Warm catalogue burst: 40 simultaneous requests, 45.36
requests/s, 0 errors; p50 874.971, p95 877.002,
p99 877.200 ms. ASGI bypasses TCP; no CPU/RSS resource attribution.
No analytics-intake load, full authorized mixed load, or production load.

## Reader / mobile / memory

Mobile 390×844, landscape 844×390, short-height 1280×600 anonymous Reader shells
have no horizontal overflow and no page exceptions. They contain no approved text
fixture, so central vertical scroll, exact reconstruction, page-map completion,
font-size repagination, resize cost, and hundreds-page behavior are **not verified**.
Current origin/main does not contain the separate true-pagination lane changes.
This lane deliberately does not merge that implementation for benchmarking.

Five SPA navigation cycles after forced GC: retained heap
3691612 → 3895360 → 4299152 → 4272704 → 4335060 bytes.
DOM nodes 671 and JS listeners 210 remain constant. No monotonic DOM/listener leak
observed; retained heap warms and slightly fluctuates. This does not establish
long-running full Reader/content cache stability. Natural image width×height×4 is
only an estimated RGBA footprint, not actual browser decoded allocation.

## Analytics and platform

First-party and Vercel analytics remain in source. Loopback harness intercepts
external requests, so Vercel production overhead and CWV delivery are **unverified**.
Custom CWV collection is gated by REACT_APP_PERF_METRICS_ENABLED; actual deployed
value is unknown. Observers currently emit repeated LCP/CLS updates when enabled;
don't introduce another pipeline or change analytics semantics from shell evidence.

No Vercel/Railway authenticated metrics, resource pressure, regions, connection
limits, field sample window, or production compression/cache headers inspected.
No production configuration change. Dedicated platform access is needed for
those read-only observations; it is not required for the local byte reductions.

## Area scorecard

GREEN here means only the named local verification, not platform-wide acceptance.
YELLOW indicates partial evidence; RED identifies an observed target miss.

| Area | Status | Evidence / limitation |
| --- | --- | --- |
| Homepage | GREEN (delivery only) | JS/request reduction; no field CWV |
| Catalogue | YELLOW | Shell and warm ASGI; high burst latency |
| Detail | YELLOW | Anonymous shell only |
| Reader | YELLOW | Protected API verified; browser pagination missing |
| Commerce | YELLOW | Offer handler and frontend tests; no checkout |
| Auth | YELLOW | Anonymous shell/Reader auth fixture; PR517 independent |
| API | YELLOW | Selected routes; stage timings absent |
| MongoDB | YELLOW | Existing-index synthetic explain; real distribution absent |
| Redis | YELLOW | Round trip and policy tests; app hit rate absent |
| Images | YELLOW | Retired preload removed; footprint follow-up |
| Fonts | YELLOW | Request count only; Bengali subset deferred |
| Bundles | GREEN (budget only) | Deterministic guard passes |
| Memory | YELLOW | Five empty-data SPA cycles only |
| Worker | YELLOW | No throughput/contention measurement |
| Analytics overhead | YELLOW | Existing source/tests; production delivery absent |

## Validation and decisions

- Frontend full suite: 622 passed / 98 suites after updating the obsolete global
  preload assertion to verify retained artwork and current high-priority hero.
- Selected backend suite: 121 passed / 1 failed. Identical failure on clean main:
  test_api_books_uses_the_authoritative_controlled_public_query expects an older
  catalogue allowlist. No backend source changed and no catalogue test weakened.
- Existing real Mongo Reader benchmark: 1 passed; 20 protected page measurements.
- Build: PASS; static SEO: 172 snapshots, 3647 assertions, 0 failures.
- Budget script, JS syntax, Python compilation: PASS.
- Broad local regression: 132 passed, 11 failed, 4 skipped; the same totals and
  failing test names reproduced on an untouched current-main snapshot. The
  failures concern public API response-shape/index/cache checks, with reads
  guarded against mutations and production load. No protected CI run or green
  regression claim. No production deployment or activation.

DONE NOW: code-only intent prefetch; retire unused global hero preloads; capture
browser traces; byte budgets and local guardrail. No latency/field target claimed.
NEXT HIGH-ROI: catalogue serialization burst profiling; viewport artwork
derivatives; true-pagination fixtures and full Reader instrumentation; authenticated
production CWV/platform read-only evidence.
DEFER: extra Mongo indexes, authorization caching, Bengali font subsetting,
worker concurrency increases, analytics batching, and blanket React memoization.
BLOCKED: focused PR slot held by PR517. Keep commits local; Integration Lane
refreshes and reviews them after the slot clears. Comprehensive acceptance remains
open for the explicitly missing measurements above.
