# UX Rebirth Repo Cleanup

Generated: 2026-07-06

## Source Files Changed For UX Pass

- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/audioReleaseSafety.test.js`
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/components/AudioPlayer.css`
- `frontend/src/components/FirstVisitSiteTour.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/index.css`
- `frontend/scripts/generate-static-seo-snapshots.mjs`

## Documentation Added

- `sprint_go_live_dashboard.md`
- `ux_rebirth_audit.md`
- `earnalism_luxury_design_system.md`
- `earnalism_luxury_ux_index.json`
- `ux_rebirth_evidence.md`
- `ux_rebirth_repo_cleanup.md`
- `frontend_luxury_sprint_report.md`

## Generated Files Not For Commit

- `frontend/build/`
- `output/ux-rebirth/*.png`
- `output/ux-rebirth/*.json`
- release-gate run folders, audio, sidecars, logs, traces, and caches.

## Validation Run

- `npm --prefix frontend run build` - PASS
- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` - PASS
- Local production static route curl checks for `/`, `/library/`, `/book/dracula/`, `/reader/dracula/` - PASS HTTP 200
- Playwright via system Chrome route smoke - PASS with local CORS limitations documented
- axe-core WCAG 2 A/AA subset - PASS on locally renderable routes

## Merge Readiness

Not merge-ready as-is because the worktree contains many unrelated dirty files from prior catalog/book work. Stage only the UX source/docs above after reviewing diffs. Do not stage generated build output or `output/ux-rebirth`.

## Risks

- Same-origin deployed validation is still required for API-backed book and reader pages.
- Reader content should remain API-controlled unless a future approved static reader manifest path is added.

## Graphical Covers + Calm Typography Follow-Up

Keep source/docs if selected:

- `frontend/src/lib/bookCoverResolver.js`
- `frontend/src/lib/images.js`
- `frontend/src/components/BookCoverImage.jsx`
- `frontend/src/components/ShelfTwoSlideshow.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/index.css`
- `frontend/src/lib/api.js`
- `frontend/public/index.html`
- `frontend/scripts/audit-book-covers.mjs`
- `frontend/scripts/visual-luxury-smoke.mjs`
- `internal/audiobook_lab/scripts/generate_graphical_book_covers.py`
- `internal/earnalism_intelligence/cover_acceptance_policy.json`
- `graphical_covers_calm_type_plan.json`
- `graphical_covers_repo_cleanup.md`

Do not stage generated artifacts:

- `frontend/build/`
- `/tmp/earnalism-graphical-covers-*`
- release-gate outputs, audio, sidecars, dashboards, logs, screenshots, caches, signed URLs.

Latest validation: build PASS, audio safety PASS, cover audit PASS, visual smoke PASS, git diff check PASS, Lighthouse PARTIAL at performance 90 / LCP 3.6s.
