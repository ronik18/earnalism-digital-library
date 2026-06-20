# Real-User UX Review Report

## Environment

- Timestamp: `2026-06-20T14:42:42+00:00`
- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Git SHA: `a4fdc4182a12b10ddfd7028d8658af59cbd74304`
- Branch: `codex/real-user-ux-video-audit`
- Railway replica: `20fcb1b8-060b-49da-ab82-e6c918231d6c`
- Vercel deployment id: `not set`
- Vercel URL: `not set`


## Scope

This report is generated from the live Playwright real-user UX video audit artifacts and live backend API probes. It must not be edited into a PASS state by hand.

The audit verifies:

- Dracula is the only live approved Tier A core reading title.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Unapproved titles do not show Start Reading, Read Preview, or Listen Now.
- Pricing uses Dracula-first reading-time packs.
- Removed demo/ecommerce routes do not serve a generic Earnalism shell.

## Current Owner Recommendation

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`

## Validation Summary

| Check | Result |
| --- | --- |
| Playwright browser journey | PASS (12/12 passed) |
| Video artifacts | 10 |
| Trace artifacts | 12 |
| Screenshots | 11 |
| Backend catalog truth | PASS |
| Backend catalog truth canary | PASS |
| Visual removed-route sample | PASS via Playwright |
| Full removed-route canary | PASS |
| Production parity | PASS |
| Payment smoke | PASS_TEST_MODE |
| SEO audit | BLOCKED_FOR_BOOK_SEO |
| Full launch readiness | HOLD_FOR_FIXES |

## Backend Catalog Truth

- `/api/books` status: `200`
- `/api/books` live slugs: `['dracula']`
- `/api/books/dracula` status: `200`
- `/api/reader/book/dracula/manifest` status: `200`
- `/api/reader/book/dracula/manifest` chapter count: `27`
- `/api/reader/book/dracula/manifest` first chapter preview/free: `True`
- `/api/reader/book/dracula/audiobook` status: `404`
- Backend catalog truth: `PASS`

No backend catalog truth failures.


## Artifact Summary

- Screenshots: `11`
- Videos: `10`
- Traces: `12`

## Main Finding

Hydrated UX passes, but SEO/readiness remains blocked.
