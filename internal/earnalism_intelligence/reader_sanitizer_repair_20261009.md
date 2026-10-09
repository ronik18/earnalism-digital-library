# Local Reader sanitizer repair — 2026-10-09

Owner-authorized shared-path correction only. Canonical acquisition references
pr525-reader-handoff-20261009T070257Z. Starting main:
5f341e75ec0e229887507ea1dc7dafa7a74b4bf8.
Performance history archived; #525 source unchanged; no new PR authorized.

## Root causes and focused changes

Prose whitespace regexes in normalize_render_html affected sanitized pre
subtrees. Apply prose normalization only outside complete sanitized pre
subtrees. Bleach remains before preservation; no raw HTML reinsertion.
Allow sup structure without broadening attributes or URL protocols.
Both fragment ingestion and chapter uploads share these paths.

Three new regressions failed before correction; all focused tests pass after.
Expanded regression covers independent pre contexts, escaped markup, nested
markup, tabs/newlines, unsafe attributes, scripts and javascript URLs.
23 tests pass across content safety, native Reader rendering, promotion
safeguards and static Reading Pass security.

## Independent private corpus qualification

All 14 approved chapter-file bindings unchanged. Strict parsed events retain
significant Unicode/text/whitespace and structures; all raw-to-rendered and
rendered-to-segment comparisons pass, including Chapter 6 sup and Chapter 14.
437 pre blocks preserved. Historical per-chapter exceptions total 156 changed
pre blocks; earlier prose claim of 166 was inaccurate and is not repeated as
a verified count. Full-corpus preservation covers every block regardless.

Derived native candidate: 211 pages, manifest 2d6e081a92bbeac0e5364cf2.
Neither 207 nor 211 was an acceptance target. Historical 207 remains rejected
for integrity failure; historical offline 211 remains invalid preparation
method, separate from this newly derived native candidate.

Private evidence: /Users/ronikbasak/.codex/archives/reader-sanitizer-repair-20261009
audit-repaired.py uses the unchanged independent audit except private output
directory; qualify.py verifies full corpus, bindings, determinism and hashes.
Isolated local Chromium excerpts with existing Reader CSS pass at390/768/1440:
indentation, superscript and overflow. Not a production Reader smoke or complete
authenticated application qualification. No production session touched.

One broader unrelated test fails because book-d19e96859f is absent from the
current controlled live allowlist. No catalogue fixture/allowlist repaired or
weakened here. This is not attributed to sanitizer behavior.

## Review, compatibility and rollback boundary

Existing stored pages are unchanged. A future authorized re-preparation can
derive different hashes/page boundaries for meaningful pre whitespace and sup;
review its exact manifest and source bindings before any promotion. No active
manifest/version/pointer, rights, entitlement or payment change occurred.
Rollback of code would reintroduce the defects; neither older stored content
nor historical rejected candidates is an approved content rollback target.

Next decision under one-PR rule: review this exact local repair and qualified
candidate, decide how the focused sanitizer code may enter the protected release
lane while #525 remains open. Separately authorize any source-bound content
recovery/promote plan. No new PR, merge, storage, promotion or deploy performed.

READER_PRODUCTION_VERIFIED=NO
READER_LANE_COMPLETE=NO
PERFORMANCE_WORK=PAUSED_FOR_READER_INTEGRITY
