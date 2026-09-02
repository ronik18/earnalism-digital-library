# Implementation sequence and acceptance gates

All checkpoints require a clean worktree, regression relevant to their owned paths, `git diff --check`, no secret exposure, and a rollback note.

| Checkpoint | Permitted files | Gate | Approval boundary | Stop condition |
|---|---|---|---|---|
| A1 extraction | `backend/cache/**`, `backend/media/**`, tests | characterization parity plus a fully adjudicated, reproducible A0 baseline | none | behavior differs or baseline is not green |
| A2 codec | `backend/cache/**` | safe codec/migration tests | cache key migration review | corrupt/legacy incompatibility |
| A3 limits/metrics | cache and benchmark files | size guard/metrics | capacity threshold approval | no capacity evidence |
| A4 invalidation/singleflight | cache/services files | mutation and concurrent-miss tests | authorization semantics review | stale authorization risk |
| A5 audio hardening | `backend/media/**` | Range/HEAD/ETag/auth tests | protected delivery contract | memory/stream regression |
| A6 PDF scope closure | docs/tests only when no product exists | inventory and binary-exclusion tests | none | PDF_CUSTOMER_DELIVERY_NOT_APPLICABLE |
| A7 frontend | frontend after PR #344 | lifecycle/browser tests | PR #344 integrated | overlap/contract mismatch |
| A8 local benchmark | scripts/docs | repeatable local baseline | none | harness failure |
| A9 preview/staging | deployment config only after lanes converge | smoke/canary | deployment approval | staging unavailable |
| A10 production | merged main only | canary and metrics | explicit owner release approval | any release gate fails |

A1 is interface extraction only: it makes no optimization claim and may not alter cache keys, Redis behavior, serialization, audio delivery, or release truth. A2 owns unsafe-pickle migration, A3 owns value-size guard and metrics, and A4 owns invalidation/singleflight. Production metrics remain a staging/release requirement, not an A1 prerequisite.
