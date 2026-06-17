# Phase 2 Rights Integration Report

This report documents the exact runtime enforcement points added for the
deterministic rights verification engine. The implementation is dry-run/report
friendly and does not mutate production content automatically.

## Enforcement Summary

| Enforcement point | File | Function / route | Rights call | Expected block behavior | Test coverage |
| --- | --- | --- | --- | --- | --- |
| Book create when `is_published=true` | `backend/server.py` | `POST /api/admin/books` / `admin_create_book` | `_assert_publishable(doc)` calls `rights_publish_blockers` through `_publish_blockers` | Returns HTTP 400 with rights issues when rights metadata is missing, unsafe, Tier C, or region-invalid | `test_publishing_create_and_update_paths_call_publish_gate`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Book update when `is_published=true` | `backend/server.py` | `PUT /api/admin/books/{slug}` / `admin_update_book` | `_assert_publishable(candidate)` calls `rights_publish_blockers` through `_publish_blockers` | Returns HTTP 400 before update if the resulting published book is not rights-approved | `test_publishing_create_and_update_paths_call_publish_gate`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Chapter/source text create for published book | `backend/server.py` | `POST /api/admin/books/{slug}/chapters` / `admin_add_chapter` | `_assert_public_rights_approved(book, "Source text")` calls `rights_publish_blockers` | Returns HTTP 400 before source text is added to a published book without approved rights | `test_runtime_source_and_asset_mutations_block_published_unsafe_books`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Chapter/source text update for published book | `backend/server.py` | `PUT /api/admin/books/{slug}/chapters/{cid}` / `admin_update_chapter` | `_assert_public_rights_approved(book, "Source text")` calls `rights_publish_blockers` | Returns HTTP 400 before source text is updated on a published book without approved rights | `test_runtime_source_and_asset_mutations_block_published_unsafe_books`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Chapter file upload for published book | `backend/server.py` | `POST /api/admin/books/{slug}/chapters/{chapter_id}/upload` / `admin_upload_chapter_file` | `_assert_public_rights_approved(book, "Source text")` calls `rights_publish_blockers` | Returns HTTP 400 before uploaded source text is processed for a published book without approved rights | `test_runtime_source_and_asset_mutations_block_published_unsafe_books`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Cover/visual asset upload for published book | `backend/server.py` | `POST /api/admin/books/{slug}/cover` / `admin_upload_cover` | `_assert_public_rights_approved(book, "Visual asset")` calls `rights_publish_blockers` | Returns HTTP 400 before cover/visual asset processing for a published book without approved rights | `test_runtime_source_and_asset_mutations_block_published_unsafe_books`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Audiobook update for published book | `backend/server.py` | `PATCH /api/admin/books/{slug}/audiobook` / `admin_update_book_audiobook` | `_assert_public_rights_approved(existing, "Audiobook")` calls `rights_publish_blockers` | Returns HTTP 400 before enabling/generating/updating audiobook assets for a published book without approved rights | `test_runtime_source_and_asset_mutations_block_published_unsafe_books`, `test_server_routes_keep_all_required_rights_enforcement_calls` |
| Admin rights report endpoint | `backend/server.py` | `GET /api/admin/rights/reports/{filename}` / `admin_rights_report` | `rights_report_rows` and `rights_report_csv` | Requires admin auth; valid filenames return CSV; invalid filenames return 404 | `test_admin_rights_report_endpoint_requires_admin_auth`, `test_admin_rights_report_valid_filename_returns_csv`, `test_admin_rights_report_invalid_filename_returns_404` |
| Dry-run rights audit script | `scripts/rights_audit.py` | `main`, `load_books`, `write_reports` | `rights_report_rows` and `rights_report_csv` | Reads local JSON export and writes approved/quarantine/blocked CSVs without production connections or mutations | `python3 -m py_compile scripts/rights_audit.py`; documented in `RIGHTS_ENGINE.md` |

## Admin Report Endpoint

Endpoint:

```text
GET /api/admin/rights/reports/{filename}
```

Valid filenames:

- `rights_quarantine_report.csv`
- `rights_approved_report.csv`
- `rights_blocked_report.csv`

The endpoint is protected by `require_admin`. Invalid filenames return 404.
CSV output includes `decision_status` and `decision_issues`.

## Public Publishing Block Policy

Public publishing is blocked when deterministic rights metadata is missing,
unsafe, Tier C, or region-invalid. Draft records may retain assets and source
preparation artifacts, but draft state does not mean public rights approval.

## Production Mutation Safety

The dry-run rights audit script reads a local JSON export only. It does not
connect to production, does not update MongoDB, and does not delete or publish
content.
