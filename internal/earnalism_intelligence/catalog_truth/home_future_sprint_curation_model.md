# Future Sprint Home Curation Model

Home curation is metadata-first and release-truth-bound. A book may carry `release_cycle`/`sprint_id`, `editorial_shelf_ids`, `home_shelf_rank`, `home_featured`, `admin_pinned`, `do_not_feature`, `popularity_score`, `freshness_score`, `cover_valid`, and `cover_audit_status` in internal catalog state. Public payloads receive only customer-safe book metadata and canonical cover candidates.

Selection order is deterministic: admin pin, shelf rank, popularity, recent publication, then slug. A broken cover never becomes a visible card; the same shelf's reserve pool fills the slot after all candidate URLs fail.

Admin curation can pin/reorder Listening Rooms, pin genre titles, set shelf rank, set do-not-feature, preview Home, and set editorial tags. It cannot approve audio, alter QA or release gates, bypass cover audit, or bypass reader availability. No new admin UI is required for the current release.

Worked fixture simulation: Sprint 1 has 32 reader-live titles and the repository currently carries four canonical approved audiobook records (the brief names three; the discrepancy is recorded without mutation). A future Sprint 2 fixture adds reader-live Bengali/Gothic records and one approved Gothic audiobook. The backend payload automatically includes the eligible records and the frontend requires no title allowlist change.
