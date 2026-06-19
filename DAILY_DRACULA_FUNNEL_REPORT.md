# Daily Dracula Funnel Report

Date: 2026-06-20 IST

Dracula funnel score: 8.1 / 10

Recommendation: GO for Dracula staying live as the only controlled core reading release; HOLD on funnel expansion until Dracula-specific CTAs and events are deployed.

## Live Dracula Checks

- `/api/books/dracula`: 200
- `/book/dracula`: 200
- `/reader/dracula`: 200
- `/api/reader/book/dracula/manifest`: 200
- `/api/reader/book/dracula/audiobook`: 404
- Reader manifest chapter count: 27
- Reader manifest first chapter: unlocked preview
- `audiobook_enabled`: false
- `generate_audiobook`: false
- audiobook asset count: 0
- manifest audio enabled: false

## CTA Findings

Current production before this branch:

- Dracula page and reader are live.
- Generic book CTAs are still present in source.
- Requested Dracula-first labels were missing from current main before this fix branch:
  - Read Chapter 1 Free
  - Start Dracula
  - Get 7-Day Reading Pass
  - source/rights note
  - audio not available yet note

This branch adds those labels and keeps audio unavailable.

## Top Wins

- Dracula API and reader manifest are healthy.
- Chapter 1 is free through the reader manifest.
- Audio remains hidden/404 and has no assets.

## Top Risks

- Without the CTA safety branch, non-Dracula book cards can expose reader CTAs.
- Current production static HTML is generic and does not expose Dracula-specific crawlable copy.
- Dracula-specific analytics events were not all allowlisted before this branch.

## Exact Fixes Needed

- Deploy the CTA safety branch.
- Add server/prerendered Dracula metadata and launch copy.
- Keep Dracula audio disabled until audio QA and human listening review pass.

Dracula stays live: Yes.

Rollback needed today: No.

