# Reader final performance acceptance — 2026-10-05

**READER PERFORMANCE FOLLOW-UP REQUIRED**. No application source changes. No push, PR, merge, deployment or Google retry.

## Exact-head environment

Reader `0a242584c438a0da8160ea502e421161b039d0fe`; backend `f5a693771e2b76bcaca1a867d58dfc3bc50874ef`. Chromium149.0.7827.55; MongoDB8.2.7 replica set on27018 and Redis8.10.1 on26594; isolated backend18594. Repository-supported UAT, synthetic signup/wallet, normal session/consent/lease/protected handlers and repository-controlled Dracula. No API mocks in the90-load benchmark. Owned SVG/media mock is separately labeled layout-only.

## Cold / warm distributions

All90 samples on exact Reader head. First readable measured from document-start T0 to two animation frames after DOM content ready with opening absent.10 cold(new browser contexts) and20 warm(same context/reloads) each; backend caches not flushed.5500ms pacing excluded from timings. Every load traced with script stacks, adding profiling overhead. Automated consent is included where required. Thin shell = **READER_ENGINE_PATH**, not full app startup. Conservative upper-observed quantile `sorted[ceil((n-1)*p)]`; no p99.

|Viewport|Kind|n|Median ms|p90 ms|p95 ms|Max ms|
|---|---|---:|---:|---:|---:|---:|
|1440|cold|10|492.2|516.9|516.9|516.9|
|1440|warm|20|431.9|620.9|670.6|670.6|
|390|cold|10|510.5|554.2|554.2|554.2|
|390|warm|20|389.8|527.0|1157.5|1157.5|
|844|cold|10|524.5|546.5|546.5|546.5|
|844|warm|20|455.3|522.7|565.0|565.0|

## Mobile cold tail

**MOBILE_COLD_TAIL_NOT_REPRODUCED**: cold max554.2ms versus historical970ms. No new cold sample approached the old tail. Every sample contains stage/network/CPU/GC summaries. Portrait warm outlier1157.5ms remains included: manifest response356ms, then485ms manifest-ready→lease-ready, mostly before lease request; lease endpoint24ms. Pre-request automation/consent scheduling is not attributed to Reader layout. Forcedlayout30.563ms; no>50ms main task; MinorGC2.037ms. The untraced historical and traced current medians are not a matched regression experiment.

## Stage timings

Per-load complete numeric marks in `genuine-stack.json`; cumulative document-relative medians below. Public manifest may precede lease. Current/background pagination hooks run concurrently: T10 is first hook result, **not** final current-page commit. T11 is canonical visible content ready; separate primary paginator durations are43.3/50.0/81.2ms median. T14 may precede T13. Fonts ready precedes existing80ms layout-stabilization wait.

|Stage (ms from T0)|Desktop|Portrait|Landscape|
|---|---:|---:|---:|
|Book Awakening start|21.3|21.6|21.6|
|Auth|31.9|33.1|31.9|
|Lease|164.7|155.4|159.4|
|Manifest|55.1|55.2|54.4|
|Protected fetch start|167.1|157.8|161.8|
|All authorized chunks received|263.0|242.7|252.9|
|Hashes verified|263.0|242.8|253.0|
|Chapter assembled|264.5|244.3|254.5|
|Fonts ready|292.5|268.4|279.2|
|Pagination started|375.5|351.7|363.1|
|First pagination-hook result|384.0|360.1|371.7|
|CONTENT_READY|423.0|406.9|450.7|
|Book Awakening absent|423.0|406.9|450.7|
|FIRST_READABLE|452.9|426.4|467.7|
|Final map ready|425.5|409.7|456.3|

Book Awakening overlaps network/pagination; its start/end are not added to costs. DOM removal observed at T12, not a fabricated CSS exit duration.

## Layout / CPU

Forced = complete trace Layout with explicit JS stack or nested entirely within same-thread FunctionCall/EvaluateScript/RunMicrotasks. This is synchronous script-attributed reflow, not every browser layout. Script is Performance.getMetrics delta; layout/style/paint separate trace durations. Top-level GC episodes and observed nested event names are retained; never sum nested events as exclusive time.

|Phase|Forced count|Forced ms|Longest layout ms|Script ms|Layout/style ms|Paint ms|
|---|---:|---:|---:|---:|---|---:|
|Initial1440(30-sample medians)|512|27.90|6.27|43.05|33.06/23.22|4.46|
|Initial390(30-sample medians)|612|30.54|6.01|44.90|34.56/23.94|3.64|
|Initial844(30-sample medians)|842|40.13|5.54|55.34|46.09/29.91|3.95|
|desktop-to-portrait|610|25.86|5.54|24.52|31.67/18.69|2.06|
|portrait-to-landscape|838|35.57|5.14|32.78|41.24/23.63|1.15|
|text-size-change|885|39.51|4.94|35.35|39.79/20.91|0.82|
|Media initial+three-page traversal|21|6.94|9.99|110.11|29.20/31.17|10.91|

