# ASR Mismatch Repair Plan

Generated: 2026-07-09T05:54:16Z

## Scope

This plan covers:

- `book-d19e96859f`
- `book-f5d593e1f4`

Both titles remain no-public-audio candidates.

## Current Diagnosis

Prior evidence shows severe Bengali audio/manuscript mismatch. Source-rights evidence exists, but the paid diagnostic must be limited to one cleaned, targeted group sample per title after the exact mismatch segment is defined.

## Repair Rules

- Do not reuse stale or failing audio as release evidence.
- Do not add either title to public audio or paid Listen surfaces.
- Do not generate full-book audio.
- Do not commit generated audio artifacts unless repo policy explicitly authorizes it.
- Keep the diagnostic sample small and budget-scoped.

## Next Actions

1. Identify the contaminated group or source-frontmatter region for each title.
2. Strip source/page boilerplate from the diagnostic sample.
3. Run at most one small paid diagnostic sample per title after env gates are present.
4. Re-run ASR/source alignment and listening QA on the diagnostic output.
