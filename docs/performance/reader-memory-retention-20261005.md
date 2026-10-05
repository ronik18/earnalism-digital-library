# Reader memory retention investigation — 2026-10-05

Classification: **BENCHMARK INSTRUMENTATION RETENTION**.

Isolated baseline: `35d4326f9044c507ba2df92cd6688268f7943306`.
Actual Reader compiled read-only: `bf0160975c55f18499ae63b585aa78fe9a25a690`.
Chromium 149.0.7827.55, production React build, 1440×900, same owned fixture,
20 cycles per arm, 300ms post-unmount settle and two explicit GC calls.
Snapshots at 0/5/10/15/20. Raw snapshots remain private in /tmp, outside git.

## Matched controls and causal arms

Least-squares slopes over cycles 6–20:

| Arm | Post-GC KiB/cycle | Nodes/cycle | Listeners/cycle |
| --- | ---: | ---: | ---: |
| Idle | 0.22 | 0 | 0 |
| Router shell | 2.28 | 0 | 0 |
| Reader metadata-failure shell | 6.69 | 0 | 0 |
| Reader, retained ElementHandles | 59.16 | 513 | 48 |
| Reader, Locator waits | 19.27 | 0 | 0 |
| Reader, per-cycle handle disposal | 19.47 | 0 | 0 |

Full individual samples and separate 1–5/6–10/11–15/16–20 slopes are in the
adjacent JSON. Router controls use the same thin React/router fixture shell,
not full production Home/Library/detail components. This controls framework
navigation, not the complete customer journey.

The original ignored `waitForSelector` return values were reproduced in a
separate run, without an explicit retained-handle array: nodes 32→2597→5162
→7727→10292 and listeners155→408→648→888→1128 at cycles0/5/10/15/20.
Thus the controlled held-handle experiment matches the actual profiler defect.

## Retainer and dominator proof

Strong root path: `(GC roots)` → `(Global handles)` → edge `2 / DevTools console`
→ detached `reader-v2__visual-viewport` → entire Reader subtree.
5,400 detached native nodes at cycle20: SVG paths660, paragraphs500, SVGs460,
text nodes440, buttons260, spans240, circles180, list items160, h2 headings80,
divs60 among the largest families.

Global-handle retained size: cycle5 897,980B; cycle20 3,396,252B; after disposal
95,272B; no-handle cycle20 94,232B. Individual Reader viewport subtrees retain
approximately163,596B. After disposal there are no retained Reader viewport
trees and zero detached nodes.

In the clean run, largest cycle5→20 shallow growth is compiled InstructionStream
193,632B, TrustedByteArray56,784B, ProtectedFixedArray23,920B, WeakArrayList12,020B,
Code11,736B, Object9,848B (instrumentation metadata), FeedbackVector6,772B.
These are shallow growth, distinct from dominator retained size. Residual heap
has not fully plateaued: this report does not declare the entire Reader leak-free.

## Lifecycle and repagination

10 desktop→portrait→landscape→desktop round trips and20 font-size actions.
Bookmark and owned note created through UI. Prose cycle5→10 heap4,398,736→
4,380,300B, nodes706 and listeners212 unchanged; one mounted page for24 logical
pages. After exit: heap3,911,892B, nodes32, listeners155, mounted pages0,
Reader observers0, timers0, RAF0. Resize/visualViewport/keydown registrations
balance after unmount. Document selectionchange and router popstate each remain1.

Generated figure fixture cycle5→10 nodes402/listeners218 unchanged; exit returns
nodes32/listeners155/observers0. **Its layout overflows: clientHeight460px,
scrollHeight1472px.** This is not a media pagination acceptance result. It is
recorded separately without broadening this memory correction into a paginator rewrite.

Static audit: component-local layout cache has4-entry FIFO bound and authorization/
revision/geometry/font/content scoping; effect teardown cancels timers, disconnects
observers and removes listeners. Whole-book boundary maps retain source coordinates,
not duplicated manuscript HTML. Manifest/chapter effects abort or invalidate stale
work. Reader creates no object/blob URLs. A single chapter was exercised; multiple
chapters and genuine network cancellation remain unmeasured. Mock acquisition does
not establish security acceptance or real-backend latency. Native Chrome raw CDP GC
was unavailable; the measurements use headless Chromium, not native Chrome GC.

## Correction

Only five profiler waits change from `page.waitForSelector()` to
`page.locator(...).waitFor()`, eliminating implicitly retained ElementHandles.
Two regression tests prevent that API and assert browser/context/server teardown.
No Reader application code changed. No Redis changes: accepted single-flight PASS.

Reproduce owned-fixture experiments:

```sh
PERF_READER_WORKTREE=/tmp/earnalism-reader-true-viewport-pagination \
PERF_READER_FIXTURE=/tmp/reader-structural-fixture/mock.js \
node scripts/investigate_reader_memory.mjs
python3 scripts/analyze_reader_heap.py /tmp/earnalism-reader-memory-evidence
python3 scripts/reader_heap_dominators.py /tmp/earnalism-reader-memory-evidence
```

The fixture is deliberately required explicitly; no production fallback exists.
Do not commit raw heap snapshots. Temporary viewport/media experiments remain in
/tmp. All test browser contexts and the local fixture server were closed.

No push, PR, merge, deployment, auth retry or production mutation.

## Fresh validation and reconciliation

Profiler tests2/2; benchmark runner3 tests+6 subtests; actual Reader focused10
suites/135 tests; actual Reader branch full102/687; recorded performance source
full99/624. Production build PASS; SEO172/3647/0 failures; initial JS155,882 gzip
bytes below165,000 budget. Disposable canonical UAT passed backend groups14/54/
452/1/71/15 (overlap, not summed), catalogue1 existing skip+55 subtests; local
unit29; proxy Node12; frontend contract8/50; broad regression15 suites/143 passed/
0 failed/4 existing skips. Signed journey smoke PASS. No protected CI claim.

Setup attempts are retained in /tmp logs: alternate Mongo28591 rejected by the
benchmark's27018 guard; root dependencies/browser cache initially absent.
Canonical27018 plus existing read-only installed dependencies/browser cache
resolved setup. No application workaround or skip added. Final gate log:
`/tmp/earnalism-memory-regression-complete.log`.

Concurrent performance lane independently committed an equivalent Locator correction
in4059596864eb92ab93836ec56ca25cdfd408857d and worker evidence in91eda6a75.
It was not edited by this investigation. Do not blindly cherry-pick this commit
onto it: compare the profiler patch and carry only nonduplicated tests/evidence.
Worker results are separate prior lane evidence, not a fresh measurement here:
all3840 foreground requests200; canary/stress showed no consistent p95 regression.
Zero external source requests means6/min budget was not exercised. Production
worker remainsOFF. Real-backend-to-browser/multi-chapter memory remains a separate
next proof; this fixture report must not substitute for it.
