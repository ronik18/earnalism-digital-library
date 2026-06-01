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

## Future Book Onboarding Without Codex

Use this exact operating path whenever you onboard a new title. It uses only local scripts and terminal commands.

1. Put each future book into `book_import_manifest.json` under `books[]`.
2. Use the canonical fields already shown in the manifest: `title`, `subtitle`, `author`, `author_death_year`, `original_publication_year`, `source_url`, `source_type`, `source_license`, `rights_basis`, `commercial_use_allowed`, `requires_attribution`, `requires_sharealike`, `category_slug`, `short_description`, `description`, `benefits`, `who_for`, `learnings`, `about_author`, `is_published`, `availability`, `attribution_notice`, and `forbidden_source_terms`.
3. Keep reader-facing metadata clean: do not place source repository names, legal boilerplate, or source URLs in `title`, descriptions, chapters, benefits, who-for, learnings, or about-author copy unless the license requires it.
4. Set `is_published` to `false` and `availability` to `draft` for every new book. The pipeline decides whether a draft is safe to publish.
5. Use only these shelf slugs: `bengali-classics`, `literary-fiction`, `young-readers`, `business`, `technology`, `history-strategy`, `adventure`, `science-fiction`, `gothic-fiction`.
6. For audiobook generation, add both `audiobook_enabled: true` and `generate_audiobook: true` to that book's manifest item. Leave both `false` or omitted when no generated audiobook is needed.
7. Confirm `.secrets/earnalism-import.env` and `.secrets/earnalism-audio.env` are present on the machine. They provide admin upload credentials and any audio provider settings.
8. Run a no-publish preflight first:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage preflight \
  --manifest book_import_manifest.json \
  --trust-existing-admin-rights
```

9. If preflight is green, upload drafts only:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage upload-drafts \
  --manifest book_import_manifest.json \
  --update-existing-drafts \
  --trust-existing-admin-rights
```

10. Publish only after human approval. This command runs legal gates, formatting checks, latency-risk holdbacks, optional audiobook generation, smoke tests, and slideshow sync:

```bash
PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh
```

11. If only one book should go live, pass its slug:

```bash
PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh book_import_manifest.json --book-slug your-book-slug
```

12. Read the generated report under `output/bulk_publishing_pipeline/<timestamp>/`. It prints uploaded IDs/slugs, published slugs, skipped-book reasons, latency-risk holdbacks, audiobook asset checks, smoke-test status, and slideshow visibility.

Books held by latency-risk gates stay as drafts. They should not be forced live unless backend projection, pagination, and load tests have been verified for that specific manuscript size.

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

Legacy slugs such as `classic-literature` and `children-classics` are migrated to `literary-fiction` and `young-readers`. The importer and admin API also normalize incoming book records to this shelf list so a book cannot be uploaded with a dangling category.

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

## Latency-Risk Holdbacks

The production workflow automatically holds oversized books as drafts when publishing them could increase API latency or timeout risk. By default, a book is held back if it exceeds any of these thresholds:

- More than `80` chapters.
- More than `1,800,000` stored-content characters.
- Any single chapter over `120,000` stored-content characters.

Held books stay uploaded as admin drafts with their text and covers intact, but they are not published live and are excluded from the publish batch. The report lists them under `Latency-Risk Holdbacks`. Tune the guard per run with:

```bash
python3 scripts/bulk_publishing_pipeline.py \
  --stage publish \
  --max-publish-chapters 80 \
  --max-publish-chars 1800000 \
  --max-publish-chapter-chars 120000
```

Use `--disable-latency-risk-gate` only after backend pagination/projection has been verified for very large books. Use `--block-latency-risk-holdbacks` if you want a holdback to fail the whole batch instead of publishing the safe books.

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
