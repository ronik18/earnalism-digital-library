# Parallel Go-Live Sprint Dashboard

Generated: 2026-07-07T16:33:36+05:30

## Global Locks

- Production metadata: `internal/earnalism_intelligence/locks/production_metadata.lock`
- Backend deploy/restart: `internal/earnalism_intelligence/locks/backend_deploy.lock`
- Paid TTS/provider calls: `internal/earnalism_intelligence/locks/paid_tts.lock`

## Lane Status

| Lane | Focus | Status | Cheapest safe next action |
| --- | --- | --- | --- |
| 1 | Bengali endpoint materialization for `book-2b9853ec52` | Endpoint materialized; browser gate blocked | Deploy current reader-manifest audio-control frontend, then rerun metadata/browser-only resume |
| 2 | 6 Bengali reader-only rights blockers | No mutation; requested script missing; latest evidence says repaired | Do not mutate unless production evidence shows regression |
| 3 | PR87 frontend preview readiness | Ship-ready | Owner may merge PR87; it does not include Reader manifest audio-control support |
| 4 | Next 3 Bengali canary prep | Prepared, no TTS | Use `bengali_next_3_canary_preflight.json` after pilot is live |
| 5 | English audiobook fallback preflight | Deferred | Skip unless higher-priority lanes are idle |

## Current Pilot Truth

- Pilot: `book-2b9853ec52` / `দুই বিঘা জমি`
- Upload/checksum: PASS
- Metadata: PASS via admin API
- ASR/source: PASS accepted by TTS-by-construction with supporting ASR
- Listening: 9.4 / confidence 0.95
- Sync: `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`
- Latest live API probe: detail/manifest audio enabled and audiobook endpoint returns 206
- Non-pilot Bengali sample checked: audio remains hidden
- Browser gate: BLOCKED because the production frontend bundle does not render the current reader-manifest audio controls.

## Independent Lane Findings

- PR87: GitHub checks PASS, Vercel PASS, protected preview validation PASS. Worktree has report-only local edits and an untracked smoke report; nothing was staged.
- Rights repair: `internal/audiobook_lab/scripts/bengali_reader_only_rights_repair.py` is absent. Latest intelligence says the six target slugs were already repaired, with 31 reader-only approved and 0 rights blockers. Public probes found no target slug exposing audiobook audio.
- Canary prep: selected `muchiram-gurer-jibanchorit`, `book-d19e96859f`, and `book-2ddbed8293` for post-pilot representative auditions only. Two need audiobook-clean opening stripping before TTS.

## Cost Controls

- No paid TTS ran in this coordination pass.
- No provider bakeoff ran.
- No image generation ran.
- No broad Bengali audiobook wave is allowed until the pilot browser gate passes.

## Validation Summary

- Endpoint branch: `python3 -m py_compile backend/server.py backend/catalog_truth.py && pytest -q backend/tests/test_bengali_pilot_endpoint_materialization.py` PASS, 7/7.
- Factory scripts: `py_compile`, stop-guard checks, and listening QA schema 3 checks PASS.
- Frontend: `npm ci --prefix frontend` PASS with existing warnings; audioReleaseSafety PASS 4/4; production build PASS.
- General: `git diff --check` PASS.
