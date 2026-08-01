# Unapproved Direct Audio Remediation Plan

## Status

This is a dry-run plan only. No Cloudinary/B2 object was changed, no release gate was mutated, and no deployment occurred.

- Reviewed inventory SHA-256: `21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c`
- Reachable unapproved/stale MP3 objects: **214**
- Reachable unapproved/stale sidecars: **392**
- Future atomic containment targets: **606**
- Protected current approved MP3 objects: **2**

## Containment Order

1. Freeze the reviewed inventory by SHA-256 and obtain the exact owner authorization token.
2. Confirm the destination B2 QA bucket is private and its lifecycle/retention policy is owner-approved.
3. Download each reviewed public object, record byte size and SHA-256, and upload it under an immutable containment object ID in the private QA bucket.
4. Verify private-copy size/checksum before touching public delivery.
5. Delete or revoke the original public Cloudinary/B2 object.
6. Poll the original URL until it returns 403 or 404.
7. Validate both approved API proxy endpoints still return 206 and all hidden controls remain disabled/404.
8. Remove unapproved direct URLs from public controlled-publication source in a separate reviewed PR, replacing historical URLs with object IDs/checksums where evidence must remain.

## Protected Approved Package Set

The future mutation script excludes these exact manifest-bound MP3 objects and their eight current sidecars:

- book-2b9853ec52: https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks/earnalism/audiobooks/book-2b9853ec52/book-2b9853ec52_mp3_a974819392d7.mp3
- a-ghost-story: https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks/earnalism/audiobooks/a-ghost-story/a-ghost-story_mp3_00190d747d28.mp3

Stale Cloudinary versions for approved slugs remain containment targets.

## Cloudinary

Required: CLOUDINARY_URL (or equivalent cloud name/API key/API secret) and the Python cloudinary package.

For video/upload MP3s, remove only the final delivery extension to derive public_id; a URL ending in .mp3.mp3 therefore retains the embedded .mp3. For raw/upload sidecars, retain the extension. After private-copy verification, use cloudinary.uploader.destroy(public_id, resource_type=resource_type, type='upload', invalidate=True).

## Backblaze B2

Required: B2_ACCESS_KEY_ID, B2_SECRET_ACCESS_KEY, B2_S3_ENDPOINT, B2_REGION, B2_PRIVATE_QA_BUCKET, B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true, and AWS CLI.

Bucket/key locators are recorded per object. Copy to the confirmed-private QA bucket, verify with head-object, then delete the original public key. The exact approved package URLs are excluded.

## Unknown Provider

No real unknown-provider object was found. Test/example URLs are excluded. Any unresolved locator or authentication condition becomes OWNER_STORAGE_ADMIN_REQUIRED and is skipped.

## Source Cleanup Classification

- PUBLIC_SOURCE_RISK: unapproved direct URL in backend/data or data controlled-publication source.
- PRIVATE_EVIDENCE_ONLY: internal evidence should retain a checksum/object ID, not public delivery URL.
- TEST_FIXTURE_SAFE: synthetic test URL.
- HISTORICAL_LEDGER_SAFE: preserve evidence through a redaction migration.
- NEEDS_REDACTION_OR_REPLACEMENT: owner review required.

## Exact Later Fix Prompt

P0_REMOVE_UNAPPROVED_DIRECT_AUDIO_REFERENCES_FROM_PUBLIC_SOURCE

Use unapproved_direct_audio_inventory.json at SHA-256 21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c. Remove unapproved/stale direct MP3 and sidecar URLs from backend/data/controlled_publications/**/public_book.json and data/controlled_publications/**/public_book.json. Preserve only the exact current approved packages for book-2b9853ec52 and a-ghost-story. Replace retained private/historical evidence URLs with stable containment object IDs, checksums, and private evidence references; do not delete evidence. Do not mutate release gates, expose Listen, run audio providers, touch paid_tts.lock, deploy, or alter unrelated frontend behavior. Add regression tests proving hidden manifests contain no provider/voice/URL/assets, hidden audio proxies return 404, approved proxy endpoints remain manifest-bound, and no unapproved direct storage URL remains in runtime controlled-publication data. Run focused backend release-truth tests, audioReleaseSafety tests, JSON validation, direct public-media scans, and git diff --check. Open a focused PR only after owner separately authorizes source cleanup.

## Required Owner Authorization Before Mutation

AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.

The owner must also confirm inventory SHA-256 21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c and explicitly approve all 606 reviewed MP3/sidecar containment targets after private retention verification.

## Execution File

unapproved_direct_audio_remediation_commands.sh is deliberately inert unless invoked with --execute-reviewed, the exact owner token, the reviewed inventory SHA-256, and private-bucket confirmation. It was not run in this dry-run.
