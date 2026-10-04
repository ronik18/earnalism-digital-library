# Measured Reader pagination: local implementation and unresolved acceptance

## Status
BLOCKED — PAGINATION INTEGRITY. No push, PR, merge, deployment or production mutation.

Base main: cdb654d51f94f782063cf79a27c4a93a6a2c0809. Local dependency: premium opening commit ed59d4573cd4d0192ae2c876610102bee00b8bb1. Dedicated owner-requested worktree /tmp/earnalism-reader-true-viewport-pagination; canonical integration and dirty regular checkout untouched. PR516 occupies focused slot.

## RCA
Merged reader-v2.css explicitly sets overflow-y:auto on the viewport-sized canvas. The canonical server page is a source chunk, not a measured visual page; long authorized chunks therefore scroll inside the sheet.

## Implementation
Sanitized semantic DOM blocks are measured offscreen at the exact prose width and typography. Stylesheets and the required web font load before measurements. Whole blocks move to the following page; oversized text blocks split at word boundaries using binary search and DOM Range cloning, preserving inline markup and every whitespace character. Sentence boundaries and measured widow protection apply where feasible. Subsequent fragments suppress repeated decorative drop caps; short landscapes omit the initial decorative drop cap without shrinking body text.

The source offset is the visual navigation anchor; source hash/manifest revision binds URL anchors and local notes/bookmarks. Existing p URLs continue identifying authorized canonical chunks. Resizing produces no history entry, and maps the original offset to the containing new visual page. Existing server-side progress remains canonical and is not replaced with responsive numbers. Precise intra-chunk position is carried by URL/notebook; server resume persistence was not extended.

ResizeObserver plus viewport/font events trigger an 80ms debounce. A maximum of four layout signatures are cached (revision, width, height, typography and sanitized markup); font events invalidate the cache. Rendered overflow is rejected before paint, not silently clipped. Settings/side panels may scroll; prose cannot.

## Fixed-height browser evidence — supplied Agentic AI With Python chapter
Actual Chrome CSS viewport dimensions. Existing localhost zoom is 67%; overrides obtain the requested CSS sizes. These are NOT native 100/125/150% zoom assertions. 1280 targets render at1279 due rounding.

| CSS viewport | Usable px | clientHeight | scrollHeight | Generated pages in supplied chapter | Algorithm ms |
|---|---:|---:|---:|---:|---:|
| 1440×900 | 480 | 480 | 480 | 78 | 246.2 |
| 1279×720 | 312 | 312 | 312 | 129 | 332.8 |
| 1024×768 | 401 | 401 | 401 | 92 | 234.4 |
| 768×1024 | 638 | 638 | 638 | 71 | 210.4 |
| 390×844 | 256 | 256 | 256 | 196 | 583.0 |
| 844×390 | 80 | 80 | 80 | 583 | 1833.8 |
| 1279×600 | 192 | 192 | 192 | 221 | 653.2 |

All recorded surfaces use overflow-y:hidden. Document dimensions equal their CSS viewport; no chapter-caused outer overflow. Body typography remains1.125rem; short-screen blockquote/list/code/table spacing is reduced instead of text size. Landscape80px prose height remains sparse. The full chapter fixture has three whitespace-only landscape fragments; this is an efficiency/polish limitation, not omitted text.

## Content and interaction evidence
Used readonly committed owner-supplied chapter001/002 from data/controlled_publications/agentic-ai-with-python/. No source manuscript changed or newly committed as a fixture. Current chapter001 rendered text is40,822 characters. This local API fixture supplies ONE complete chapter per authorized source unit, unlike the real chunk-based production contract.

Final desktop traversal:78 pages,40,822 reconstructed characters, exact equality, every page fits. Final landscape traversal:583 pages,40,822 reconstructed characters, exact equality, every page fits. Source-range equality holds for every landscape page; missing/duplicated/reordered characters=0 in these supplied-chapter traversals. Initial landscape test falsely mismatched because it read text and anchors in separate browser calls across a render. Its failed artifact is retained; replacement atomic text+anchor+geometry traversal passes. These results do NOT prove a whole-chapter map exists in the current real public route.

Next from final desktop page reached Chapter2; Previous returned Chapter1. Source offset12128 survived desktop→mobile→desktop: mobile fragment12051–12303 includes that offset; desktop returned12128–12617; URL unchanged during repagination. Prior generated-fixture evidence also covered first/last disabled states, keyboard/history, reduced motion, font-size change and notebook anchors; those were not all rerun with this supplied chapter.

