# Dracula Production Data Repair Runbook

Generated: 2026-06-20

## Default Action

Prefer the deployable Dracula artifact fallback first. Production DB repair is not required if:

- `/api/books` exposes only Dracula as live readable.
- `/api/books/dracula` returns safe `PublicBookOut`.
- `/api/reader/book/dracula/manifest` returns 27 chapters.
- `/api/reader/book/dracula/audiobook` returns 404.

## Dry-Run Diagnostic

```bash
npm run prod:dracula-diagnostic
npm run prod:repair-dracula-record:dry-run
```

The repair script is dry-run by default. It writes:

- `output/production/dracula_repair/dracula_repair_dry_run.json`
- `output/production/dracula_repair/dracula_repair_dry_run.md`

## Apply Guardrail

Only after operator review:

```bash
npm run prod:repair-dracula-record:apply
```

The apply mode:

- only touches `slug=dracula`
- never deletes records
- never mutates non-Dracula records
- refuses to run without a valid approved artifact pack
- refuses if chapter count is not 27
- keeps audio disabled

## Post-Repair Verification

```bash
npm run launch:backend-catalog-truth-canary
npm run release:post-production-canary
```
