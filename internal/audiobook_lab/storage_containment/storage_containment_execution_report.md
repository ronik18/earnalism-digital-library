# Storage Containment Execution Report

## Verdict

**BLOCKED_PRIVATE_BUCKET_STORAGE_CAP**

The bn-066 canary passed, so the full frozen 606-target run started. It stopped fail-closed when the confirmed-private B2 QA bucket rejected four multipart uploads with `AccessDenied: storage cap exceeded`.

- Reviewed targets: **606**
- Retained privately and SHA-tagged: **179**
- Old URLs now 403/404: **179**
- Remaining reachable URLs: **427**
- Private retained bytes: **4,068,062,849**
- Incomplete multipart uploads: **0**
- Failed-object deletions: **0**
- Approved proxy regressions: **0**
- Hidden-title regressions: **0**

## Canary

The `bn-066` canary retained five objects, verified byte size and source SHA-256 metadata, revoked the old B2/Cloudinary delivery, and confirmed all five old URLs return 404. Both approved proxies remained 206 and bn-066 remained disabled/404.

## Full Run

The full executor validated the complete frozen target universe before dividing it into disjoint shard counts of 152, 152, 151, and 151. Every successful object followed the same invariant:

1. Download the reviewed public object.
2. Compute byte size and SHA-256.
3. Upload to the confirmed-private QA bucket.
4. Verify private size and SHA metadata.
5. Revoke/delete only the old public object.
6. Poll until the old URL returns 403/404.

The private object-ID set exactly matches the 179 post-probe-inaccessible target IDs. All 179 objects have positive size and source SHA metadata.

Four Cloudinary source objects reached the upload stage but were not deleted because private upload verification failed at the storage cap. The executor stopped each shard immediately; it did not retry after the capacity error.

## Production Controls

- `book-2b9853ec52`: enabled, `APPROVED`, `QA_PASSED`, range proxy **206**.
- `a-ghost-story`: enabled, `APPROVED`, `QA_PASSED`, range proxy **206**.
- `bn-066`, `book-d19e96859f`, `book-f5d593e1f4`, `muchiram-gurer-jibanchorit`, `the-open-window`, and `dsires-baby`: audio disabled with empty public fields and proxy **404**.

No release gate, Listen state, application source, or `paid_tts.lock` was changed.

## Required Capacity Action

Increase the confirmed-private B2 QA bucket/account storage cap to at least **10 GiB**. The frozen set requires at least 5,341,752,636 known bytes, while some remaining sidecars do not provide a reliable `Content-Length`. Do not delete retained evidence to make space.

After the cap increase, rerun the same hash-bound full executor. It is idempotent: the 179 contained objects will be verified and skipped, and only the remaining 427 targets will transfer.

## Source Cleanup

Source cleanup remains separately gated. The exact 98 `PUBLIC_SOURCE_RISK` files and follow-up prompt are in `internal/audiobook_lab/storage_containment/P0_source_cleanup_prompt.md`.
