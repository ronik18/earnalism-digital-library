# Disposable worker/foreground contention

Scope: LOCAL ONLY. PR517 remains parked; no remote write, merge, deployment,
production switch, customer mutation or publication was performed.

Worker source was read-only at `27cd849add22aa87511b14337794f07f0ca50681`.
`scripts/profile_worker_contention.py` uses actual worker queue, discovery,
package validation and Mongo processing, with the final adapter restricted to
unpublished synthetic drafts in a UUID-named disposable database. Foreground
requests execute the actual backend with real disposable signup/device/session/
lease and Mongo/Redis. The synthetic Reader book authority is explicitly local;
this does not prove publication rights or production readiness.

Three repetitions alternate forward/reverse mode order. Each mode/repetition
has 40 bursts of eight foreground requests, two per route, separated by 30ms.
All 3,840 responses were HTTP200. Genuine session end/start between samples
keeps leases current; an earlier expired-lease run is excluded, not hidden as
an application performance defect.

Median of three per-run p95 values (ms):

| Mode | Catalogue | Detail | Authorized Reader | Analytics | Draft jobs/run |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF | 30.589 | 31.368 | 35.725 | 54.122 | 0 |
| ON1 | 25.958 | 24.574 | 28.365 | 38.484 | 3 |
| Canary, concurrency1/batch2 | 26.057 | 25.443 | 30.032 | 29.329 | 6 |
| Stress, concurrency4/batch8 | 25.959 | 24.682 | 28.098 | 52.344 | 16 |

Foreground throughput ranges128.96–133.58rps, including intentional pauses.
Aggregate Mongo command p95 ranges4.38–6.213ms, Redis command p95
6.04–6.241ms. Command timings overlap and are NOT exclusive request-stage time.
Foreground process peak RSS108,396,544B; child peak RSS58,572,800–59,179,008B.
Worker CPU56.580–133.872ms/sample; foreground CPU1,121.952–1,172.015ms/sample.
Queue depth at sample end was0 in all modes. ON1 draft throughput1.223–1.233/s,
canary2.450–2.494/s, stress6.421–6.516/s. Discovery interval is shortened to1s
for this bounded local test; these are not proposed production settings.

No consistent material p95 degradation was demonstrated. Do not retain a
speculative adaptive-backpressure change or interpret lower worker-on numbers
as a causal performance improvement. Existing DB/memory/queue guardrails remain
unchanged. This is not saturation or realistic external-acquisition evidence:
there are zero source network calls, no rate-budget exercise, no production
publication, and no forced-backpressure trigger test.

Raw per-run p50/p95/p99/max, command counts/timing, CPU/RSS and queue states:
`internal/earnalism_intelligence/performance-worker-contention-20261005.json`.
Reproduce using explicit
loopback replica-set Mongo27018, disposable Redis27019 and the named read-only
worker worktree. The harness refuses non-UAT/non-loopback Mongo configurations.

Next unfinished local proof: genuine backend-to-browser multichunk Reader and
broader memory soak. Existing mock browser timing is not substituted for it.

Fresh validation after this harness addition: frontend99 suites/624 tests;
Redis ownership9; disposable repository gate backend14/54/452 tests, real
Mongo Reader1 test, catalogue71 tests+1 existing skip+55 subtests, proxy15
Python/12 Node tests, frontend contracts8 suites/50 tests, broad regression15
suites/143 tests with2 suites/4 tests explicitly skipped. Totals overlap and
are not summed. Native UAT build and signed journey smoke passed. Static SEO
172 snapshots/3,647 assertions/0 failures; main JS gzip155,886B within165,000B.
Python compilation, JSON parsing and diff checks passed. Fresh gate log:
`/tmp/earnalism-performance-worker-fresh-gate.log`.

Existing canonical master ledger already classifies517 as BLOCKED_HUMAN,
not engineering failure. Observed programme counts are DONE5, READY_FOR_PR5,
BLOCKED_HUMAN3, BLOCKED_POLICY4, total17. Its unexpected untracked evidence
is preserved; this local checkpoint does not create a competing master ledger
or declare a whole programme task complete.
