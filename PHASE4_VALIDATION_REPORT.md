# Phase 4 Validation Report

Branch: `codex/phase4-source-ingestion`

## Scope

Phase 4 adds a deterministic, dry-run public-domain source ingestion pipeline. It does not add production routes, publish content, call paid APIs, fetch live source URLs by default, or mutate production data.

## Changed Files

- `backend/source_ingestion.py`
- `backend/tests/test_source_ingestion.py`
- `scripts/source_ingestion.py`
- `package.json`
- `SOURCE_INGESTION.md`
- `PHASE4_VALIDATION_REPORT.md`

## Validation Commands

```bash
python3 scripts/check-hidden-unicode.py backend/source_ingestion.py backend/tests/test_source_ingestion.py scripts/source_ingestion.py package.json SOURCE_INGESTION.md PHASE4_VALIDATION_REPORT.md
python3 -m py_compile backend/source_ingestion.py
python3 -m py_compile backend/tests/test_source_ingestion.py
python3 -m py_compile scripts/source_ingestion.py
PYTHONPATH=. pytest backend/tests/test_source_ingestion.py
npm run source:ingest
npm run catalog:audit
npm run regression -- modules/13-public-content-governance.test.js
npm --prefix frontend run build
```

## Result

- Hidden Unicode / line-ending scan: passed for 6 files.
- Python compile: passed for `backend/source_ingestion.py`, `backend/tests/test_source_ingestion.py`, and `scripts/source_ingestion.py`.
- Source ingestion tests: passed, 18 tests.
- `npm run source:ingest`: passed and wrote local dry-run reports to `output/source_ingestion`.
- Default JSON report excludes full `raw_text` and `cleaned_text`; it includes previews, hashes, character counts, and chapter metadata.
- Provenance check passed: `content_hash` and `provenance_hash` are present in dry-run reports.
- `npm run catalog:audit`: passed, 251 items audited.
- Public content governance regression: passed, 15 tests.
- Frontend build: passed.

## Hardening Checks

- Rights blockers are evaluated before scanned PDF placeholder status. A Tier C scanned PDF source returns `BLOCKED_RIGHTS`, not `PENDING_OCR`.
- `downstream_regeneration_required` replaces the previous misleading regeneration signal.
- `downstream_artifacts_regenerated` remains present for compatibility and is always `false` in Phase 4 dry-runs.
- The CLI is dry-run only. `--commit`, `--publish`, and `--write` are rejected.
- `--include-text` is required before full raw or cleaned text appears in JSON reports.
- `--text-preview-chars` controls preview length; default is 1000 characters.

## Raw GitHub Verification

Pending after push of the hardening commit.

## Production Mutation

No production content was mutated.

## Remaining Risks

- Chapter detection is deterministic and conservative; unusual source formatting may need manual review.
- Scanned PDF ingestion is intentionally a placeholder until a later OCR phase.
- URL fetching is not enabled by default; source text must be supplied locally for this phase.
