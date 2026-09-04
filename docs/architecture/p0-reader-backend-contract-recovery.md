# P0 Reader Backend Contract Recovery

Status: `BACKEND_PR_IMPLEMENTING`
Baseline captured: 2026-09-04

## Rollback baseline

- Rollback PR: #348, merged as `23702561124845aab1a14b383f1e9f1ff4292842`.
- Historical failed repair: #346, merged as `4d13fd4fecb63c3d133097652dbd995493fd751d`; it is diagnostic material only.
- Canonical implementation worktree: `/private/tmp/earnalism-main-approved-integration`.
- Current implementation base: `23702561124845aab1a14b383f1e9f1ff4292842`.
- The retained rollback commit is an ancestor of current `origin/main`; no reset was performed.

Read-only production checks at the baseline confirmed Home, Library, Dracula
Book Detail, and Frankenstein Book Detail. The public API returned distinct
Dracula, Frankenstein, and Jekyll-and-Hyde IDs and slugs; their reader
manifests carried matching `book.slug` values. No authenticated request,
wallet mutation, payment, protected-page request, or production cache mutation
was made.

## Reproduced CORS/cache failure

The production API accepted a preflight from `https://theearnalism.com`, but a
subsequent `GET /api/books/frankenstein` from
`https://www.theearnalism.com` received a cached
`Access-Control-Allow-Origin: https://theearnalism.com` header. The response
also carried `Vary: Origin` and a Railway shared-cache hit/stale marker. A
browser at the `www` origin must reject that response. This is the confirmed
failed-repair CORS chain: a dynamic CORS response was eligible for a cache that
did not preserve the Origin variant. It is not an allowlist-wide-open issue.

PR A therefore marks every Origin-bearing API response `private, no-store`.
The explicit two-origin production allowlist remains in place, while the
backend's internal metadata cache remains available for identity-validated,
release-safe payloads.

## Redis inventory and PR A boundary

| Family | Current key material | Sensitivity | PR A action |
| --- | --- | --- | --- |
| public metadata | `public-cache` generation plus hashed `book_detail` key | public metadata | require matching title identity and release version |
| reader metadata | `reader-content` `book-access:*:{slug}` | reader release metadata | require matching slug before reuse |
| reader manifest | `reader-manifest` `book-manifest:*:{slug}` | public metadata plus access state | require matching book slug and release version |
| chapter body | `reader-content` `chapter-content:*:{slug}:{chapter}` | public preview or protected reader text | remove shared Redis reads and writes |
| legacy preview response | `public-cache` `reader_preview_chapter:*` | can contain a whole chapter | remove shared cache reads and writes; no-store response |
| audiobook package manifest | `reader-manifest` `audiobook-package:{slug}:{version}` | protected release metadata | bind cache key and payload to title identity |
| wallet authority | user wallet cache | entitlement-adjacent | retain cache for non-authoritative displays only; reader authorization uses `ReadingPassService.wallet_state` |

No production Redis scan or deletion has been performed. Legacy eviction stays
out of scope until a merged, deployed PR A proves that no full chapter body is
written to shared Redis and produces a bounded deletion manifest.

## Concurrent Redis work

The preserved concurrent branch is `codex/cache-media-architecture-baseline`
at `adc5404be5e97f3b0634672d94f7bb2bd77bdd19`; its open draft PR is #345.
It changes broad cache/media modules and overlaps `backend/server.py`, reader
manifest caching, audiobook routing, and reader frontend code. It remains
analysis-only for this incident and must realign to the final recovered main
commit before overlapping work resumes.

## Required pre-merge evidence

Run the focused CORS, cache, Reading Pass, protected-content, and audiobook
package contract suites on the final commit, then bind the command, result,
runtime, log path, and SHA-256 in the incident evidence manifest. Do not open
the frontend PR until the merged PR A deployment has passed production CORS and
two-title identity checks.
