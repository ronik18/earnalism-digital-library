# Catalog Truth Audit Runbook

## Purpose

Run a deterministic local audit proving the public backend catalog matches the
controlled launch truth: Dracula only, audio disabled, pipeline titles non-readable.

## Command

```bash
npm run owner:catalog-truth-audit
```

## Outputs

```text
output/daily/YYYY-MM-DD/catalog_truth_report.md
output/daily/YYYY-MM-DD/catalog_truth_matrix.csv
output/daily/YYYY-MM-DD/catalog_truth_report.json
```

## Pass Criteria

- `live_approved_count` is `1`.
- `dracula_only_live_approved` is `true`.
- `unapproved_reader_link_count` is `0`.
- `unapproved_audio_link_count` is `0`.
- `unapproved_sitemap_count` is `0`.
- Dracula audio is `false`.
- Kshudhita Pashan is `PIPELINE_CANDIDATE`.

## Hold Criteria

HOLD the launch or growth expansion if any of these occur:

- Any non-Dracula title is `LIVE_APPROVED`.
- Any non-Dracula title exposes a reader URL.
- Any title exposes audio while audio remains disabled.
- Any pipeline/unapproved title appears in sitemap.
- Any public projection leaks rights evidence, source hashes, source URLs, or audio storage URLs.

## Safety

This command is dry-run and local report only. It does not call external APIs, publish
content, enable audio, delete records, mutate production, or charge payments.
