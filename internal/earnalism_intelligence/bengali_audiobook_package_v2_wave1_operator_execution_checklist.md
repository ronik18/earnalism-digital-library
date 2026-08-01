# Wave-1 Storage Containment Operator Checklist (Immediate Action)

## Current objective
Migrate 8 remaining `can_expose=True`, `live_approved=True` but non-private audiobook titles to private B2 and keep all release gates intact.

## Exact slug targets
- `radharani`
- `muchiram-gurer-jibanchorit`
- `book-d19e96859f`
- `book-f5d593e1f4`
- `book-edfcf810c5`
- `the-tell-tale-heart`
- `the-yellow-wallpaper`
- `the-necklace`

## Why slug execution is required
These slugs are present in the reviewed-containment inventory as `MOVE_TO_PRIVATE_QA_BUCKET` entries, but many are not all present in `sprint1_scoped_containment_targets.json` object-id list (that scoped file is not the right mechanism for this exact 8-title batch).

## Exact command sequence (operator run)
```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
set -a
source secrets.env
source .secrets/earnalism-import.env
set +a
export OWNER_APPROVAL_TOKEN=AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.
export REVIEWED_INVENTORY_SHA256=21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c
export ALLOW_REMOTE_MUTATION=true
unset SPRINT1_CONTAINMENT_TARGETS_JSON

bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed \
  radharani muchiram-gurer-jibanchorit book-d19e96859f book-f5d593e1f4 book-edfcf810c5 the-tell-tale-heart the-yellow-wallpaper the-necklace
```

## What to verify immediately after run
```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json
```

Expected postconditions:
- `live_private_b2_count` should move toward 10 (from current 2).
- `nonprivate_exposed_count` should decrease as these slugs become private.
- For the 8 slugs above: `private_b2` should become `true` where applicable.

## Safety checks
- Keep `ALLOW_REMOTE_MUTATION=true`.
- Keep `OWNER_APPROVAL_TOKEN='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'`.
- Keep `REVIEWED_INVENTORY_SHA256='21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c'`.
- Keep `B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true`.

## Current blocker to clear first
Execution is currently blocked by environment DNS/network in this shell:
- `Could not resolve host: api.theearnalism.com`
- `Could not resolve host: s3.us-west-004.backblazeb2.com`
