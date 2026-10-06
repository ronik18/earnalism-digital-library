# Performance follow-up — local, not deployed

Base: `c33faa0b52134d74a174e4cd1f424fccd87a0b56`. Branch: `codex/platform-performance-optimization`. PR517 remains the only open focused PR. Previous five commits are preserved. No production variables, indexes, rights, payments, auth or release state changed.

## Retained improvements

| Controlled observation | Before | After | Scope |
| --- | ---: | ---: | --- |
| Cold Redis catalogue rebuilds, 8 callers | 8 | 1 | Real disposable Redis/Mongo, actual handler |
| Catalogue full / opt-in Library JSON | 307769 B | 149975 B | 52 existing repository-backed public projections; -51.3% |
| Catalogue gzip | 35167 B | 18603 B | Same projection family; -47.1% |
| Account CLS, matched build with/without reservation | 0.167839 | 0.043684 | Anonymous lab shell; not field p75 |
| Home initial JS, earlier paired evidence | 682502 B | 552178 B | Preserved earlier delivery change |
| Home requests, earlier evidence | 34 | 24 | No analytics disabled |
| Logo response | 650122 B | 15477 B | Existing derivative, unchanged rendered dimensions/master |
| Home font responses | 2378972 B | 783968 B | Lossless Latin derivatives; Bengali unchanged |

Redis cold bursts at concurrency2/4/8/16/32 each made one Mongo query and one rebuild, with zero errors. p95ms:109.730/116.800/125.344/154.714/217.197. GET counts7/15/31/63/127; ownership SET attempts2/4/8/16/32; two Lua operations each (one atomic publish and one owner-safe release). These are single local bursts, not production SLO percentiles.

The cache key retains the existing truth/filter bindings and public generation. Redis lock TTL10s, maximum acquisition wait12s, bounded polling10–100ms. Redis socket timeouts remain repository-configured. Atomic publication checks BOTH captured generation and ownership; an invalidation/expired owner cannot write an older fill into a new generation. Builder errors propagate, cancellation releases ownership, Redis outage returns an uncached authoritative rebuild, and worker death recovers through TTL. Wait exhaustion also uses an authoritative uncached build; strict single-flight is not promised during outages or expired ownership.

## Library contract audit

`/api/books` default and `view=full` retain the complete existing public payload. Only the Library opts into `view=library-v1`; Book detail/Reader/other callers are unchanged. Unknown views return422.

LIST_REQUIRED: identity/title/title_en/author; short_description; category/category_slug; language/language_code/lang/locale; estimated_reading_time/word_count; timestamps used for ordering; publication/access/Reader/preview route flags; all cover candidate/status/URL metadata; all audio release/QA/disabled/asset bindings; attribution/source_note/rights_note/text_license. All these fields are preserved verbatim. The chapter subset retains id/title/is_preview/chapter_number: the real preview CTA requires explicit id+is_preview, so dropping chapters completely would be incorrect.

DETAIL_ONLY (omitted solely in the opt-in view): description/about_author/learnings/benefits; other chapter fields such as hashes, transport metadata and detail descriptions. UNKNOWN: every other field is retained, not optimistically removed. No additional INTERNAL fields are exposed; the original rights-filtered builder is still the sole input.

Tests compare every retained field and chapter preview identity without mutating the full projection. Rendered BookCard markup, language/sort/presentation/audio decisions match for the controlled fixture. Anonymous/authenticated gzip/cache boundaries pass on both views. Summary Redis p50/p95ms at1/8/40 were4.453/4.453,24.816/25.017,147.180/148.494. Timing runs include host variance; payload reduction is the primary demonstrated win, not an asserted steady-state API SLO.

## Account

Only the shared main container on `/account` reserves80vh, matching the existing auth-shell height. No authentication, redirects, provider initialization, cookies, requests or PR517 behavior changed. Same compiled build with reservation disabled gave CLS0.167839; enabled0.043684. Earlier separate run0.1623 is historical, not the matched control. Reproduce using the included browser harness on separately built main and candidate routes; no private screenshot is required to review this claim.

## Fresh correctness

Complete frontend:99 suites/624 tests pass. Selected backend:128 tests pass. Redis ownership suite:9 pass (explicit disposable loopback Redis), covering 2/4/8/16/32 cold callers across generations, generation-change rejection, exception cleanup, outage fallback, owner-safe release/expiry recovery and cancellation.

Fresh repository disposable gate: regression15 suites/143 tests pass,2 suites/4 tests existing skipped. Additional overlapping gates: backend14/54/452 tests; real-Mongo Reader1 test; catalogue71 tests+1 existing skip+55 subtests; proxy15 Python tests+12 Node tests; frontend contracts8 suites/50 tests; signed journey smoke PASS. Totals overlap and are not summed as unique coverage. Authenticated Reader response p95 observed4.917ms over20 requests; this is ASGI/Mongo, not browser paint.

Historical production build and SEO172 snapshots/3647 assertions passed. Main gzip155886B within165000B; largest chunk budget170000B; retained Latin WOFF2 budget passed. Compilation, JS syntax and diff checks passed. Reproduce with the documented build, budget and repository regression commands. Current exact-head qualification supersedes these historical totals; archived local logs are not review prerequisites.

## Still not established

Reader production-mode standalone benchmark on the separate, unchanged branch `bf0160975c55f18499ae63b585aa78fe9a25a690`:200 turns at each1440×900/390×844/844×390. Browser input-to-second-frame p50/p95/p99ms:48.1/49.4/49.7;48.1/49.3/49.7;48.0/49.2/49.6. This is event/DOM/frame timing, not GPU presentation or field INP. Resize PASS, mounted pages1, errors0. Five actual SPA dispose/reentry cycles retained32 DOM nodes and169 listeners at every checkpoint. Heap ranges4.53–4.98MB/4.57–5.10MB/4.56–5.03MB: modest growth remains unattributed, not declared leak-free. An initial run retained benchmark ElementHandles and falsely retained whole Reader trees; that run is discarded for application leak conclusions. Locator waits avoid those references. Owned mock API/auth remains explicit; no source code from that Reader branch was copied or changed.

- Worker OFF/ON1/canary/stress: measured in three bounded disposable repetitions,3,840 foreground HTTP200 responses. No consistent material p95 degradation; no speculative backpressure change. See `worker-contention-20261005.md` for exact scope, measurements and external-acquisition limitations.
- Genuine authenticated backend-to-browser multichunk Reader timing: not established; Mongo HTTP proof and mock browser proof remain separate.
- Production first-party CWV emission/intake/storage/dashboard correlation: not verified. Existing source requires `REACT_APP_PERF_METRICS_ENABLED=true`; actual deployed flag/access has not been verified, so this is NOT classified as a proven platform-access failure.
- Real52-cover derivative delivery and full chapter/notes/font-change memory soak: not completed. Preserve owner masters and the separate Reader feature lane.
- Bengali font request reduction: deferred; no glyph-quality trade-off made.

The branch is not being declared a complete platform audit or customer-release proof. PR517 blocks opening/pushing a competing performance PR, not local profiling. Next local work: real UAT worker contention and genuine authenticated multichunk browser delivery; refresh against main after the auth PR before Integration Lane review. No deployment performed.
