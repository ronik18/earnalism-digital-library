# Sprint 1 Package-v2 Migration: Next Execute Packet

## Readiness status (as of latest local truth)
- Production package-v2 live: 10
- Private-B2 package-v2 live: 2
- Approved+QA titles still on non-private sources: 8 (if all migrate successfully, private-B2 live becomes 10)

Targets:
- radharani
- muchiram-gurer-jibanchorit
- book-d19e96859f
- book-f5d593e1f4
- book-edfcf810c5
- the-tell-tale-heart
- the-yellow-wallpaper
- the-necklace

## Required checks passed before execute
- `SPRINT1_CONTAINMENT_TARGETS_JSON` preflight and scoped dry-run executed successfully.
- Inventory SHA currently expected by script:
  - `21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c`
- Routing tests passed:
  - `backend/tests/test_b2_audiobook_routing.py`
  - `backend/tests/test_audiobook_package_v2_routes.py`
  - `backend/tests/test_redis_cache_policy.py`

## Execute (requires explicit approval + credentials)
Use exactly this command pattern for each title:

```
ALLOW_REMOTE_MUTATION=true \
OWNER_APPROVAL_TOKEN=AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT. \
REVIEWED_INVENTORY_SHA256=21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c \
B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true \
B2_ACCESS_KEY_ID=... \
B2_SECRET_ACCESS_KEY=... \
B2_S3_ENDPOINT=... \
B2_REGION=... \
B2_PRIVATE_QA_BUCKET=... \
B2_SOURCE_ACCESS_KEY_ID=... \
B2_SOURCE_SECRET_ACCESS_KEY=... \
B2_SOURCE_S3_ENDPOINT=... \
B2_SOURCE_REGION=... \
TARGET_SLUG=<slug> \
SPRINT1_CONTAINMENT_TARGETS_JSON=internal/audiobook_lab/storage_containment/sprint1_scoped_containment_targets.json \
bash internal/audiobook_lab/storage_containment/unapproved_direct_audio_remediation_commands.sh --execute-reviewed
```

Run once per slug above. Example:
- `TARGET_SLUG=radharani ... bash ... --execute-reviewed`

## Post-iteration validation after each batch
1) Re-run:
   - `python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json`
2) Confirm candidate drops from:
   - `live_not_private_b2_for_package_v2`
   - `can_expose_non_private`
   and increments `live_private_b2_count`.

## Batch-run command (wave driver)
- For a deterministic, validated sequence, use:
  `bash internal/audiobook_lab/storage_containment/run_sprint1_private_b2_wave1.sh --dry-run`
  (for safe preflight) and
  `bash internal/audiobook_lab/storage_containment/run_sprint1_private_b2_wave1.sh --execute-reviewed`
  once approval and credentials are supplied.

## Single-command batch flow (recommended)
Use this composite wrapper for precheck + migrate + postcheck:
`bash internal/audiobook_lab/storage_containment/run_wave1_with_validation.sh --dry-run`
`bash internal/audiobook_lab/storage_containment/run_wave1_with_validation.sh --execute-reviewed`
or pass a custom order/list of slugs as trailing arguments:
`bash internal/audiobook_lab/storage_containment/run_wave1_with_validation.sh --execute-reviewed radharani book-d19e96859f ...`

## End-to-end success condition (this wave)
- First practical milestone: all eight titles in this target list become private-B2 package-v2, not exposed from Cloudinary/public remotes.
- Current hard stop: private-B2 count moves from **2 -> 10** for package-v2 in `sprint1_package_v2_readiness.json` before broader sprint1 expansion.
- Ongoing sprint target after this: move toward 32 titles through the same safe gating path (release gate + QA + private migration).
