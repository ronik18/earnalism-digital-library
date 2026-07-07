# Repo Cleanup Report

## PR87 Blocker Rescue

Generated validation outputs were excluded from the PR scope:

- `frontend/build/`
- `book_cover_audit_report.json`
- `book_cover_audit_report.csv`
- `ux_visual_regression_report.json`
- Lighthouse JSON under `/tmp`
- visual smoke screenshots under `/tmp`

Remaining changes are source/config/test/docs only. No release-gate run folders, audio files, sidecars, screenshots, traces, caches, signed URLs, or secrets are present in the working tree.

## Merge Hygiene

Use explicit `git add` paths only. Do not use `git add .`.
## Bengali Endpoint Materialization Source Package

- Clean worktree: `/private/tmp/earnalism-bengali-endpoint-materialization`.
- Changed source/config: `backend/catalog_truth.py`, `backend/server.py`, `data/controlled_launch.json`, `backend/data/controlled_launch.json`.
- Added test: `backend/tests/test_bengali_pilot_endpoint_materialization.py`, including non-pilot Bengali manifest audio-hidden coverage.
- Added concise reports: `book_2b9853ec52_endpoint_materialization_plan.json`, `book_2b9853ec52_controlled_launch_source_report.json`, `bengali_endpoint_source_promotion_report.json`.
- Excluded generated artifacts: release_gate folders, generated audio, sidecars, logs, traces, screenshots, caches, signed URLs, secrets.
- Validation: backend py_compile PASS; targeted endpoint materialization/safety pytest PASS; `git diff --check` PASS.
- Production cache note: reader-manifest cache version includes `runtime_audio_requires_materialization=true` so stale non-pilot audio manifests are bypassed after deploy.
- Known unrelated test debt: older catalog tests still assert Dracula-only launch and fail against the current 63-title controlled-launch data.
- Additional endpoint/browser reports kept source-only: `book_2b9853ec52_endpoint_materialization_verification.json`, `book_2b9853ec52_browser_gate_frontend_blocker.json`.
- Backend deploys were run from `/private/tmp/earnalism-bengali-endpoint-materialization/backend`, not from the dirty sprint workspace.
- Generated release-gate outputs, audio, sidecars, logs, screenshots, caches, signed URLs, and secrets remain excluded.
