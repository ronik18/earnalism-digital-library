# Phase 5 Earnalism Edition Generator

Phase 5 adds a deterministic dry-run pipeline for value-added Earnalism editions. It does not generate full production books, publish content, call LLMs, call paid APIs, fetch network resources, run OCR, synthesize audio, or generate images.

## Purpose

The edition generator sits after Phase 4 source ingestion. It uses approved source metadata and cleaned public-domain text to prepare reviewable edition scaffolds before any expensive content-generation work begins.

## Templates

The pipeline defines templates and prompts for:

- clean reading edition
- chapter summary
- character map
- historical context
- glossary
- themes
- quiz
- 7-day reading plan
- teacher/parent notes
- why this book matters today
- audiobook-ready script
- SEO copy
- landing page copy
- social excerpts

Each template has a prompt string and a deterministic local renderer. The prompt inventory is present for future review and controlled model integration, but Phase 5 does not send prompts to any model.

## Generation State

Each result includes:

- `source_hash`
- `content_hash`
- `provenance_hash`
- `prompt_version`
- `model_version`
- `generated_at`
- `quality_score`
- `qa_status`
- `cache_key`

The cache key is derived from `source_hash`, `prompt_version`, and `model_version`. If a matching cache key is supplied, generation is skipped as `SKIPPED_UNCHANGED`.

## Required Gates

Phase 5 generation blocks before any section renderer runs unless all upstream gates are satisfied:

- Phase 2 rights: `rights_tier=A`, `verification_status=approved`, and no `blocked_reason`.
- Phase 3 demand priority: `action_status=READY_FOR_GENERATION`.
- Phase 4 ingestion: `ingestion_status=INGESTED` or `CLEANED`.
- Traceability: `source_hash`, `content_hash`, `provenance_hash`, `source_url`, `source_name`, and `source_license` are present.

Gate outcomes:

- Tier C: `BLOCKED_RIGHTS`
- missing or unknown rights: `BLOCKED_RIGHTS_REVIEW_REQUIRED`
- Tier B: `REGION_GATED_REVIEW`
- non-ready demand status: `BLOCKED_PRIORITY_GATE`
- incomplete ingestion: `BLOCKED_INGESTION`
- missing hashes/source metadata: `BLOCKED_TRACEABILITY`

## Cost Controls

The dry-run input supports:

- `max_sections_per_run`
- `max_generation_budget`
- skip unchanged source hash/model/prompt cache key
- dry-run default

The default npm command generates only a local fixture:

```bash
npm run edition:generate
```

Run against a local Phase 4-style payload:

```bash
python3 scripts/edition_generator.py \
  --input path/to/source-ingestion-payload.json \
  --max-sections-per-run 4 \
  --max-generation-budget 10000 \
  --output-dir output/edition_generation
```

Phase 4 preview-only payloads are intentionally rejected. For local dry-run generation, rerun Phase 4 with `--include-text` so `cleaned_text` is present.

Generate selected sections only:

```bash
python3 scripts/edition_generator.py \
  --input path/to/source-ingestion-payload.json \
  --section quiz \
  --section seo-copy
```

The CLI rejects `--commit`, `--publish`, and `--write`.

Full generated section content is excluded from JSON by default. Use this only for local review:

```bash
python3 scripts/edition_generator.py \
  --input path/to/source-ingestion-payload.json \
  --include-content \
  --content-preview-chars 1200
```

## QA

The QA layer checks:

- missing section detection
- hallucination-risk flag
- citation/source coverage
- readability score
- age-appropriateness flag

Low-quality or under-supported output is marked `BLOCKED_QA`. Partial output caused by budget or section limits is marked `NEEDS_MORE_RUNS` rather than published.

Every generated section also includes review metadata:

- `citation_required`
- `editorial_review_required`
- `source_coverage_status`
- `section_status`

Historical context, why-this-book-matters, landing page copy, SEO copy, and social excerpts always require editorial review.

## Outputs

The CLI writes local dry-run files:

- `output/edition_generation/edition_generation_report.json`
- `output/edition_generation/edition_generation_report.csv`
- `output/edition_generation/edition_generation_report.md`

These are scaffolds for review, not production content.

Reports include generation status, gate status, blocking reason, rights tier, demand action status, ingestion status, source/content/provenance hashes, prompt/model versions, QA status, quality score, section counts, and `dry_run=true`.

## Limitations

- The clean reading edition uses only a short preview scaffold and explicitly avoids full book generation.
- Historical context is conservative and requires later human/editorial citation review.
- Character maps and glossary terms are deterministic candidates, not final editorial output.
- Future model integration must stay behind dry-run, cache, budget, and QA gates.
