# Backend Catalog Truth Deployment Checklist

## Purpose

Use this checklist before and immediately after deploying the backend catalog truth
gate. The gate is intentionally strict so that unsafe or incomplete production
metadata fails closed instead of exposing unapproved books.

## Required Production Dracula Mongo Fields

The production `books` document for Dracula must have:

- `slug = "dracula"`
- `is_published = true`
- `rights_metadata.rights_tier = "A"`
- `rights_metadata.verification_status = "approved"`
- `rights_metadata.blocked_reason` empty, null, or missing
- `qa_status = "QA_PASSED"`
- `source_hash` present
- `content_hash` present
- `provenance_hash` present
- `source_url` present
- `source_name` present
- `source_license` present
- `approved_to_publish = true` or equivalent committed approval evidence

## Expected Failure Mode

If production Mongo does not have these fields, `/api/books` may return zero live
books. That is a safe fail-closed state, but it is a launch blocker until the
production Dracula record is corrected.

## Post-Deploy Canary

Run immediately after deployment:

```bash
npm run launch:backend-catalog-truth-canary
```

The command calls the production API and writes:

```text
output/launch/backend_catalog_truth_canary/catalog_truth_report.json
output/launch/backend_catalog_truth_canary/catalog_truth_report.md
output/launch/backend_catalog_truth_canary/catalog_truth_matrix.csv
```

## Pass Criteria

- `/api/books` contains Dracula as the only live readable item.
- No non-Dracula book has `reader_enabled=true`.
- No non-Dracula book has `preview_enabled=true`.
- No item has `audio_enabled=true`.
- Kshudhita Pashan is absent or pipeline-only.
- `/api/reader/book/dracula/manifest` returns 200.
- `/api/reader/book/kshudhita-pashan/manifest` returns 404 or 403.
- `/api/reader/book/dracula/audiobook` returns 404 while audio is disabled.
- `/api/reader/book/kshudhita-pashan/audiobook` returns 404.

## Hold Criteria

HOLD deployment or roll back if:

- Any non-Dracula item is live readable.
- Any non-Dracula item exposes preview or reader access.
- Any audiobook endpoint returns 200 or redirects to an asset.
- `/api/books` returns zero live Dracula rows.
- Dracula detail or reader manifest returns 404.

## Safety

This checklist does not approve new books, enable audio, mutate data, or call paid
providers. It only verifies that production already matches the controlled launch truth.
