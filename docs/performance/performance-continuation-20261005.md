# Performance continuation — local checkpoint, 2026-10-05

## Executive result

Preserved c5306d0299b5bc71cf07e9be94d38e0b3e5778cd. Base remains
c33faa0b52134d74a174e4cd1f424fccd87a0b56. PR517 still owns the focused slot.
No push, competing PR, deployment, production load, or canonical/dirty checkout edit.
This is **not** comprehensive platform performance acceptance.

Three additional measured low-risk changes: catalogue route serialization,
existing official logo derivatives, and lossless Latin font WOFF2 delivery.
Original artwork and TTFs remain unchanged; Bengali font declarations unchanged.

## Catalogue concurrency and attribution

Real ASGI handler, disposable Mongo replica set, existing repository-approved
52-title artifact catalogue. Identity encoding excludes gzip from this curve.
One warm burst at each concurrency; these are diagnostic sample percentiles,
not steady-state or production SLOs. Final standard-response comparison uses
the identical current builder through FastAPI's original response path.

| Concurrency | Local baseline p95 ms | Optimized p50 / p95 / p99 ms | Optimized req/s | CPU ms/burst |
| --- | ---: | ---: | ---: | ---: |
| 1 | 17.685 | 3.629 / 3.629 / 3.629 | 259.7 | 3.6 |
| 2 | 34.507 | 5.910 / 5.960 / 5.960 | 323.7 | 5.9 |
| 4 | 67.271 | 10.962 / 11.041 / 11.041 | 351.6 | 11.1 |
| 8 | 129.294 | 22.072 / 22.242 / 22.242 | 350.6 | 22.6 |
| 16 | 272.323 | 42.941 / 43.415 / 43.415 | 360.2 | 44.2 |
| 24 | 440.209 | 62.861 / 63.740 / 63.896 | 367.3 | 65.1 |
| 32 | 517.429 | 83.552 / 84.626 / 84.788 | 369.4 | 86.3 |
| 40 | 575.974 | 103.199 / 104.175 / 104.445 | 374.3 | 106.6 |

Redis p95 baseline → optimized, concurrency 1/2/4/8/16/24/32/40:
17.089→4.867; 32.422→8.204; 63.585→15.109; 125.395→29.437;
282.789→60.149; 371.990→89.487; 529.890→149.745; 649.181→145.519 ms.
Full p50/p99/CPU/cache-stage/RSS data are in the continuation JSON.

Warm local calls issue **zero Mongo queries**. FastAPI's recursive primitive
encoding cost about 12 ms/request and rendering about 2 ms/request in the initial
profile. CPU time approximately equals burst wall time: event-loop CPU contention,
not warm Mongo pool acquisition, explains this isolated curve. Cache GET wall
time under Redis includes scheduling behind that CPU; do not label it wire RTT.
Optimized maximum loop probe delay at concurrency40: local91.4 / Redis96.9ms.
RSS high-water140.6MB; not a per-request memory allocation measurement.

The narrow HTTP wrapper calls the unchanged rights/publication builder and
serializes its public JSON-shaped projection once. Non-JSON leaves retain normal
FastAPI conversion; unsupported values/nonfinite numbers fail rather than being
stringified. The existing list builder and OpenAPI operation identity remain.
No fields, cache TTL, filters, auth, rights, or release semantics changed.

## Catalogue payload / client usage / scale

307769 bytes before and after. Standard encoding equality is asserted against
the same result; cross-process updated_at values can differ, so cross-run digest
equality is not an acceptance criterion. Gzip about35KB, content-dependent.

Largest measured field contributions (key/wrapper overhead included):
chapters167065B; text_license13140; description11269; learnings9214;
benefits8491; about_author8203; short_description7579; back_cover_image_url6273;
who_for6189; cover_image_url6041.

Library, libraryCatalog, homeCuration, BookCard, cover and release helpers consume
identity/title/author/language/category, short_description, estimated_reading_time,
cover aliases/candidates/verification flags, publication/Reader/audio decisions and
routes. Detail-only editorial fields and chapter data dominate excess list bytes.
Nested release helpers and other clients require a complete contract audit before
removing fields; no summary endpoint or pagination was introduced speculatively.

Synthetic scale repeats the existing distribution (not actual new titles):
52/75/100/150/200/500 titles produce307769/392991/589007/883430/1175260/2913890B.
Original recursive serialization CPU11.5/14.3/22.0/32.7/44.2/109.9ms;
JSON rendering2.1/2.8/4.2/6.7/9.0/21.9ms. At500, a separate compatible summary
contract is high-ROI. Current endpoint is bounded to500 DB records plus controlled
artifact reconciliation; this is not an unbounded future-catalogue claim.

## Mongo