No>50ms main task in90 loads or traced resize/text/media phases. Largest main task across90 loads45.317ms. Resize paginator58.1/84.9ms; increased text81.9ms. Forced-layout count is high because of rendered block fitting, but aggregate cost is bounded in this local fixture; no severe P0 established.

## Media geometry

Six cold-cache supported figure/caption layouts: exact captions81 chars reconstructed,3 images in order, no overflow. Intrinsic image320×640. Empty measurement clones after completion are normal; container widths below are the active measured width, final figure rectangle rounds fractionally. Hidden source parent is wider; algorithm copies effective viewport width into the measurement surface.

|Viewport|Client/scroll W|Clone W|Final figure W|Client/scroll H|
|---|---|---:|---:|---|
|1440×900|595/595|595|595.12|460/460|
|1280×720|541/541|541|541.41|285/285|
|768×1024|358/358|358|358.00|590/590|
|390×844|350/350|350|350.00|295/295|
|844×390|438/438|438|438.00|148/148|
|1280×600|541/541|541|541.41|165/165|

## Native zoom

Prior exact-head100→125→150→100 text/media timing remains preserved in `reader-native-zoom-closeout-20261005.json`. Fresh expanded mixed prose/image-only/adjacent-page proof is separate:

|Zoom|CSS viewport|Client/scroll W|Client/scroll H|Pages|Pagination ms|Exact chars|
|---|---|---|---|---:|---:|---|
|100|960×704|540/540|296/296|33|43.2|11152/11152|
|125|768×563|358/358|116/116|81|58.4|11152/11152|

All pages visited through real selector, one `media:0` occurrence and stable revision. Adjacent prose fits. Native toolbar125% confirmed; no CSS zoom. Chrome quit once, reopened normally. Mac locked before fresh150 and return100, so expanded roundtrip **BLOCKED_HUMAN — UNLOCK MAC AND LEAVE CHROME OPEN**. Prior native proof is not falsely relabeled this fresh expanded acceptance. Page snapshots wait300ms to measure after intentional280ms transitions; immediate transient transforms can temporarily enlarge numeric scrollWidth.

## Remaining layout follow-up

Independent settled prose desktop→390×844 reproduction on unchanged source: **clientWidth350/scrollWidth353**, height295/295. Computed transform identity; animation finished at280ms. This reproduces concurrent exact-head evidence that removing animation in an ephemeral diagnostic eliminates retained overflow. Numeric horizontal resize criterion fails at2px tolerance even though media passes. No source fix is made because this task permits application changes only for severe P0 and this small layout defect is not one. Follow-up: remove retained finished-animation overflow without clipping prose or changing pagination/entitlement.

## Page turns

40 exact-head turns each; intentional280ms effect excluded.

|Viewport|p50 ms|p95 ms|Max ms|
|---|---:|---:|---:|
|1440×900|94.84|96.08|96.42|
|390×844|94.19|96.83|97.43|
|844×390|94.56|96.35|96.64|

Prior p95~95–96ms: no material page-turn regression.

## Budget / full app / memory

Existing Reader first-readable/page-turn/repagination budgets are **not calibrated**. No new pass thresholds invented. Fieldp75LCP/INP/CLS and isolated untraced API budgets are not inferred from this traced Reader shell. Full app APP_START_TO_READER_READABLE and full-app READER_ROUTE_TO_READABLE = **NOT_MEASURED** (optional). Reader engine is measured above.

Preserved15-cycle genuine lifecycle and matched-control evidence; no repeat handle investigation/soak. HANDLE_RETENTION=RESOLVED; MEMORY=ACCEPTED_FOR_TESTED_PATH. Zero post-exit cache entries, flat nodes/listeners, no growing Reader-specific detached family. Residual18–19KiB/cycle does not establish leakage or universal leak freedom.

## Validation / Git / ledger

Harness tests5 passed; syntax and diff checks pass. Existing exact Reader validation unchanged:10 suites137; full102 suites689; backend372; buildPASS; SEO172/3647; regression143/0/4. Not rerun this task because no source changes. Disposable services stopped; no production mutation. Foreign concurrent exact-head acceptance documentation and dependency symlinks preserved and excluded from this commit. Updated master-ledger copy on performance lane keeps original external preservation artifact immutable.

REDIS=DONE; WORKER=DONE_FOR_TESTED_LOCAL_ENVELOPE; CLS=DONE_LOCALLY; MEDIA=DONE_LOCALLY; CANCELLATION=PASS; MULTI_CHAPTER=PASS; MEMORY=ACCEPTED_FOR_TESTED_PATH; READER_E2E=FOLLOW_UP (3px settled horizontal resize extent); NATIVE_ZOOM=BLOCKED_HUMAN (expanded150/return100); PRODUCTION_CWV=UNVERIFIED.

Next exact local prompt: `Fix the retained finished-animation horizontal scroll extent after portrait resize without clipping text; preserve Reader0a242584 ancestry and pagination/security invariants. Then finish native mixed-content150→100 after Mac unlock. No push, PR, merge or deployment.`
