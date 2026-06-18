# Phase 6 Visual Design Engine

Phase 6 adds a deterministic dry-run engine for visual explainer and study assets. It does not publish content, fetch network resources, use copyrighted images, call AI image generation, run OCR, call TTS, or use paid APIs.

## Asset Templates

The engine supports:

- character relationship diagram
- timeline
- chapter flow
- theme map
- vocabulary cards
- quiz worksheet
- 7-day reading plan card
- teacher handout

It also includes dry-run generation hooks for:

- reading edition EPUB
- study guide PDF
- mobile HTML edition

## Deterministic Tools

Outputs use only deterministic local formats:

- Mermaid text for character diagrams, timelines, and chapter flows.
- Inline SVG for theme maps.
- HTML/CSS templates for cards, worksheets, handouts, and mobile HTML.
- Pandoc-compatible dry-run hook strings for EPUB/PDF.

No external images are referenced.

## Upstream Gates

Visual generation blocks before any asset renderer runs unless all upstream evidence is present:

- Phase 2 rights: `rights_tier=A`, `verification_status=approved`, and no `blocked_reason`.
- Phase 3 demand: `action_status=READY_FOR_GENERATION`.
- Phase 4 ingestion: `ingestion_status=INGESTED` or `CLEANED`.
- Phase 5 edition: `edition_generation_status=READY_FOR_REVIEW`, `PARTIAL_DRY_RUN`, or `QA_PASSED`.
- Traceability: `source_hash`, `content_hash`, `provenance_hash`, `source_work`, and `cleaned_text` are present.

Blocked gate statuses include `BLOCKED_RIGHTS`, `BLOCKED_RIGHTS_REVIEW_REQUIRED`, `REGION_GATED_REVIEW`, `BLOCKED_PRIORITY_GATE`, `BLOCKED_INGESTION`, `BLOCKED_EDITION_GATE`, and `BLOCKED_TRACEABILITY`.

## Metadata

Each generated asset includes:

- `asset_type`
- `source_work`
- `source_hash`
- `content_hash`
- `provenance_hash`
- `generated_at`
- `quality_score`
- `file_size`
- `output_format`
- `qa_status`
- `generation_hook`

## Dry-Run CLI

Safe sample:

```bash
npm run visual:design
```

Local payload:

```bash
python3 scripts/visual_design_engine.py \
  --input path/to/source-or-edition-payload.json \
  --output-dir output/visual_design
```

Selected assets:

```bash
python3 scripts/visual_design_engine.py \
  --input path/to/payload.json \
  --asset theme-map \
  --asset quiz-worksheet
```

Full deterministic content is excluded from JSON and Markdown by default. Use `--include-content` only for local review.

The CLI rejects `--commit`, `--publish`, and `--write`. Direct library calls with `dry_run=False` are blocked.

## Reports

The CLI writes:

- `output/visual_design/visual_design_report.json`
- `output/visual_design/visual_design_report.csv`
- `output/visual_design/visual_design_report.md`

Reports are preview-only by default and include lightweight file-size metadata.

## QA

The QA layer verifies:

- no copyrighted image dependency
- no AI image generation required
- dry-run EPUB/PDF hooks are present
- generated assets are lightweight
- deterministic content is present for requested assets

External image/dependency policy blocks or flags all generated content containing:

- `<img`
- `src=`
- `srcset=`
- `background-image`
- `url(`
- `http://`
- `https://`
- `data:image`
- `//cdn`

This validation applies to HTML, SVG, Mermaid, JSON-hook, and Markdown-style content.

## EPUB/PDF Hooks

EPUB/PDF outputs are dry-run metadata only. The engine records Pandoc-compatible command strings but does not execute Pandoc, Calibre, subprocesses, or any external conversion tooling.

## Limitations

- Mermaid rendering itself is not performed in Phase 6; the output is Mermaid source.
- EPUB/PDF hooks are dry-run command metadata, not executed builds.
- Visual content remains a review scaffold until a later editorial/design pass.
