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
