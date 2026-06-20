# Backend Catalog Truth Audit

## Scope

This audit documents the backend/API truth gate for the Dracula-only controlled launch.
It is a local dry-run review artifact; it does not publish content, enable audio, call
providers, or mutate production data.

## Current Launch Truth

- Dracula is the only live approved Tier A core reading candidate.
- Dracula may expose book metadata, reader manifest, preview chapter access, and core reader access.
- Dracula audio remains disabled.
- Kshudhita Pashan remains pipeline-only.
- Tier B, Tier C, and unapproved titles must not expose Start Reading, Read Preview, Listen Now, public audiobook, or sitemap entries.

## Backend Enforcement Points

| Surface | Expected Behavior |
| --- | --- |
| `/api/books` | Returns only Dracula as the live approved reading title. |
| `/api/books/{slug}` | Returns Dracula metadata only; unapproved slugs return 404. |
| `/api/books/{slug}/chapters` | Returns Dracula chapter metadata only. |
| `/api/books/{slug}/chapters/{chapter_id}` | Returns Dracula preview content only when preview rules allow it. |
| `/api/reader/book/{slug}/manifest` | Returns Dracula manifest only; non-Dracula returns 404. |
| `/api/reader/chapter/{slug}/{chapter_id}` | Returns Dracula reader content only. |
| `/api/reader/book/{slug}/audiobook*` | Returns 404 while audio is disabled, including Dracula. |
| `/api/home`, `/api/home/books`, `/api/featured` | Project only Dracula as the live controlled release. |

## Projection Policy

Public projections are generated through `backend/catalog_truth.py`. They remove
internal rights/source evidence and audio storage fields from public metadata, and
they strip chapter body content from metadata responses.

## Daily Owner Command

```bash
npm run owner:catalog-truth-audit
```

This writes:

- `output/daily/YYYY-MM-DD/catalog_truth_report.md`
- `output/daily/YYYY-MM-DD/catalog_truth_matrix.csv`
- `output/daily/YYYY-MM-DD/catalog_truth_report.json`

## Result

The local audit matrix for 2026-06-20 reports:

- Live approved count: 1
- Dracula-only live approved: true
- Pipeline candidate count: 1
- Unapproved reader link count: 0
- Unapproved audio link count: 0
- Unapproved sitemap count: 0

Recommendation: GO for Dracula-only backend catalog truth after validation remains green.
