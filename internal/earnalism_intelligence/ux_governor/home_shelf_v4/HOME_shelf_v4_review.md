# Home Shelf v4 review

## Implementation result

The Love card now uses a bounded Duo cover stage in a container-aware card body. Title, description, chips, covers, and CTA occupy separate functional zones. Adventure uses the same outer row height at desktop. Short Masterpieces is a full-width runway, and Selected Listening is a full-width premium rail when canonical approved audio exists.

## Responsive contract

- Desktop: explicit 12-column literary runway with Bengali 7/Gothic 5, Love 5/Adventure 7, Short full width, then audio full width.
- Tablet: explicit two-column areas with Bengali and Adventure spanning both columns.
- Mobile: explicit one-column areas; Short and audiobook content use bounded scroll-snap rails without page overflow.

## Validation state

Focused backend and frontend tests pass, the frontend production build passes, and the deterministic geometry audit reports zero modeled intersections/overflow. The full frontend suite is 23 suites / 111 tests; the focused backend release/home suite is 36 tests. The requested production screenshots and live endpoint canary remain pending: the protected Vercel preview reached sign-in before the application in the available browser surface. See `HOME_shelf_v4_scorecard.json`.

The repository’s canonical evidence currently exposes four approved audiobook records, including `the-open-window`; release truth was not changed. The brief names three approved records, so this discrepancy is recorded rather than silently hiding or publishing audio.

## Future-sprint and admin contract

Future titles join through canonical metadata (`editorial_shelf_ids`, `home_feature_eligible`, `home_shelf_rank`, `admin_pinned`, `popularity_score`, and `do_not_feature`). The runtime endpoint is `GET /api/home/curated`; React contains no Sprint title array. Editorial placement is admin-ready through `PATCH /api/admin/books/{slug}/home-curation`, which changes shelf membership/order/visibility fields only and explicitly returns `reader_audio_release_truth_unchanged: true`.

The remaining UI backlog is a small admin shelf editor for those fields plus shelf-level variant/max-visible preview. It must call the endpoint above and must not expose an audio override or mutate reader/audio release gates.

## Known baseline validation conflict

The broader `backend/tests/test_backend_catalog_truth.py` suite still asserts an older Dracula-only catalog, while the current checked-in `data/controlled_launch.json` and canonical artifacts intentionally contain the active multi-title catalog. Running that stale suite produces 10 assertion failures before/alongside this change. No release truth was weakened to make those assertions pass; the focused current home/release tests are the applicable evidence for this branch.

Cover audit note: `scripts/audit-book-covers.mjs` ran in the isolated checkout but found zero local book/cover assets, so it is recorded as an environment limitation, not as proof that the production cover catalog is complete.

Paid work was not invoked. The source checkout’s lock remains `status: active`, `current_holder: none`, `allowed_next_holders: []`; this branch did not modify it.
