# Lean Redesign Performance Verification

## Scope

This evidence verifies the currently deployed Home, Library, and Commerce data
paths using the isolated local UAT stack and synthetic data. It does not query
or mutate production data.

Run: `2026-08-22T17:57:04Z`
Launcher: `bash scripts/start_local_uat.sh`
API: `http://127.0.0.1:18005/api`

Each endpoint was requested five times with compressed responses enabled. The
listed p95 is the slowest of the five samples, which is conservative for this
small deterministic run.

| Surface | Initial calls | Compressed JSON | Local p95 | Budget | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Home | 2 | 2,758 B | 5.014 ms | <=2 calls, <=150 KB, cached p95 <=150 ms | PASS |
| Library | 2 | 34,762 B | 19.522 ms | <=2 calls, 24-card response <=100 KB, p95 <=350 ms | PASS |
| Commerce | 1 | 355 B | 1.749 ms | <=1 call, <=30 KB, p95 <=250 ms | PASS |

## Endpoint evidence

| Surface | Endpoint | Compressed bytes | p95 |
| --- | --- | ---: | ---: |
| Home | `/home/hero` | 1,986 B | 5.014 ms |
| Home | `/home/listening?limit=3` | 772 B | 2.219 ms |
| Library | `/books` | 27,584 B | 19.522 ms |
| Library | `/home/curated?compact=true` | 7,178 B | 12.922 ms |
| Commerce | `/payments/offers` | 355 B | 1.749 ms |

## Decision

The measured public surfaces meet the stated request-count, payload, and local
latency budgets. No additional public-performance refactor, database index, or
projection collection is justified. Existing route compatibility remains the
authoritative contract.
