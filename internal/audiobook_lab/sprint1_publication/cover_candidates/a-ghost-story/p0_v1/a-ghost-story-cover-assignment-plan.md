# A Ghost Story controlled cover assignment plan

`PROPOSED_METADATA_ASSIGNMENT_NOT_LIVE`

The approved front and back candidates are staged in the private candidate namespace and are hash-bound in the adjacent JSON plan. No public title field, reader field, audiobook field, source, rights record, or Reading Pass configuration has changed.

## Exact later promotion scope

- Front fields: `cover_url`, `cover_image_url`, `coverImage`, `cover_image`, `thumbnail_url`, `blur_placeholder`, `dominant_color`, and `cover_dimensions.front`.
- Back fields: `back_cover_url`, `back_cover_image_url`, `backCoverImage`, `back_cover_thumbnail_url`, `back_cover_blur_placeholder`, `back_cover_dominant_color`, and `cover_dimensions.back`.
- The authoritative promotion mechanism derives these fields from the two immutable candidate records; it preserves all non-cover fields and records the former values for rollback.

## Before state

Both current URLs visibly and authoritatively belong to *Bharat at the Crossroads*. The exact former values are preserved in `a-ghost-story-cover-rollback.json`.

## Gate

Only `APPROVE_A_GHOST_STORY_ASSIGNMENT` permits canonical metadata promotion. It does not authorize merge or deployment.
