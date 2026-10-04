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

## Fixed-height browser evidence
Actual Chrome CSS viewport dimensions; the browser's existing localhost zoom was 67%, and viewport overrides were adjusted to obtain these CSS dimensions. These are not 100/125/150% native zoom assertions. 1280 targets rendered at1279 because of rounding.

| CSS viewport | Usable px | clientHeight | scrollHeight | Pages in current chunk | Algorithm ms |
|---|---:|---:|---:|---:|---:|
| 1440×900 | 511 | 511 | 511 | 20 | 7.7 |
| 1279×720 | 341 | 341 | 341 | 40 | 6.2 |
| 1024×768 | 396 | 396 | 396 | 40 | 12.9 |
| 768×1024 | 656 | 656 | 656 | 40 | 17.2 |
| 390×844 | 266 | 266 | 266 | 80 | 57.0 |
| 844×390 | 75 | 75 | 75 | 360 | 299.3 |
| 1279×600 | 221 | 221 | 221 | 80 | 42.6 |

All recorded reading surfaces fit, overflow-y:hidden; document width/height did not exceed the visible CSS viewport. Short landscape remains sparse (75px prose area) rather than reducing text size.

## Content and interaction evidence
Generated original test manuscript: 17,111 source characters. Sequential traversal of20 measured desktop pages reconstructed17,111 characters with strict equality and every page fit. No copyrighted fixture manuscript was imported. Source-boundary Next reached p=2; Previous returned p=1&a=end and its final measured page. Final book page disabled Next. A saved passage includes source revision and offset. Desktop→mobile→desktop retained offset4271: mobile fragment4271–4562, desktop4271–5127. Increased text size triggered repagination. Keyboard Right changed source offset5127; browser Back/Forward restored4271/5127. Reduced-motion inspection returned animation:none. Captured console-error list was empty. Normal server authorization remains in force.

## Validation
Focused: 5 suites /80 tests. Full frontend:99 suites /629 tests. Production build passed, including static SEO172 snapshots /3647 assertions. Broad PR regression used repository start_local_uat.sh, isolated native MongoDB replica set, Redis, backend and production-built frontend at127.0.0.1:13251/18251; 15 suites /143 tests passed, zero failed,4 unchanged PR-mode skips. No production APIs/database/customer data used. No separate lint/typecheck script; build includes ESLint. Diff check passed.

## Outstanding acceptance
1. Whole-book responsive total and a single global selector are NOT implemented. Current page count is measured within the current authorized source chunk, explicitly labelled with section number. The API manifest does not contain complete authorized chapter text/layout data; fetching all protected chunks blindly would change access/preview behavior. Required next engineering action: design an authorization-aware chapter/layout contract, preserve canonical preview boundaries and stable progress, then implement global page map/selector without estimating unseen text.
2. Oversized composite media/table blocks and indivisible oversized structures fail visibly; supported semantic adapters must be completed and tested before broad content acceptance. No clipping or scrolling fallback is used.
3. Native desktop zoom125%/150% is not verified. Native UI tool reported the Mac locked and unable to unlock; browser DOM testing remained available. Minimum operator action for that verification is unlock the Mac. Browser text-size controls were verified, but are not equivalent to native zoom.
4. New chapter-boundary and all-page landscape traversal are not fully browser-verified; existing canonical route/navigation tests pass. Precise server resume offset remains unchanged.
5. PR516 is the live governance hold; no conflicting PR opened.

## Durable evidence
Outside Git: /Users/ronikbasak/Documents/Earnalism audits/2026-10-04-reader-pagination/ (fixed-height-proof.json, content-integrity.json, screenshots). Screenshot API clipped captures caused temporary viewport recalculation; desktop-prose-proof.png is the uncropped content evidence. Generated fixtures/services/logs are disposable and not committed.

## Next exact action
Continue this branch by adding the authorization-aware chapter visual-page map and oversized structured-block adapters; rerun integrity/browser/zoom acceptance before integration. Do not cherry-pick or release this partial pagination implementation.
