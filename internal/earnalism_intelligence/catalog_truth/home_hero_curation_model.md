# Home Hero Curation Model

## Purpose

`backend/data/home_hero_curation.json` is a small editorial ordering layer for the premium home hero. It references canonical Sprint 1 slugs; it never owns public title, author, cover, reader, rights, or audiobook truth.

## Supported editorial fields

Each slug entry may use:

- `hero_pinned`: place an eligible book ahead of unpinned books.
- `hero_rank`: deterministic pinned order; lower values rank first.
- `do_not_feature`: exclude an otherwise eligible title from hero and shelf selection.
- `shelf_rank`: deterministic fallback shelf order.
- `popularity_score`: optional aggregate, privacy-safe popularity signal.
- `editorial_badge`: optional reader-facing badge, with canonical language fallback.
- `updated_at`: ISO-8601 editorial timestamp.
- `updated_by`: non-public administrative actor label.

## Selection order

1. Start with the exact 32 configured Sprint 1 active slugs.
2. Resolve each slug through `first_controlled_artifact_dir` and canonical controlled-publication data.
3. Require canonical reader exposure and an exact title, author, and safe front-cover URL.
4. Remove `do_not_feature` entries.
5. Sort pinned records by `hero_rank`, then unpinned records by descending `popularity_score`, then `shelf_rank`, then slug.
6. Deduplicate by slug and apply deterministic collection limits.

## Non-overridable gates

Admin curation cannot:

- enable a reader or bypass controlled-publication availability;
- approve or expose audio;
- add an audiobook URL;
- override rights or cover evidence;
- synthesize a title, author, or public cover;
- add a non-Sprint 1 slug to this contract.

Audio fields are always projected from `backend/catalog_truth.py`. A title receives Listen only when canonical audio exposure passes, release state is approved, QA is passing, and the audiobook URL is the same-origin reader API route. All other titles receive Start Reading and omit `audiobook_url`.

## Popularity readiness

`popularity_score` is optional. The current payload has no aggregate metric, so the deterministic pinned/editorial order is authoritative. A future metric must be aggregate and privacy-safe; individual reading history, identity, email, or raw event trails must never enter this file or the public payload.

## Change control

Editorial changes require focused curation tests. Audio approval changes belong to the existing audiobook release pipeline and must not be made through this model.
