# Book Card Truth Gate Report

Status: `PASS`

Implementation:

- `frontend/src/lib/controlledLaunch.js` defines `LIVE_APPROVED_SLUG = dracula`.
- `frontend/src/components/BookCard.jsx` derives `LIVE_APPROVED` or `COMING_SOON_PIPELINE`.
- Only Dracula can render reader/revenue CTAs.
- Non-Dracula cards render Coming Soon / Notify Me only.
- Backend public APIs and reader helpers gate public book access to Dracula with Tier A approved rights.

Tests:

- Static regression validates the book-card truth gate.
- Backend tests validate the controlled public book query and allowed slug.