Exact current controlled query/projection/sort explained on1000 synthetic rows.
These deliberately have no approved slugs: nReturned0; keys examined0;
documents examined1000 with and without existing indexes. The simple historical
is_published index result did **not** generalize to this complete release query.
No index added to product or production. A useful index decision still needs
approved-document distributions, production-shaped explain and write/storage cost.
The cache-hit burst has no Mongo acquisition, so no pool adjustment is justified.

## Redis

Five actual cache requests: one miss/rebuild, four hits;11GETs and1SETEX.
Warm request uses generation GET plus payload GET. Stored blob38409B; observed
jittered TTL327seconds for configured300seconds. Decode roughly0.8–1.3ms.
Invalidation followed by8 concurrent requests caused8Mongo queries and8rebuilds:
a real cold-stampede observation. No invalidation or locking policy changed.
Need bounded single-flight design with generation fencing in a later focused fix.
This fixture's80% hit ratio is not an application/production hit rate.

## Images

Header master650122B → existing320AVIF15477B (-97.62%); desktop rendered size
remains320×96. Canonical master2400×720 retained; derivative encoded320×96
reduces source RGBA estimate6912000→122880B. Density-corrected naturalWidth is
not decoded buffer size. Existing640 derivatives support DPR2; fallback retained.
Desktop/mobile screenshots and browser overflow checks passed locally.
No canonical owner cover bytes or catalogue exposure changed. Data-backed cover
decode/priority audit remains incomplete; empty shelves cannot prove it.

## Fonts

Eight actual Home requests2378972B →783968B (-67.05%); count remains8.
Latin families/weights/styles unchanged. No subsetting. Derivative script verifies
every glyph outline, cmap, horizontal metrics, GSUB/GPOS/GDEF/name/OS2/fvar when
present against original bytes; all9Latin files pass. Original TTFs retained.
Bengali TTFs unchanged. No new dependency in frontend or runtime; fonttools4.66.1
was used only in a disposable asset-conversion environment. Asset/source hashes
and route-by-route face/byte records are persisted in the JSON.

## Reader

Existing actual authenticated Mongo/lease benchmark:20page fetches,
median4.509ms/p955.099/max5.375;1testPASS, protected denial and no-debit checks.
Separate actual-source browser harness compiles each selected branch read-only,
with the retained **owned mock** API and consistent current3-page preview policy.
It is NOT an authenticated backend→browser end-to-end proof.

| Development fixture | 1440×900 | 390×844 | 844×390 |
| --- | ---: | ---: | ---: |
| Main first readable ms | 271.7 | 238.0 | 175.0 |
| Pagination branch first readable ms | 405.8 | 409.3 | 403.7 |
| Pagination branch turn p50/p95 ms | 63.2/65.6 | 63.4/65.7 | 63.8/77.1 |

Turn timing includes Playwright overhead plus two animation frames, not isolated
INP. Branch source bf0160975c55f18499ae63b585aa78fe9a25a690; main lacks that
pagination algorithm, so first-page timing differences are not optimization deltas.
64/136/264 visual-page metadata rows; only1mounted text page.102turns per viewport,
three post-GC snapshots; final corrected-fixture resize checksPASS all3.
Stable229listeners; retained heaps roughly7–8MB. No long leak-free claim.
The early fixture's old2-page preview boundary caused invalid comparisons/resize
failure; correcting only that mock to3 resolved it without changing either Reader.
Full leave/reenter, chapter switching, zoom soak and browser real-lease integration
remain open. No pagination code copied or changed.

## Account CLS / Web Vitals / worker

Anonymous Account CLS0.1623 remains. Dominant0.1227 shift is footer movement
during auth-route resolution; body startup shift0.0389 and font/header shifts are
smaller. Auth state-machine and placeholder changes deferred to PR517 integration.
Home lab CLS0.0392, Library0.0394; no field p75/INP claim.
First-party CWV production emission still needs enabled-build flag and correlated
intake/storage/dashboard readback. No additional analytics pipeline/config change.
Worker foreground OFF/ON and adaptive backpressure remain **unmeasured**; source
inspection is not a contention benchmark. Queue/worker changes were not imported.

## Correctness and guards

Frontend98suites/623PASS; selected backend127PASS; Reader Mongo1PASS. BuildPASS;
SEO172snapshots/3647assertionsPASS. Main gzip155691B against165000B budget.
New lossless Latin WOFF2 total845252B against1MB budget; primitive conversion/fail-closed/gzip/
public-vs-identified cache regression tests added. Final totals recorded in commit
checkpoint. Prior broad regression132PASS/11baseline failures/4skips was not rerun
as production traffic; no new whole-platform regression PASS claim.

## Next integration action

Keep local whilePR517owns slot. Complete worker/content/browser-field profiling
as separate bounded experiments; after slot frees, refresh against current main,
run coherent isolated exact-head regression and independent review. No deployment.
