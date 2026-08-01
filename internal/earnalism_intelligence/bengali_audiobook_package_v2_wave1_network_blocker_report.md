# Wave-1 Package-v2 Migration: Network Blocker Report

## Status
- `run_wave1_one_by_one_with_postcheck.sh --execute-reviewed` fails on first target before any mutation with DNS/network failure.

## Evidence
- `storage_containment_executor.py` reports `EndpointConnectionError` to:
  - `https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks-prod-v2-236e72b043e2`
- Host resolution failures observed:
  - `Could not resolve host: api.theearnalism.com`
  - `Could not resolve host: s3.us-west-004.backblazeb2.com`

## Why release gates still hold
- The guard logic succeeds up to token/env validation when using correct owner token for the chosen path.
- `validate_sprint1_wave1_private_b2_progress.sh` and `sprint1_package_v2_readiness.json` confirm:
  - `live_count=10`
  - `live_private_b2_count=2`
  - `nonprivate_exposed_count=8`

## Exact next action once network/DNS is available
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

Post-check:
- `python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json`
- `bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh`

## 2026-07-31T00:00:00Z Follow-up (current environment)

- Dry-run validation of all remaining 8 wave-1 targets still passes.
- Full execute still blocked by DNS/network; observed repeated failures:
  - `Could not resolve host: s3.us-west-004.backblazeb2.com`
  - `Could not resolve host: api.theearnalism.com`
- Host resolution check in-shell also fails for generic names:
  - `example.com`, `api.github.com`, `google.com`, `s3.us-west-004.backblazeb2.com`
- This confirms the blocker is external connectivity in this runtime, not a release-gate or target-selection defect.

## 2026-07-31T00:00:00Z Deterministic network preflight added
- Added: `internal/audiobook_lab/storage_containment/check_wave1_endpoint_connectivity.sh`
- New command:
  ```bash
  bash internal/audiobook_lab/storage_containment/check_wave1_endpoint_connectivity.sh
  ```
- Latest result in this environment:
  - `api.theearnalism.com` -> fail
  - `s3.us-west-004.backblazeb2.com` -> fail
  - `s3.us-east-005.backblazeb2.com` -> fail
  - `api.github.com` -> fail
  - `backblaze.com` -> fail
- This script is intended to be run before execute attempts to separate DNS/network blockers from migration logic blockers.

## 2026-07-31T18:20:00Z Operator update

- Same environment check in the user shell now passes DNS for all required endpoints:
  - `api.theearnalism.com`, `s3.us-west-004.backblazeb2.com`, `s3.us-east-005.backblazeb2.com`, `backblaze.com`, `api.github.com`.
- In this agent runtime, the DNS checker still fails; therefore, `--execute-reviewed` cannot be completed here.
- Important: owner-token requirement is command-path dependent:
  - `run_wave1_with_guard.sh` / `run_sprint1_private_b2_wave1.sh` expect:
    `AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.`
  - `run_wave1_one_by_one_with_postcheck.sh` and direct remediation path without scoped target list expect:
    `AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.`
- To resolve the blocker, run the execute command in a DNS-working shell and then immediately re-check:
  - `bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh`
  - `python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json`

## 2026-07-31T18:35:00Z Validation status from this runtime

- `python3 -m pytest backend/tests/test_b2_audiobook_routing.py -q` → **5 passed**
- `python3 -m pytest backend/tests/test_audiobook_package_v2_routes.py -q` → **11 passed**
- Connectivity blocker in this runtime remains: `gaierror [Errno 8] nodename nor servname provided...`
- Readiness evidence remains unchanged:
  - `live_count=10`
  - `live_private_b2_count=2`
  - `nonprivate_exposed_count=8`

## Exact operator commands for remaining Wave-1 migration (preferred)

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
set -a
source secrets.env
source .secrets/earnalism-import.env
set +a

# If migrating via wave1_with_guard / wave1_private_b2 script:
export OWNER_APPROVAL_TOKEN='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'

# If migrating via one-by-one postcheck runner:
# export OWNER_APPROVAL_TOKEN='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'

export REVIEWED_INVENTORY_SHA256='21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c'
export ALLOW_REMOTE_MUTATION=true
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true
unset SPRINT1_CONTAINMENT_TARGETS_JSON

bash internal/audiobook_lab/storage_containment/check_wave1_endpoint_connectivity.sh && \
bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed \
  radharani muchiram-gurer-jibanchorit book-d19e96859f book-f5d593e1f4 book-edfcf810c5 the-tell-tale-heart the-yellow-wallpaper the-necklace

bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json
```

## 2026-07-31T18:45:00Z Current readiness snapshot (agent runtime)

- `live_count = 10`
- `live_private_b2_count = 2`
- `nonprivate_exposed_count = 8`
- Remaining Wave-1 slugs still requiring private-B2 migration:
  - `radharani`
  - `muchiram-gurer-jibanchorit`
  - `book-d19e96859f`
  - `book-f5d593e1f4`
  - `book-edfcf810c5`
  - `the-tell-tale-heart`
  - `the-yellow-wallpaper`
  - `the-necklace`

## 2026-07-31T19:05:00Z Deterministic launcher added

- Added deterministic wrapper:
  - `internal/earnalism_intelligence/run_sprint1_wave1_migrate.sh`
- Wrapper behavior:
  - `postcheck` mode sets `AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.` and runs the 8-slugs migration by default
  - `guard` mode sets `AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.` and runs scoped-wave flow
- In this agent runtime, wrapper still stops on `check_wave1_endpoint_connectivity.sh` because DNS remains blocked.
- Use wrapper from DNS-working shell:
  - `bash internal/earnalism_intelligence/run_sprint1_wave1_migrate.sh postcheck`
