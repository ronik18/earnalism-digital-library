# P1 UAT tooling repair: root cause and review record

## Root cause

Classification: `DETACHED_EXACT_MAIN_PROVENANCE_UNSUPPORTED_AND_STATIC_UAT_COUNT_MARKERS_STALE`.

The System UAT reporter treated a symbolic `codex/*` branch and the latest
commit that changed an executable path as universal provenance authorities.
That rejects a clean detached checkout which is exactly the refreshed remote
authority under test. It also treated historical test totals as required log
substrings. When the test suites legitimately grew, the raw tests passed but
report finalization rejected their current passing summaries.

## Repair

- Provenance is now explicit and fail-closed. `ATTACHED_EXPECTED_BRANCH`
  requires the named branch, expected commit, expected tree, and clean tree.
  `DETACHED_EXACT_REMOTE_AUTHORITY` requires a branchless HEAD, an available
  expected commit object, exact commit/tree agreement, a refreshed named
  remote ref whose local value equals the expected commit, and a clean tree.
- The exact-main runner fetches `origin/main` before resolving and passing the
  expected commit/tree and remote-ref evidence to the reporter.
- Backend-core, backend-policy, and frontend-full store log-hash-bound,
  semantically named observed counts. Their deterministic parsers validate the
  terminal pytest or Jest summary and reject a missing, malformed, stale, or
  mismatched result. No fixed current suite total is a release condition.

## Sanitized repair review

Scope is limited to UAT provenance, runner orchestration, dynamic count
evidence, and focused tests. The repair does not alter production settings,
the Reading Pass runtime flag, deployment configuration, title data, routes,
entitlements, or customer-facing content. The records contain no credentials,
sensitive values, private URLs, or local filesystem paths.

## Required follow-up

Run the System UAT only in a newly created, clean, detached checkout at the
freshly fetched `origin/main` commit. A passing tooling suite is not
`CUSTOMER_READY`; it only makes the P1 exact-main preflight evidence truthful.