Initial pagination now uses the existing ReaderOpening component during genuine calculation. Ordinary turns do not replay the book-opening animation. Fast calculations finish synchronously; long calculations yield after bounded8ms slices. Superseded calculations abort rather than committing stale fragments. Table fragments preserve complete rows, wrappers, whitespace, inline formatting and source order without repeated headers. Unsupported indivisible rows/media still fail closed.

Captured browser error messages include asynchronous listener/message-channel failures; no proven Reader runtime exception was captured, but a zero-console-errors assertion is NOT made. Native browser zoom remains unverified because native UI reports the Mac locked.

## Validation
Focused:6 suites /91 tests. Full frontend:99 suites /634 tests. Production build passed, including static SEO172 snapshots /3647 assertions. Broad PR regression used repository start_local_uat.sh, isolated native MongoDB replica set, Redis, backend and production-built frontend at127.0.0.1:13251/18251; 15 suites /143 tests passed, zero failed,4 unchanged PR-mode skips. No production APIs/database/customer data used. No separate lint/typecheck script; build includes ESLint. Diff check passed.

## Outstanding acceptance
1. Whole-book responsive total and a single global selector are NOT implemented. Current page count is measured within the current authorized source chunk, explicitly labelled with section number. The API manifest does not contain complete authorized chapter text/layout data; fetching all protected chunks blindly would change access/preview behavior. Required next engineering action: design an authorization-aware chapter/layout contract, preserve canonical preview boundaries and stable progress, then implement global page map/selector without estimating unseen text.
2. Complete-row table pagination now passes the supplied chapter at all seven sizes. Indivisible rows, rowspans, composite media and unsupported structures still fail visibly. No clipping or scrolling fallback is used.
3. Native desktop zoom125%/150% is not verified. Native UI tool reported the Mac locked and unable to unlock; browser DOM testing remained available. Minimum operator action for that verification is unlock the Mac. Browser text-size controls were verified, but are not equivalent to native zoom.
4. Complete supplied-chapter desktop/landscape traversal and next/previous chapter boundary now pass. Native zoom, real authorized multi-chunk whole-chapter map, precise server resume offset and all structural adapters remain outstanding.
5. PR516 is the live governance hold; no conflicting PR opened.

## Durable evidence
Outside Git: /Users/ronikbasak/Documents/Earnalism audits/2026-10-04-reader-pagination/ (owned-final-height-proof.json, owned-desktop-final-integrity.json, owned-landscape-integrity-atomic.json, retained failed owned-landscape-integrity.json, settled screenshots). Screenshot API clipped captures caused temporary viewport recalculation; desktop-prose-proof.png is the uncropped content evidence. Generated fixtures/services/logs are disposable and not committed.

## Next exact action
Continue this branch by adding the authorization-aware chapter visual-page map and oversized structured-block adapters; rerun integrity/browser/zoom acceptance before integration. Do not cherry-pick or release this partial pagination implementation.

## Two-lane follow-up

PR516 exact head940f88b82c3af46bf1744f2d476e7098156754c1 passed all nine non-deployment checks. Owner explicitly authorized merge plus automatic deployment after the workflow coupling was identified. GitHub merged=true, merged_at2026-10-04T09:27:23Z, merge/current origin-main c33faa0b52134d74a174e4cd1f424fccd87a0b56. Automatic main workflow37192206945 started; deployment success is not inferred. Its scope is header/Blog/logo/Coming Soon/no-auto-renewals, not Reader pagination.

Formatting-only top-level whitespace now remains raw whitespace instead of becoming artificial paragraphs. Whitespace-only candidate pages join neighboring fragments without removing source characters. Heading lookahead skips formatting nodes. Two new invariant tests cover preserved offsets and whitespace-only sources. Final landscape traversal waits for the selected DOM visual index, then reads text/offset/geometry atomically:581 pages,40,822 characters, zero blank pages, exact reconstruction, all pages fit. An earlier unsynchronized traversal failed and remains retained.

Pre-refresh validation: targeted6/93, full99/636, build/SEO172/3647, diff check pass. Full-chapter runtime map and native zoom acceptance remain unfinished. Native AX inventory became readable, but keyboard setup did not create a tab and native screenshot returned unavailable; this does not establish usable native zoom automation.


## Authorization-aware chapter map follow-up (supersedes prior architecture hold)

Status: BLOCKED — NATIVE ZOOM VERIFICATION. No push, PR, merge, deployment or production mutation. Fresh origin/main remains c33faa0b52134d74a174e4cd1f424fccd87a0b56; open PR list is empty. Canonical integration and dirty regular checkout are untouched. Owner expressly requested continuing this isolated Reader branch.

