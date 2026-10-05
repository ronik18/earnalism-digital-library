# Reader genuine end-to-end performance — 2026-10-05

## Result
READER PERFORMANCE FOLLOW-UP REQUIRED. Fresh native 125%/150% acceptance remains blocked by locked Mac. No production mutation, push, PR, merge or deployment.

## Memory reconciliation
The two Locator corrections are identical. Canonical profiler retained; unique memory scripts/tests/evidence preserved in 20934fb0dba62b5431c5ed1af6d11b8125b08752. Prior large DOM/listener growth was benchmark ElementHandle retention, not established Reader leakage. Main 15-cycle control-adjusted heap slope 19.02 KiB/cycle; final-source cache probe 18.15 KiB/cycle. No growing nodes/listeners or detached family. One detached native family also exists in control before Reader mounts. Actual weakly observed layout caches have zero entries after exit/GC. This bounded test does not establish universal leak freedom.

## Genuine environment / authorization
Repository disposable Mongo replica set, Redis, backend; actual AuthProvider signup/session, wallet consent/start lease, protected API, normal exit/settlement. Thin route shell rather than full application startup bundle. Preview fetches only chunks 1–3, unauthorized fetches zero. Separate deliberate protected page4 denial probe returns401. Full lease uses normal API and verifies hashes/source assembly. No raw heap, credentials or auth codes stored. Failed unpaced attempts hit real429/409; no limits weakened. Successful series uses paced requests and normal settlement.

## Samples
10 cold +20 warm loads each; 100 turns each. Existing280ms visual animation is separate from input→DOM change+two frames timing; pacing excluded. Large series ran media geometry correction before final selector correction. Final-source stage/cache/media and final validation are separate evidence, not falsely relabelled exact-head90-load results.

|Viewport|Cold median/p95|max|Warm median/p95/max|Pages|Client/scroll|
|---|---|---|---|---|---|
|1440×900|462.5/481ms|481ms|443/460/460ms|51|460/460|
|390×844|460.5/970ms|970ms|408/469/469ms|151|286/286|
|844×390|470.5/485ms|485ms|410/459/459ms|381|148/148|

Page-turn p50/p95/p99/max(ms): desktop93.89/95.49/104.16/104.16; portrait93.21/96.04/96.92/96.92; landscape93.60/95.82/97.53/97.53. No mounted-page duplication or overflow.

## Chapter/cancellation / resize
15 A→B→A cycles. Controlled delay buffers actual authorized response; three requests aborted, zero completed/stale responses applied after exit. 15 resize/text samples: requested absolute chapter coordinates6010/6409 remain within every generated [start,end) range. Observed128.7–189.9ms includes120ms observation wait. Structural figure anchor+Page2 selector preserved desktop→portrait→landscape→desktop. Native100% client443/scroll443; fresh125/150 NOT_TESTED, Mac locked. No CSS simulation substituted.

## Supported media
Cold clone decoding defect confirmed in repository-owned synthetic supported figure fixture, not a demonstrated shipped edition:460/1472, while warmcache460/460. Intrinsic geometry copied/reserved for measurement clone; source bytes unchanged. Selector now compares chunk+offset+revision. Three-page source geometry320×640. Client/scroll:1440×900460/460;1280×720285/285;768×1024575/575;390×844295/295;844×390148/148;1280×600165/165. All six no overflow, caption retained and aspect ratio preserved.

## Stage/CPU/network
Final-source desktop T0 document-start (not click). Auth75.1ms, public manifest92.3ms, lease170.6ms, fetchstart173.4ms, received274ms, verified274.1ms, assembled275.8ms, fonts310.6ms, paginationstart394.9ms, readyset403.6ms, DOMready/openingremoved426.7ms, mapcomplete432.3ms, first readable443.9ms. Public metadata may resolve before lease; marks are concurrent, not forced sequential.
Initial script77.465ms/layout38.683ms;20turn trace script141.526ms/layout23.263ms;resize script53.502ms/layout83.155ms. Maximum captured complete trace event37.001/7.038/12.6ms respectively; no captured >50ms event. Forced-layout count NOT_MEASURED. Resize1972 layouts is the measured hotspot; no speculative optimization. Current/background cache sizes1/1. Protected responses private,no-store; public previews immutable max-age300.

## Validation / boundaries
Focused10 suites137; full frontend102 suites689; backend372; buildPASS; SEO172/3647; diffPASS. Fresh disposable broad regression:15 suites passed,143 tests passed,0 failed,4 unchanged PR-mode skips. Nativezoom is remaining human gate. Google#517 remains parked, no OAuth retry. Preserve independent branches and focused-PR policy.

## Replay
Use scripts/profile_reader_completion.mjs with explicit PERF_READER_WORKTREE, ENVIRONMENT=uat, UAT_BASE_URL and UAT_API_BASE_URL pointing to repository-owned disposable backend. It checks PID/worktree/port before fixture writes. Browser outputs sanitized metrics; heap snapshots remain in-memory only. Do not run on production.
