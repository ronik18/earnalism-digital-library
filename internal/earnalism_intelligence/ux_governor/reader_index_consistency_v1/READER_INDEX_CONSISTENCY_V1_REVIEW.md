# Reader Index Consistency v1 Review

Status: source, hosted CI, isolated staging API, and Vercel preview validation passed.

## Problem

Reader contents surfaces mixed a generated ordinal with source titles that often repeated a second numbering system. Long indexes also inherited the fixed reader page overflow, which clipped later chapters on mobile. Dracula exposed both faults: entries rendered as `01` beside `Chapter I...`, while chapters below the viewport were unreachable.

## Decision

- Use one deterministic `chapter-index.v1` contract in the backend manifest, chapters endpoint, full-page contents view, and drawer contents view.
- Preserve source metadata while deriving a stable sequence, structural label, and primary title for display.
- Convert structural Roman numerals to Arabic labels, remove only formatting marks and terminal `continued` suffixes, and preserve Bengali or other non-English titles unchanged.
- Make the index page vertically scrollable, prohibit horizontal overflow, and retain 44 px minimum interactive rows.
- Keep the reader's horizontal page-change gestures unchanged. Index scrolling is vertical content navigation, not a page-change gesture.

## Evidence

- Controlled-publication audit: 79 books, 691 chapter/index records, zero blockers.
- Backend focused tests: 10 passed.
- Frontend reader/index/release-truth tests: 31 passed.
- Production frontend build: passed.
- Dracula local browser at 390 x 844: scroll height 1824 px, client height 669 px, maximum scroll 1155 px reached, scroll width equals client width at 390 px.
- Dracula final visible range included chapters 19 through 27 and the contents footer.
- Hosted PR regression: passed in 3m08s; production deploy and canary jobs skipped.
- Railway staging deployment `37b1b381-301f-48f0-a875-802d3ba0cf1c`: healthy; the Dracula manifest returns `chapter-index.v1`, 27 ordered entries, and the normalized first/last labels.
- Vercel preview deployment `dpl_FdbErLSUAcrdiSjEobrxYGwsrKt5`: ready, preview target, noindex, and its built artifact contains `chapter-index.v1` and the isolated staging API hostname.

The generated full audit remains outside version control at `/private/tmp/pr269-reader-index-audit.json`; rerun it with `python3 scripts/audit_reader_indexes.py`.

## Release boundary

This evidence does not approve an audiobook, merge PR #269, or change production. Reading Pass remains confined to the isolated staging environment. Private preview audio is still fail-closed because no approved Dracula master exists.
