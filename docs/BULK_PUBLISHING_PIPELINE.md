# Bulk Publishing Pipeline

`scripts/bulk_publishing_pipeline.py` coordinates the existing Earnalism book tooling into one gated flow:

- Agentic AI With Python package readiness or regeneration.
- Legal-source import dry-run or draft upload through `scripts/import_books.py`.
- Admin draft gates and optional live publish through `scripts/book_production_workflow.py`.
- Existing HTTP QA smoke gates, with optional k6 post-publish smoke.
- Landing-page slideshow sync verification through the public `/api/books` response.
- One combined JSON/Markdown report under `output/bulk_publishing_pipeline/`.

The pipeline keeps live publishing blocked by default. Any live publish still requires both `PUBLISH_LIVE=1` and `HUMAN_APPROVED=1`, enforced by the production workflow and the single-command wrapper.

## One-Command Go-Live

Use this from macOS/Linux after updating `book_import_manifest.json` with legally cleared books:

```bash
PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh
```

That single command runs the full automated path:

1. Checks or prepares the Agentic AI publication package.
2. Dry-runs the manifest importer and blocks on rights, source, boilerplate, sanitization, chapter, or metadata failures.
3. Uploads only validation-passing books as drafts.
4. Runs production GO/NO-GO gates on the exact slugs returned by the upload report.
5. Publishes only GO books.
6. Verifies the newly published slugs are visible in public `/api/books` with cover images.
7. Runs `scripts/k6_smoke.js`.
8. Writes the combined report under `output/bulk_publishing_pipeline/<timestamp>/`.

To use a different manifest or a narrowed slug set:

```bash
PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh path/to/manifest.json --book-slug my-book-slug
```

The wrapper intentionally requires `k6`. Install it once on macOS:

```bash
brew install k6
```

The pipeline loads `.secrets/earnalism-import.env` and `.secrets/earnalism-audio.env` for draft upload, production gates, publish, and audio steps. Make sure admin credentials are present there or exported in the shell.

For full platform regression and 100-user load gates, see `docs/REGRESSION_AND_SCALE.md`.

## Current Shelf Slugs

Use these canonical `category_slug` values in manifests and admin uploads:

- `bengali-classics`
- `literary-fiction`
- `young-readers`
- `business`
- `technology`
- `history-strategy`
- `adventure`
- `science-fiction`
- `gothic-fiction`

Legacy slugs such as `classic-literature` and `children-classics` are migrated to `literary-fiction` and `young-readers`.

## Slideshow Behavior

No separate slideshow edit is needed after publishing. The landing-page infinite slideshow reads the live public books endpoint at runtime. Once a book is published and appears in `/api/books` with a cover image, it is automatically included in the slideshow. The `landing_slideshow_sync` phase fails the go-live report if a newly published slug is missing from that public response or lacks a public cover.

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

For normal operations, prefer the one-command `scripts/earnalism_go_live.sh` wrapper instead of manually sequencing `preflight`, `upload-drafts`, and `publish`.

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
