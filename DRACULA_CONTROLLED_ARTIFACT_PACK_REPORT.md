# Dracula Controlled Artifact Pack Report

Generated: 2026-06-20

## Artifact Location

`data/controlled_publications/dracula/`

## Included Files

- `public_book.json`
- `reader_manifest.json`
- `approval_evidence.json`
- `source_evidence.json`
- `checksum_manifest.json`
- `chapters/chapter-001.json` through `chapters/chapter-027.json`

## Provenance

The pack is derived from existing approved Dracula controlled-publication artifacts:

- `APPROVED_TO_PUBLISH.md`
- `output/publication_candidates/dracula/source_evidence.json`
- `output/publication_candidates/dracula/dracula_gate_results.json`
- `output/book_import_golive_retry2/20260526T111622Z/metadata/dracula.json`

## Safety Claims

- Slug: `dracula`
- Title: `Dracula`
- Author: `Bram Stoker`
- Source: `Project Gutenberg eBook #345`
- Rights tier: `A`
- Verification status: `approved`
- QA status: `QA_PASSED`
- Approved to publish: `true`
- Source/content/provenance hashes are present in the artifact evidence.
- Chapter count: `27`
- Audio enabled: `false`
- Audiobook enabled: `false`

## Runtime Policy

The backend may use this artifact pack only for Dracula and only after validation passes. It must never enable audiobook assets, never apply to non-Dracula books, and never expose source hashes or rights internals through public APIs.

The fallback is self-contained for runtime truth gating:

- Runtime fallback does not require `output/publication_candidates/`.
- Runtime fallback does not require production MongoDB to already contain Dracula.
- Runtime fallback still requires checksum-valid `approval_evidence.json`, `source_evidence.json`, `reader_manifest.json`, and 27 chapter files.
- `load_dracula_artifact_book()` merges internal-only source, rights, approval, and traceability fields from the artifact evidence files before calling the truth gate.
- `public_book_projection()` and `PublicBookOut` strip private source URLs, source/content/provenance hashes, rights metadata, and audiobook internals from public API responses.
- `audio_enabled_slugs` remains empty, and the Dracula artifact always forces audiobook availability to `false`.
