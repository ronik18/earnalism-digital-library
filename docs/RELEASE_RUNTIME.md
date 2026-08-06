# Release runtime

`scripts/release_runtime.py` is the side-effect boundary for the governed
release evaluator. It adds real Sarvam Bulbul v3 and ElevenLabs adapters,
idempotent segment generation, checksum-bound local staging, and an
operator-owned HTTP production-promotion adapter.

## Generation

Dry-run is the default and performs no provider call:

```bash
python3 scripts/release_runtime.py generate \
  --manifest /path/to/release-manifest.json \
  --output-dir internal/audiobook_lab/release_runtime/<slug>
```

Paid execution requires all of the following before any provider request:

- the manifest's exact audiobook profile approval;
- `EARNALISM_ENABLE_PAID_GENERATION=true`;
- `EARNALISM_APPROVE_SARVAM_GENERATION=true` or
  `EARNALISM_APPROVE_ELEVENLABS_GENERATION=true`;
- numeric `EARNALISM_PAID_GENERATION_MAX_USD` covering the manifest estimate;
- `EARNALISM_PAID_GENERATION_LOCK_PATH` pointing to a JSON lock with
  `status=AUTHORIZED`, matching `lock_id`, and an allowed provider;
- matching `EARNALISM_PAID_GENERATION_LOCK_ID`.
- `rights.commercial_use=APPROVED`, non-empty approved territories, and
  `rights.audio_derivative_rights_status=APPROVED` in the manifest.

Then the operator must opt in explicitly:

```bash
python3 scripts/release_runtime.py generate \
  --manifest /path/to/release-manifest.json \
  --output-dir internal/audiobook_lab/release_runtime/<slug> \
  --execute-paid
```

Only transient provider failures retry, at most three times. A completed
segment is reused only when its request fingerprint and checksum match.

## Staging import

Staging is private and not release-eligible:

```bash
python3 scripts/release_runtime.py stage \
  --manifest /path/to/release-manifest.json \
  --generation-dir internal/audiobook_lab/release_runtime/<slug> \
  --staging-dir internal/audiobook_lab/staging
```

The receipt is immutable-by-release-id and verifies every copied artifact.
The existing `audiobook_package_storage_v2.py` remains the production B2
primary/DR path; its strict preflight, versioning, retention, and replica
requirements are not bypassed by this local staging adapter.

## Production promotion

Promotion requires the existing release evaluator to prove all automated
checks and both human approvals, plus a passing private staging receipt.
Dry-run is default:

```bash
python3 scripts/release_runtime.py promote \
  --manifest /path/to/release-manifest.json \
  --staging-receipt /path/to/staging_receipt.json
```

Actual promotion additionally requires `EARNALISM_ENABLE_PRODUCTION_PROMOTION=true`,
`EARNALISM_PRODUCTION_PROMOTION_APPROVED=true`, an explicit
`EARNALISM_PRODUCTION_PROMOTION_ENDPOINT`, and a secret
`EARNALISM_PRODUCTION_PROMOTION_TOKEN`. The endpoint must return
`{"status":"PROMOTED","slug":"..."}` for the exact idempotency key.
The input manifest must already contain `release_status=LIVE` and
`audio_release_gate_status=PASS`; the runtime never promotes directly from a
partial generation or staging receipt.
No catalog flag is flipped locally, and no production status is inferred from
an HTTP request that does not return explicit promotion evidence.