### Actual backend contract and authorization
The existing public manifest supplies ordered canonical_pages metadata with immutable page IDs, chapter IDs, SHA-256 and content revision; no protected text. Existing GET /api/reading-pass/books/:slug/pages/:index remains the ONLY content path. Preview is at most three transport units. Each protected unit independently requires current server-side lease, publication, territory and entitlement checks. There is no partial-window lease API in the current repository: any denied unit fails the entire selected window closed rather than filling a gap or inferring permission. No backend authorization or business rule changed.

New authorizedChapter.js separates source chapter, authorized window and visual fragments. It validates contiguous canonical manifest ordering, duplicates, chapter/title, exact body SHA-256, publication and segmentation versions. Three bounded concurrent requests assemble only the selected authorized units in exact order, with cancellation and a 32MiB in-memory string budget. Canonical HTML segmentation preserves complete semantic blocks and repeats no transport furniture; concatenation inserts no separators and removes no source text heuristically. Network failures use existing recoverable Reader UI; no uncontrolled retry added.

One chapter-window revision/offset domain drives visual selector, arrows and layout cache. Chunk-local hash-bound p/a/r URLs and notebook anchors map to absolute window offsets and back. Server progress remains canonical chunk based; precise intra-chunk position remains in URL/notebook, not newly added to backend resume storage. A protected fragment can straddle preview/protected units: billing activity now follows actual visible protected source intervals, not merely its starting chunk. Public-only fragments send inactive activity to existing server heartbeat. Pause, expiry, revocation, identity change, denied content and version mismatch remove/discard protected maps. Existing authorization still determines the enforcement point; the client grants nothing.

### Final measured fixed-height proof
Actual Chrome CSS viewport sizes; integer override rounding makes 1280 targets1281/1279. Existing native localhost zoom67% is NOT native100/125/150 verification. Required fonts and styles are loaded for this final table; no central overflow, no horizontal overflow, document height equals viewport height.

| Actual CSS viewport | clientHeight | scrollHeight | Overflow | Visual pages | Pagination ms |
|---|---:|---:|---|---:|---:|
| 1440×900 | 472 | 472 | NO | 83 | 271.7 |
| 1281×720 | 296 | 296 | NO | 156 | 554.5 |
| 1024×768 | 393 | 393 | NO | 103 | 382.0 |
| 768×1024 | 630 | 630 | NO | 83 | 335.2 |
| 390×844 | 248 | 248 | NO | 257 | 772.9 |
| 844×390 | 86 | 86 | NO | 635 | 2304.3 |
| 1281×600 | 176 | 176 | NO | 282 | 993.3 |

All maps above assemble13 authorized transport units. Stable footer copy/line height prevents transport p changes from altering usable prose height. Code wraps without dropping whitespace or horizontally clipping text. Short-height chrome reclaims spacing while retaining44px toolbar and selector targets; prose remains18px. Prior80px landscape surface becomes86px in the final loaded-font layout.635 visual pages and2.3s initial landscape pagination remain a known short-screen efficiency limitation. Algorithm yields in bounded slices, uses binary-search text splitting, memoized normalized source and a four-signature in-memory cache; cached return was observed. No production delay or giant unbounded fetch introduced.

### Integrity and browser evidence
Production-shaped owner-text fixture uses actual backend canonical_page_records segmentation: chapter1 has13 units and40,831 canonical rendered characters (canonical transport formatting differs from prior unsplit40,822-character fixture). Final synchronized635-page landscape traversal reconstructs40,831 exactly; every source range matches, every page fits, page count stable. Missing/duplicate/reordered=0. Earlier unsynchronized traversal failed because it read before React committed the selected page; artifact retained. Earlier font/layout run and original evidence retained, not used as final loaded-font assertions.

Preview2 fixture: only requests[1,2],6,201 authorized characters, four visual pages, exact reconstruction; units3+ never fetched, final Next reaches established sign-in return p3. Automated fixture additionally covers a ten-unit chapter with only two allowed units. Browser lease revocation at existing heartbeat removed the protected sheet and all reading text. Final desktop Next reaches chapter2 at p14 with14 units; Back restores chapter1 source anchor. Desktop offset12014 → mobile interval11929..12107 → desktop12014..12517; URL unchanged, desktop cached=true.

Final desktop startup: manifest0.3ms, acquisition wall44.9ms, aggregate parallel network85.5ms, SHA verification15.7ms, assembly3.4ms, pagination271.7ms, lease-start-to-reader-mounted410ms. Network sum is NOT wall time. These are local fixtures, not production latency. Final landscape initial algorithm2304.3ms. No paid/source acquisition or customer-data access.

Browser logs include extension-style asynchronous response/message-channel errors. No proven Reader runtime exception; zero-console-errors is NOT claimed.

