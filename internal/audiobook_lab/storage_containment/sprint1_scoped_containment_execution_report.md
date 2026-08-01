# Sprint 1 Scoped Storage Containment Execution Report

## Result

**SPRINT1_STORAGE_BYPASS_CONTAINED**

The raised private B2 cap passed the Railway write/head/delete probe. The 70 remaining reachable Sprint 1 stale/unapproved Cloudinary objects were copied to the confirmed-private QA bucket, verified by size and SHA-256 metadata, revoked from public delivery, and independently reprobed at HTTP 404.

- Inventory SHA-256: `21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c`
- Active Sprint 1 slugs: **32**
- Deferred exclusions: `great-expectations`, `jane-eyre`
- Reviewed Sprint 1 objects: **135**
- Newly executed targets: **70**
- Newly retained bytes: **219,315,085**
- Newly retained objects: **6 MP3 + 64 sidecars**
- Previously retained and inaccessible: **35**
- Scoped objects now privately retained and inaccessible: **105**
- Already inaccessible without matching private-retention evidence: **30**
- Exact current approved package objects protected: **10**
- Non-Sprint reviewed targets deferred: **471**

## Execution

The initial local Railway-injected upload stalled on the first 4 MB transfer. It was interrupted before the executor wrote a mutation record or revoked the source; the source still returned 206 and no deterministic private destination existed. The operation was then run inside the Railway service container so both source retrieval and private retention remained cloud-to-cloud.

- Run ID: `storage-containment-306318ac3882`
- Started: `2026-07-14T02:50:04Z`
- Completed: `2026-07-14T02:57:28Z`
- Selected: **70**
- Private-copy verified: **70**
- Public delivery revoked: **70**
- Failures: **0**
- Mutation ledger SHA-256: `abbf9db41f5ac49d7d27ac561ea4ffbdc2b1bae7b5529ad86e5497b905c5f386`

The mutation ledger object IDs exactly match the scoped target list. An independent B2 HEAD pass confirmed all 70 destination objects have the expected size, `source-sha256`, and `source-object-id` metadata.

## Production Controls

Approved controls passed after mutation:

| Slug | Manifest | Release gate | QA | Range proxy |
|---|---|---|---|---:|
| book-2b9853ec52 | enabled | APPROVED | QA_PASSED | 206 |
| a-ghost-story | enabled | APPROVED | QA_PASSED | 206 |

The approved range responses remained `bytes 0-1023/5233965` and `bytes 0-1023/7047789`, respectively.

Hidden controls passed for `bn-066`, `book-d19e96859f`, `book-f5d593e1f4`, `muchiram-gurer-jibanchorit`, `the-open-window`, and `dsires-baby`: each manifest remains audio-disabled with empty public audio fields and each audiobook proxy returns 404.

The final 135-object scoped reprobe returned:

- HTTP 404: **135**
- Remaining reachable Sprint 1 direct objects: **0**

No non-Sprint object ID appeared in the mutation ledger. No release gate, Listen state, source record, or `paid_tts.lock` state changed.

The temporary Railway SSH key and all local/remote scratch files used for the cloud-to-cloud run were removed after verification. Railway reports no registered SSH keys.

## Residuals

- `30` scoped URLs were already inaccessible before this run but have no matching private-retention evidence in the reviewed ledger. This is a retention-evidence gap, not a live public storage bypass.
- Non-Sprint remote containment remains `NONSPRINT_REMOTE_CONTAINMENT_DEFERRED_BY_OWNER` for the separately reviewed 471-object scope.
- Sprint 1 runtime/public source files still contain stale direct URL references. Cleanup is intentionally deferred to the prepared `P0_REMOVE_SPRINT1_UNAPPROVED_DIRECT_AUDIO_REFERENCES_FROM_PUBLIC_SOURCE` prompt.

## GO LIVE Implication

`SPRINT1_STORAGE_BYPASS_CONTAINED`

The Sprint 1 direct-storage release-truth blocker is contained. This result does not approve any new audiobook, expose Listen, or alter the release-gate status of any title.

## Validation

- frozen inventory SHA: PASS
- scoped JSON validation: PASS
- executor Python compile and shell syntax: PASS
- scoped/full/canary dry runs: 70 / 606 / 5 targets
- backend B2 routing: 5/5 PASS
- backend applicable release-gate tests: 12/12 PASS
- frontend audio release safety: 4/4 PASS
- public media file scan: PASS, zero audio files
- static `/audio/` production probes: API 404, web 404
- `git diff --check`: PASS
- temporary Railway access cleanup: PASS
- `paid_tts.lock`: unchanged

Source cleanup requires separate owner authorization.
