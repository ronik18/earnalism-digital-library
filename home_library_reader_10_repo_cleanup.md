# Home, Library, Reader/Audiobook 10/10 Repo Cleanup

Generated: 2026-07-07T18:20:00Z

## Source Files Intentionally Changed

- `frontend/src/pages/Reader.jsx`
- `home_library_reader_10_audit.json`
- `home_library_reader_10_scorecard.json`
- `home_library_reader_10_evidence.md`
- `home_library_reader_10_repo_cleanup.md`

## Policy/Memory Files Intentionally Updated

- `internal/earnalism_intelligence/ux_governor/ux_decision_ledger.jsonl`
- `internal/earnalism_intelligence/ux_governor/ux_sprint_learnings.md`
- `internal/earnalism_intelligence/decision_ledger.jsonl`
- `internal/earnalism_intelligence/sprint_learnings.md`

## Generated Files To Exclude Unless Intentionally Reviewed

- `frontend/build/`
- `frontend/public/sitemap.xml`
- `graphical_cover_generation_report.json`
- `ux_visual_regression_report.json`
- screenshots
- traces/videos
- release-gate outputs
- generated audio/sidecars
- signed URLs
- local npm logs

## Dependency Hygiene Note

`npm ci --prefix frontend` stalled during dependency resolution and left `frontend/node_modules` incomplete. Follow-up should restore dependencies from a clean worktree or use a known-good npm/Node pairing before rerunning validation.

## Merge Readiness

Not merge-ready until required frontend validation passes.
