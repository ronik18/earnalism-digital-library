# Open Window upload budget controls — implemented, not executed

Upload and replication CLI commands require the SAME --budget-ledger path. It is owner-only, exclusively locked, fsynced before requests/mutations and bound to the release descriptor. Do not delete/reset it or choose a fresh path to retry an ambiguous upload.

Shared ceilings: 2,000 instrumented API requests; 31,713,460 payload-download bytes; 15,856,730 uploaded bytes; 176 attempted new versions; plus 16,777,216 bytes reserved for Native API metadata response bodies (conservatively 1 MiB+1 per request). The metadata allowance is separate from the previously proposed payload-download budget and must appear in the next approval. S3 response-header/XML transport overhead is not metered byte-for-byte by this application wrapper; this is not a provider billing cap.

SDK automatic retries disabled with total_max_attempts=1. Multipart/deletion methods are not permitted by the budget gateway. Object mutation attempts are identified by hashed bucket/key pairs; failed/uncertain calls retain their budget reservation and cannot be retried with the same ledger. Raw adapter PUT fails without an active durable budget. GET bodies reserve the declared ContentLength before any application-level body read and bound reads to that length. Provider transfer can begin before application reads; this does not promise a network-level packet cap. Full-download hash and planned-size checks remain mandatory.

Existing immutable-key, local-hash, production-status, privacy, retention, independent-DR and receipt checks remain unchanged. Unversioned HEAD absence behavior remains a separate unresolved gate. Do not run uploads until exact adoption/rights and the readback/absence handling, account tariffs, pinned private owner runner and approved cost envelope are qualified. No trust gates were relaxed.

Tests: 16 budget tests and 28 existing storage tests PASS with dummy clients only. Tests include persisted primary+DR totals, uncertainty/no-retry, request/upload/version/download and metadata budgets, process lock, descriptor drift and unbudgeted PUT denial.

No upload, installation, deployment, credentials or activation performed. Auto-deploy remains held off. Previously pinned owner qualification manifests reference the old adapter hash and must not be silently updated or executed as if unchanged.

Review hardening: unknown operation names are denied; mutation-history hashes/counts are validated on reopen; ledger directory entry fsynced before execution. Reviewed total: 44 focused tests PASS.
