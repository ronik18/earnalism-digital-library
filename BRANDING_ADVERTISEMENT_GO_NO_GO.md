# Branding And Advertisement Go/No-Go

## Environment

- Timestamp: `2026-06-20T14:42:42+00:00`
- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Git SHA: `a4fdc4182a12b10ddfd7028d8658af59cbd74304`
- Branch: `codex/real-user-ux-video-audit`
- Railway replica: `20fcb1b8-060b-49da-ab82-e6c918231d6c`
- Vercel deployment id: `not set`
- Vercel URL: `not set`


## Recommendation

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`

## Backend Gate

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


## Decision

- Dracula stays live: `yes`
- Rollback needed: `no`
- Start ads: `no`

Never mark `GO_FOR_BRANDING_AND_ADVERTISEMENT` while backend catalog truth fails, Playwright fails, or SEO/readiness remains blocked.