### Validation and changed scope
Focused7 suites/113 tests; full frontend100 suites/666 tests. Related backend reading-pass policy/text-admission/revocation24 passed. Production build compiled successfully; SEO172 snapshots/3647 assertions/zero failed. Disposable PR regression15 suites/143 passed/zero failed/4 unchanged skips; isolated native MongoDB replica set, Redis, backend and production-built frontend through scripts/start_local_uat.sh. All loopback; no production services used. No separate lint/typecheck script; build includes ESLint. Diff check passes.

Implementation files: authorizedChapter.js plus tests; ReaderExperienceV2Route.jsx and lifecycle tests; ReaderExperienceV2.jsx; readerContent.js; reader-pagination.css. No backend/dependency/environment/rights/publication changes. Historical commits preserved.

### Remaining acceptance and next exact action
NATIVE ZOOM VERIFICATION BLOCKED BY TEST ENVIRONMENT. Native Chrome UI reported: The Mac is locked and automatic unlock could not unlock it. Minimum operator action: unlock the Mac, then rerun native100%,125%,150% zoom with actual source-anchor and height receipts. Do not substitute CSS transforms or viewport emulation. Indivisible oversized rows/media still fail visibly; no clipping/scroll fallback. Precise server-side intra-chunk resume remains unchanged. No release-readiness claim until native zoom acceptance passes.

Durable final artifacts outside Git: chapter-window-height-proof-final.json, chapter-landscape-integrity-final.json, chapter-preview-integrity.json, chapter-startup-performance.json, chapter-desktop-final.png, chapter-mobile-final.png in /Users/ronikbasak/Documents/Earnalism audits/2026-10-04-reader-pagination/.


## 2026-10-05 authorization-aware whole-book follow-up

Status: BLOCKED — PAGINATION INTEGRITY. No push, PR, merge, deployment or production mutation.

- Current chapter measured first; subsequent authorized chapters measured sequentially. The map retains boundaries/source anchors only, not manuscript HTML. Final whole-book totals appear only after all authorized chapters are measured.
- Authorization/layout scope changes abort acquisition and discard map/cache entries. Preview requests were exactly [1,2], outside-preview requests zero. Revoked fixture lease removed protected Reader content and the map.
- Exact reconstruction: preview 6,201 characters; chapter 1 40,831; chapter 2 44,850. Missing/duplicated/reordered characters zero. Full authorized two-chapter fixture: 160 desktop pages.
- Generated structured fixture: 4,609 characters reconstructed exactly at desktop and landscape, one displayed image, tall table cell converted to sequential semantic cells with headers once. Figure scales proportionally.
- Native Chrome: 100% 296/296, 125% 162/162, 150% 124/124 clientHeight/scrollHeight. Source offset 59 remained within the visible fragment.
- Short landscape removed redundant chapter/footer chrome and duplicate footer page-turn buttons, preserving primary 44px controls. Narrow short screens place arrows beside the sheet to reclaim bottom space.

### Actual Chromium viewport proof

| Viewport | clientHeight | scrollHeight | Book pages | Overflow |
|---|---:|---:|---:|---|
| 1440x900 | 460 | 460 | 160 | none |
| 1280x720 | 285 | 285 | 292 | none |
| 1024x768 | 357 | 357 | 207 | none |
| 768x1024 | 621 | 621 | 161 | none |
| 390x844 | 286 | 286 | 379 | none |
| 844x390 | 148 | 148 | 679 | none |
| 1280x600 | 165 | 165 | 539 | none |

### Validation

- Targeted Reader: 10 suites, 129 passed.
- Full frontend: 102 suites, 680 passed.
- Backend rendering/manifest/bootstrap: 360 passed.
- Production build passed; static SEO 172 snapshots, 3,647 assertions, zero failures.
- Disposable MongoDB/Redis/backend/production frontend PR regression: 143 passed, zero failures, four unchanged skips.
- Diff check passed.
- Browser selector, chapter boundary, first/last states and Back/Forward passed.
- First readable page 551ms, eventual map 799ms in isolated fixture; no production timing claim.

### Remaining integrity gate

Multiple textless image pages share the same text offset. This would make source-offset navigation ambiguous. The paginator now rejects that case before paint and has a focused negative test. Structural media/block anchors must be implemented and round-trip tested through URL, history, selector, notes and bookmarks before this branch is release-ready. Captioned figures passed, but do not generalize that evidence to image-only books.

PR #517 currently occupies the focused slot. Premium opening remains a separate existing commit.
Evidence directory: /Users/ronikbasak/Documents/Earnalism audits/2026-10-05-reader-book-map
Next action: implement structural source anchors for textless visual pages, then repeat media-only sequential/history/resize reconstruction before integration.
