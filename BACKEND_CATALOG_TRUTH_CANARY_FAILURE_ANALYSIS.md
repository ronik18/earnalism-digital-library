# Backend Catalog Truth Canary Failure Analysis

## Reproduction

Command run:

```bash
npm run launch:backend-catalog-truth-canary
```

Result: `HOLD`

Generated artifacts:

- `output/launch/backend_catalog_truth_canary/catalog_truth_report.json`
- `output/launch/backend_catalog_truth_canary/catalog_truth_report.md`
- `output/launch/backend_catalog_truth_canary/catalog_truth_matrix.csv`

## Production Failure Summary

The API-backed canary reported:

- `/books live readable slugs are []; expected ['dracula']`
- `/books does not contain Dracula as the live readable item`
- `Unapproved audio links detected`
- `Unapproved sitemap entries detected`
- `Backend/frontend controlled live slug mismatch`
- many non-Dracula books expose audio fields in `/books`

## Why Dracula Was Not Detected As Live Readable

Production `/api/books` returned a Dracula row, but the row was classified as `COMING_SOON` by the canary because the public API response did not expose the safe live-reader fields expected by the truth gate:

- `publication_status = LIVE_APPROVED`
- `reader_enabled = true`
- `preview_enabled = true`
- `reader_url = /reader/dracula`
- `preview_url = /reader/dracula`
- `audio_enabled = false`
- `audiobook_enabled = false`

The code path also queried MongoDB with strict rights metadata before the Python/file-backed Dracula approval evidence could be applied. If the production Dracula DB row lacks complete `rights_metadata`, `source_hash`, `content_hash`, or `provenance_hash`, the strict pre-query can exclude Dracula before `public_book_projection(book)` can mark it live approved.

## Which Fields Are Missing From Dracula API Projection

From the canary matrix, Dracula was returned as:

- `classification = COMING_SOON`
- `reader_enabled = False`
- `preview_enabled = False`
- `audio_enabled = False`
- `source_hash_present = False`
- `content_hash_present = False`
- `provenance_hash_present = False`

The fix fetches only controlled-launch candidate slugs, then applies the Python truth gate and file-backed Dracula evidence through `public_book_projection(book)`.

## Which Non-Dracula Fields Expose Audio

The canary detected truthy audio exposure across many non-Dracula `/books` rows. The fields considered unsafe include:

- `audio_enabled`
- `audiobook_enabled`
- `generate_audiobook`
- `audio_url`
- `audiobook_url`
- `audiobook.url`
- `audiobook_assets`
- `audiobook.assets`
- `audio_assets`
- `audio_files`
- `voice_url`
- `waveform_url`
- `b2_url`
- `cloudinary_audio`
- `narration_url`
- `listen_url`
- `has_audio`

The fix removes audiobook fields from the public book-list Mongo projection and keeps public projections limited to `audio_enabled=false`, `audiobook_enabled=false`, `audio_url=""`, and `audio_status`.

## Which Sitemap Entries Are Unapproved

The canary flagged `/book/dracula` as an unapproved sitemap entry because production classified Dracula as `COMING_SOON`. Once Dracula is projected as `LIVE_APPROVED`, `/book/dracula` becomes approved. The sitemap generator remains Dracula-only for book routes and excludes reader/audio/unapproved/demo routes.

## Why Backend/Frontend Slug Mismatch Occurred

Frontend controlled launch slugs resolved to `['dracula']`, while backend live approved slugs resolved to `[]` because production did not project Dracula as live readable. The fix adds `data/controlled_launch.json` as a shared controlled-launch config:

```json
{
  "live_approved_slugs": ["dracula"],
  "pipeline_slugs": ["kshudhita-pashan"],
  "audio_enabled_slugs": []
}
```

Backend catalog truth and sitemap generation read this file, while regression tests verify parity with frontend launch constants.

## Fix Summary

- Public `/api/books` now fetches only controlled-launch candidates and applies `public_book_projection(book)` before returning anything.
- Public lists no longer request raw audiobook fields from MongoDB.
- Dracula can be projected live approved using file-backed approval evidence when DB rights metadata lags.
- Reader detail, chapter, manifest, and audiobook endpoints verify `can_expose_reader` / `can_expose_audio` after fetch.
- Public cache truth version is bumped to `dracula-first-v2`.
- Backend/frontend controlled-launch config is shared through `data/controlled_launch.json`.
- Post-deploy `npm run launch:backend-catalog-truth-canary` remains mandatory before operational GO.

## Safety

No production data was mutated. No publication, audiobook enablement, provider call, email, social post, payment, or deploy was performed by this fix.
