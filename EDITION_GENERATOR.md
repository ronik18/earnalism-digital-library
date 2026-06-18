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
- `prompt_version`
- `model_version`
- `generated_at`
- `quality_score`
- `qa_status`
- `cache_key`

The cache key is derived from `source_hash`, `prompt_version`, and `model_version`. If a matching cache key is supplied, generation is skipped as `SKIPPED_UNCHANGED`.

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

Generate selected sections only:

```bash
python3 scripts/edition_generator.py \
  --input path/to/source-ingestion-payload.json \
  --section quiz \
  --section seo-copy
```

The CLI rejects `--commit`, `--publish`, and `--write`.

## QA

The QA layer checks:

- missing section detection
- hallucination-risk flag
- citation/source coverage
- readability score
- age-appropriateness flag

Low-quality or under-supported output is marked `BLOCKED_QA`. Partial output caused by budget or section limits is marked `NEEDS_MORE_RUNS` rather than published.

## Outputs

The CLI writes local dry-run files:

- `output/edition_generation/edition_generation_report.json`
- `output/edition_generation/edition_generation_report.csv`
- `output/edition_generation/edition_generation_report.md`

These are scaffolds for review, not production content.

## Limitations

- The clean reading edition uses only a short preview scaffold and explicitly avoids full book generation.
- Historical context is conservative and requires later human/editorial citation review.
- Character maps and glossary terms are deterministic candidates, not final editorial output.
- Future model integration must stay behind dry-run, cache, budget, and QA gates.
