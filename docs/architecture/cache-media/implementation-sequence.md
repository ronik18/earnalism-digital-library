# Implementation sequence and acceptance gates

All checkpoints require a clean worktree, regression relevant to their owned paths, `git diff --check`, no secret exposure, and a rollback note.

| Checkpoint | Permitted files | Gate | Approval boundary | Stop condition |
|---|---|---|---|---|
| A1 extraction | `backend/cache/**`, `backend/media/**`, tests | characterization parity | none | behavior differs |
| A2 codec | `backend/cache/**` | safe codec/migration tests | cache key migration review | corrupt/legacy incompatibility |
| A3 limits/metrics | cache and benchmark files | size guard/metrics | capacity threshold approval | no capacity evidence |
| A4 invalidation/singleflight | cache/services files | mutation and concurrent-miss tests | authorization semantics review | stale authorization risk |
| A5 audio hardening | `backend/media/**` | Range/HEAD/ETag/auth tests | protected delivery contract | memory/stream regression |
| A6 PDF | only after product exists | customer route tests | product approval | no active PDF product |
| A7 frontend | frontend after PR #344 | lifecycle/browser tests | PR #344 integrated | overlap/contract mismatch |
| A8 local benchmark | scripts/docs | repeatable local baseline | none | harness failure |
| A9 preview/staging | deployment config only after lanes converge | smoke/canary | deployment approval | staging unavailable |
| A10 production | merged main only | canary and metrics | explicit owner release approval | any release gate fails |
