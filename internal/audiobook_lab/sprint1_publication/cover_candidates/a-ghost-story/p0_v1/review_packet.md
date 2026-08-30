# A Ghost Story controlled cover-assignment review

The prior live pair was **WRONG_TITLE_ART**: both files visibly belong to *Bharat at the Crossroads* and match its authoritative Cloudinary mapping. Following `APPROVE_A_GHOST_STORY_ASSIGNMENT`, the exact approved pair is canonical in the repository-controlled mirrors; reader, audio, rights, publication, and Reading Pass state remain unchanged pending normal PR merge and deployment.

- Title/author: **A Ghost Story** — **Mark Twain**
- Rights: tier A; Mark Twain died 1910; first published 1875. Public domain in India and the U.S.
- Proposed front SHA-256: `d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742`
- Proposed back SHA-256: `baa45f507dda0926dfeeb219430a8ecd580d53eec43fbdda66aaa0c7fa2a2400`
- Existing rollback pair: `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779436724/earnalism/covers/front/cover_446c5658-2bdd-4bd6-afbe-f5233f280508.png` and `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779436737/earnalism/covers/back/back_cover_446c5658-2bdd-4bd6-afbe-f5233f280508.png`
- Owner-review artifact: `owner-review-board.png` (current wrong pair, approved pair, native-resolution front/back, thumbnail crop, blur preview, and Library/Book Detail/locked Listener desktop/mobile placement contexts). The board remains historical review evidence; production deployment has not yet occurred.
- Routed-component contract: `backend/tests/test_a_ghost_story_cover_assignment_plan.py` validates immutable assets and non-cover safety; `frontend/src/lib/aGhostStoryCoverAssignment.test.js` validates exact staged metadata through `BookCoverImage` source resolution and asserts its use by Library, Book Detail, and locked Listener surfaces.

## Gate

`CANONICAL_PROMOTED_PENDING_PR_MERGE`

`APPROVE_A_GHOST_STORY_ASSIGNMENT` authorized the canonical assignment through the repository mechanism. The corrected mirrors await PR merge and normal deployment; public production remains unchanged.
