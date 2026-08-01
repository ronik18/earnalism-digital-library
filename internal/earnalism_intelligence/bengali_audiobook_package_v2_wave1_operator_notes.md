# Wave-1 Operator Notes (Sprint 1 private-B2 migration)

## Objective
Migrate the remaining approved+QA Sprint-1 titles from public/stale objects into private QA bucket without bypassing release gates.

## Approved target list
- radharani
- muchiram-gurer-jibanchorit
- book-d19e96859f
- book-f5d593e1f4
- book-edfcf810c5
- the-tell-tale-heart
- the-yellow-wallpaper
- the-necklace

## One-shot execution sequence (preferred)

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
export ALLOW_REMOTE_MUTATION=true
export OWNER_APPROVAL_TOKEN=AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.
export REVIEWED_INVENTORY_SHA256=21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true
export B2_ACCESS_KEY_ID=...
export B2_SECRET_ACCESS_KEY=...
export B2_S3_ENDPOINT=...
export B2_REGION=...
export B2_PRIVATE_QA_BUCKET=...
export B2_SOURCE_ACCESS_KEY_ID=...
export B2_SOURCE_SECRET_ACCESS_KEY=...
export B2_SOURCE_S3_ENDPOINT=...
export B2_SOURCE_REGION=...

bash internal/audiobook_lab/storage_containment/run_wave1_with_guard.sh --execute-reviewed
```

## Immediate validation

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json
bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh
```

Expected: live_private_b2_count must rise to 10 and nonprivate_exposed_count must be 0.

## Fallback / partial-failure recovery
- If command stops mid-run, rerun with remaining slugs:

```bash
bash internal/audiobook_lab/storage_containment/run_wave1_with_guard.sh --execute-reviewed <slug1> <slug2> ...
```

- Re-run precheck/postcheck between attempts.

## Hard constraints
- Do not change public routes/route logic during migration.
- Do not proceed without all required env values.
- Do not mix `TARGET_SLUG=` with `SPRINT1_CONTAINMENT_TARGETS_JSON` for per-title flow.

