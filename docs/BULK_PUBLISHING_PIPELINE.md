# Bulk Publishing Pipeline

`scripts/bulk_publishing_pipeline.py` coordinates the existing Earnalism book tooling into one gated flow:

- Agentic AI With Python package readiness or regeneration.
- Legal-source import dry-run or draft upload through `scripts/import_books.py`.
- Admin draft gates and optional live publish through `scripts/book_production_workflow.py`.
- Existing HTTP QA smoke gates, with optional k6 post-publish smoke.
- One combined JSON/Markdown report under `output/bulk_publishing_pipeline/`.

The pipeline keeps live publishing blocked by default. Stage `publish` still requires both `PUBLISH_LIVE=1` and `HUMAN_APPROVED=1`, enforced by the production workflow.

## Preflight

Run importer validation, Agentic AI readiness checks, and admin production gates without publishing:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage preflight \
  --manifest book_import_manifest.json \
  --trust-existing-admin-rights
```

If you only want the legal-source import dry-run and Agentic AI readiness check:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage preflight \
  --manifest book_import_manifest.json \
  --skip-production-gates
```

## Upload Drafts

Upload passing manifest books as drafts, then run the production gates:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage upload-drafts \
  --manifest book_import_manifest.json \
  --update-existing-drafts \
  --trust-existing-admin-rights
```

This reuses the importer, keeps books in draft mode, and refuses to overwrite published books.

## Publish Approved Drafts

Publish only books that pass all production gates:

```bash
PUBLISH_LIVE=1 HUMAN_APPROVED=1 python3 scripts/bulk_publishing_pipeline.py \
  --stage publish \
  --manifest output/book_production/covered_drafts_manifest_20260524.json \
  --trust-existing-admin-rights \
  --run-k6-smoke
```

Use `--book-slug` repeatedly or `--all-drafts` to control the publish batch. The report prints published slugs and any blocked gates.

## Agentic AI Package

By default the pipeline checks `final_package/` for the existing Agentic AI readiness report, metadata, DOCX, PDF, Markdown, disabled audiobook flags, balanced code fences, and zero secret-like strings.

To regenerate the package first:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage preflight \
  --agentic-ai-mode prepare \
  --agentic-docx source/agentic_ai_with_python_manuscript.docx \
  --skip-production-gates
```

`prepare` reuses `scripts/prepare_technical_book.py`, which rebuilds `exports/`, `outputs/`, `final_package/`, and `code_companion/`.
