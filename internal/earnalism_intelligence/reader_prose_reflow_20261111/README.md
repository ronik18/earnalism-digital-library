# Reader source-line reflow P0

Owner request: repair Selfish Giant line-break defects across the production Reader and release promptly. Owner explicitly authorized an isolated P0 branch because the canonical integration checkout contains unrelated dirty Sredni work.

BASE_SHA: 55d7db0f5974ceec9472e489608834dca96b3582
Lane: INDEPENDENT presentation-only P0. Preserve the canonical checkout, retained audio retirement consumers, rights, releases, metering, source hashes and transport offsets. No backend deployment is required. This release supplies no Sredni runtime qualification or publication authority.

The stored Selfish Giant packet has double-newline separators at physical source-line widths. The plain-text renderer turns those into paragraphs; single-newline imports similarly create BRs. The shared Reader now projects recognizable fixed-width prose continuations into continuous paragraphs before measurement. Visible Range fragments and background book-map measurement use the same projection. Generated collapsible spaces keep canonical textContent and protected transport coordinates exact. There is no title allowlist or canonical-content rewrite. User-initiated copy materializes only selected seam spaces in the clipboard clone; ordinary/outside/multiple-range selections keep native behavior.

Detection requires at least eight ordinary lines, a >=65% fixed-width cohort, and at least four lowercase mid-sentence continuations. Within that cohort, unfinished prose may continue into a capitalized proper noun. Sentence stops, dialogue openings, headings, nonconsecutive paragraphs and structured literary blocks remain boundaries. Poetry genres, explicit verse/preserve layout and marked poem/stanza/verse blocks override inference. Code, quotations, lists, figures and tables are excluded. Ambiguous/unmarked material is not a claim of universally recoverable authorial paragraph intent: future editorial imports should preserve real paragraph/verse structure and use explicit literary metadata rather than relying on a heuristic.

A separate reproduced reflow edge case moved a retained free-preview anchor past three visual pages when enlarging text. Back now returns directly to the last free visual page. Forward navigation still requests normal protected authorization; no grant or debit bypass was added.

Validation before release:
- 317 Reader tests across 17 suites PASS, including actual Selfish Giant source, capitalized continuations, single-BR imports, verse/Bengali/code/dialogue/table preservation, context propagation and source-exact pagination cuts.
- Catalogue test traverses every stored plain-text chapter, proves source-character parity, and asserts the common projection repairs more than 60 affected title packets. Initial fixed-width source audit found 67 suspect title packets; this is not a count of live books.
- 36 real-Chrome isolated production-build cases PASS: 390x844, 360x740, 844x390, 1440x1000; 1.125rem, 1.25rem, 2rem; first three preview pages, forward/back turns, settings changes and clipboard word-spacing projections. No production API writes.
- Retained Reader owner-applicability and Sredni amendment tests: 28 PASS after keeping the protected route consumer byte-identical.
- Build/static SEO verifier PASS (307 snapshots, 6584 assertions). Final hosted exact-head checks and production verification remain required.

Reproduce:
```
CI=true npm --prefix frontend test -- --watch=false --runInBand --testPathPattern=experiences-v2/reader
npm --prefix frontend run build
node scripts/serve_frontend_build.js --port 13211
READER_REFLOW_BASE_URL=http://127.0.0.1:13211 node frontend/scripts/reader-prose-reflow-smoke.mjs
```
The browser script is loopback-only, uses approved local source fixtures and rejects API mutations. On macOS set CHROME_EXECUTABLE to an installed Chrome binary if Playwright Chromium is absent. New unit regressions are included in the mandatory PR regression launcher.

Next integration action: finish exact-head PR checks/review, merge only the reviewed head, manually deploy exact merged origin/main to the existing frontend project with automatic deployment OFF, and verify live Reader prose, page turns, font reflow and preview denial. Record the actual deployment and browser evidence separately; this document does not claim LIVE.
