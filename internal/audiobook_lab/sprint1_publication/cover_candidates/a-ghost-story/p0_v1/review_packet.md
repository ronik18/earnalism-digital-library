# A Ghost Story controlled cover-assignment review

The live pair is **WRONG_TITLE_ART**: both files visibly belong to *Bharat at the Crossroads* and match its authoritative Cloudinary mapping. The approved pair is privately staged, not canonical, and has made no reader, audio, rights, publication, or public-metadata mutation.

- Title/author: **A Ghost Story** — **Mark Twain**
- Rights: tier A; Mark Twain died 1910; first published 1875. Public domain in India and the U.S.
- Proposed front SHA-256: `d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742`
- Proposed back SHA-256: `baa45f507dda0926dfeeb219430a8ecd580d53eec43fbdda66aaa0c7fa2a2400`
- Existing rollback pair: `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779436724/earnalism/covers/front/cover_446c5658-2bdd-4bd6-afbe-f5233f280508.png` and `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779436737/earnalism/covers/back/back_cover_446c5658-2bdd-4bd6-afbe-f5233f280508.png`
- Owner-review artifact: `owner-review-board.png` (current wrong pair, proposed pair, native-resolution front/back, thumbnail crop, blur preview, and proposed Library/Book Detail/locked Listener desktop/mobile placement contexts). Every proposed surface is labeled `PROPOSED_METADATA_ASSIGNMENT_NOT_LIVE`.
- Routed-component contract: `backend/tests/test_a_ghost_story_cover_assignment_plan.py` validates immutable assets and non-cover safety; `frontend/src/lib/aGhostStoryCoverAssignment.test.js` validates exact staged metadata through `BookCoverImage` source resolution and asserts its use by Library, Book Detail, and locked Listener surfaces.

## Gate

`OWNER_A_GHOST_STORY_ASSIGNMENT_APPROVAL_REQUIRED`

`APPROVE_A_GHOST_STORY_ART` authorized only authenticated private candidate upload. Only `APPROVE_A_GHOST_STORY_ASSIGNMENT` may authorize canonical assignment. Until then, public cover fields remain unchanged.
