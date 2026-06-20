# Daily Growth Audit Runbook

## Purpose

Run a local, deterministic owner audit for The Earnalism without publishing content, enabling audio, sending campaigns, charging payments, or mutating production data.

Dracula remains the only live controlled reading title. Kshudhita Pashan and all other unapproved titles remain pipeline-only.

## Command

```bash
npm run owner:daily-growth-audit
npm run owner:catalog-truth-audit
```

The command writes dated dry-run artifacts under:

```text
output/daily/YYYY-MM-DD/
```

The output directory is intentionally not a committed source of truth. Commit only curated snapshots when a PR needs review evidence.

## What The Daily Audit Checks

- Production health signals from launch readiness tooling.
- Dracula-only reader and pricing funnel readiness.
- Payment smoke in test/static mode only.
- Analytics event allowlist coverage.
- Rights-safe publication gates.
- Bengali Gothic pipeline status without public reader/audio access.
- Backend catalog truth: Dracula-only live approved count, unapproved reader links, unapproved audio links, and unapproved sitemap entries.
- Blockers and recommended owner actions.

## Safety Rules

- Do not publish new books.
- Do not enable audiobook.
- Do not call payment providers, TTS, STT, LLM, OCR, image, email, social, or paid APIs.
- Do not mutate production data.
- Do not show Start Reading, Read Preview, or audio CTAs for unapproved books.
- Hold growth expansion if `npm run owner:catalog-truth-audit` reports any non-Dracula reader/audio/sitemap exposure.
- Keep recurring output under `output/daily/YYYY-MM-DD/`.

## Snapshot Reports

The committed `*_SNAPSHOT.md` files are sample evidence from the 2026-06-20 IST audit. They are not recurring live reports.

## Hidden Unicode Note

Run the local scanner before pushing daily-audit report changes:

```bash
python3 scripts/check-hidden-unicode.py changed-files-list
```

If GitHub still shows a hidden/bidirectional Unicode warning while the local scan passes, document the exact scanned file list and the passing local result in the PR. The scanner checks bidirectional controls, zero-width characters, BOM, and CR-only line endings.

## Rollback

Revert the PR commit that introduced a bad snapshot/report/runbook change. Generated `output/daily/YYYY-MM-DD/` files can be removed locally because they are dry-run artifacts.
