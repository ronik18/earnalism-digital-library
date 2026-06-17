# Deterministic Rights Engine

Phase 2 adds a deterministic rights verification engine for Earnalism.

The engine is intentionally rule-based. It does not call LLMs, TTS providers,
image APIs, or external legal services.

## Runtime Enforcement

Implementation files:

- `backend/rights_engine.py`
- `backend/server.py`
- `backend/tests/test_rights_engine.py`

The backend now blocks public publication when rights approval is missing or
unsafe.

Enforced paths include:

- Book create/update when `is_published` is true.
- Published-book chapter/source text creation.
- Published-book chapter/source text updates.
- Published-book chapter file uploads.
- Published-book cover/visual asset uploads.
- Published-book audiobook updates.

Draft books may still be saved while rights evidence is incomplete. Draft
records are not treated as public approval.

## Decision Outcomes

The engine returns one of:

- `approved`
- `quarantine`
- `blocked`

`approved` means the deterministic rules pass.

`quarantine` means required metadata or verification evidence is missing.

`blocked` means the available metadata indicates unsafe rights, Tier C status,
modern protected contributors, or region-policy violation.

## Reports

The backend exposes CSV report generation through:

```text
/admin/rights/reports/{filename}
```

Valid filenames:

- `rights_quarantine_report.csv`
- `rights_approved_report.csv`
- `rights_blocked_report.csv`

The endpoint is admin-only and read-only.

## Dry-Run Backfill Audit

To audit an exported local book dataset without mutating production, run:

```bash
python3 scripts/rights_audit.py \
  --input output/books_export.json \
  --output-dir output/rights_audit
```

The input may be:

- a JSON array of book documents, or
- an object with a `books` array.

The command writes:

- `output/rights_audit/rights_quarantine_report.csv`
- `output/rights_audit/rights_approved_report.csv`
- `output/rights_audit/rights_blocked_report.csv`

This dry-run report identifies:

- existing published books without rights metadata,
- existing published audiobooks without rights approval,
- existing public book assets without rights approval,
- records that are safe, blocked, or quarantined under deterministic rules.

The script never connects to production and never changes book records.

## Admin Report Output

Each report row includes:

- book slug
- book title
- decision status
- decision issues
- all rights metadata fields from `RIGHTS_POLICY.md`

## Rollout Notes

Existing public catalog records should be audited and backfilled before strict
operational rollout. Until backfilled, future public mutations for a published
book without approved rights metadata will be blocked.

