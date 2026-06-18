# Phase 4 Source Ingestion

Phase 4 adds a deterministic, dry-run source ingestion pipeline for public-domain text preparation. It does not publish books, upload assets, call paid APIs, or mutate production data.

## Purpose

The ingestion pipeline prepares source text only after rights and source metadata exist. It is designed to sit after Phase 2 rights verification and before any content generation, audiobook polishing, visual study material generation, or public publishing.

## Source Model

Each ingestion record includes:

- `source_url`
- `source_name`
- `source_license`
- `source_hash`
- `content_hash`
- `provenance_hash`
- `raw_text`
- `cleaned_text`
- `language`
- `chapter_segments`
- `ingestion_status`
- `ingestion_log`

Raw source text and cleaned reader-ready text are stored separately in memory. Local JSON reports include previews by default, not full source text, so routine dry-runs do not create large text artifacts unless explicitly requested.

## Connectors

Supported connector modes:

- `manual-text`: local plaintext import.
- `manual-url`: URL metadata hook when text is not yet attached.
- `project-gutenberg`: Project Gutenberg-compatible cleanup hook.
- `wikisource`: Wikisource-compatible cleanup hook.
- `scanned-pdf-placeholder`: placeholder for later OCR. It does not run OCR.
- `auto`: chooses a connector from the source URL and input text.

The default CLI sample does not fetch network content. Manual URL fetching is intentionally not enabled in this phase.

## Rights Guardrails

Ingestion is allowed only when:

- rights metadata is approved by the Phase 2 engine, or
- the record is pending-safe: Tier A or Tier B, source evidence is present, source license is not unsafe, and the only remaining blocker is publishing approval.

Ingestion is blocked when:

- `source_url`, `source_name`, or `source_license` is missing.
- the source license is restricted, unclear, non-commercial, or otherwise unsafe.
- rights tier is Tier C.
- a `blocked_reason` is present.
- the Phase 2 rights engine reports any substantive blocker.

## Hashing And Dedupe

- `source_hash` is the legacy source identity used for unchanged-source dedupe. In Phase 4 it is equal to `content_hash` for backward compatibility with existing dry-run calls.
- `content_hash` is a SHA-256 hash of normalized raw source text.
- `provenance_hash` is a SHA-256 hash of `source_url`, `source_name`, `source_license`, and `content_hash`.

If an existing source/content/provenance hash is supplied and matches the new source, the record status becomes `UNCHANGED` and `downstream_regeneration_required` is `false`.

## Cleanup

The cleanup layer:

- removes common Project Gutenberg boundary boilerplate,
- removes page/header/footer lines,
- normalizes whitespace,
- detects English and Bengali text,
- detects chapter headings,
- falls back to one `Full Text` segment when chapters are absent.

## Run

Safe sample:

```bash
npm run source:ingest
```

By default this writes metadata, hashes, character counts, chapter metadata, and text previews only.

Local book and text:

```bash
python3 scripts/source_ingestion.py \
  --book path/to/book-with-rights.json \
  --text-file path/to/source.txt \
  --output-dir output/source_ingestion
```

Include full raw and cleaned text only when the local reviewer explicitly needs it:

```bash
python3 scripts/source_ingestion.py \
  --book path/to/book-with-rights.json \
  --text-file path/to/source.txt \
  --include-text \
  --output-dir output/source_ingestion
```

Limit preview length:

```bash
python3 scripts/source_ingestion.py \
  --book path/to/book-with-rights.json \
  --text-file path/to/source.txt \
  --text-preview-chars 500 \
  --output-dir output/source_ingestion
```

Duplicate hash check:

```bash
python3 scripts/source_ingestion.py \
  --book path/to/book-with-rights.json \
  --text-file path/to/source.txt \
  --existing-hash "<sha256>" \
  --output-dir output/source_ingestion
```

## Outputs

The CLI writes:

- `output/source_ingestion/source_ingestion_report.json`
- `output/source_ingestion/source_ingestion_report.csv`
- `output/source_ingestion/source_ingestion_report.md`

These are local dry-run reports. They are not production publications.

The CLI is dry-run only. `--commit`, `--publish`, and `--write` are rejected.

## Limitations

- No OCR is performed.
- No external source is fetched by default.
- No downstream artifacts are generated.
- Human/legal review is still required before publishing any rights-sensitive content.
