# Audiobook package v2 canary — Sredni Vashtar

Status: **immutable production and DR storage passed; the package-v2 candidate
is staged at 0% while the already-approved legacy audiobook remains active for
all customers**.

This is a delivery migration for the existing live audiobook. It does not
approve a new audiobook, regenerate narration, or change the public count of
four.

## Exact package identity

- Candidate descriptor:
  `53458d86308f4718d46334d23aff725db31b70ed8f2736f9b731ca429e550fd3`
- Package version:
  `sha256-9f1e84d4377dff2d5778dd158393fd450feb37fdef5ca6e88c67191cbe277edd`
- Final package manifest SHA-256:
  `d488f114c154dd57ecdf474254d33b07a355a26ed9b3d416bc85ddf1b68117ea`
- Legacy descriptor retained and active:
  `1f8e4e1f81fc42419215b99afb652b1b120a4be42685c0af6ca36c00697bb50c`
- Duration / segments: `636,840 ms / 1`
- Narration regenerated: `false`

## Storage proof

Production and DR passed the combined release preflight with independent
account fingerprints, private buckets, versioning, no destructive lifecycle
rules, and 30-day default Governance Object Lock.

All 15 payload objects (`79,267,278` bytes) were:

- uploaded to production and fully downloaded for exact size/SHA-256 proof;
- verified again against the production receipt and exact version IDs;
- copied from verified production bytes to the separate DR account;
- fully downloaded and verified again in DR; and
- retained under Governance mode.

The finalized `6,452`-byte release manifest then passed the same four-step
production/DR receipt lifecycle. No released key was overwritten.

## Release selection truth

The candidate is bound at `0%`. All customers still receive the existing
legacy release. The immutable package can be tested after deployment without
claiming customer rollout, and rollback remains an explicit pointer operation.

## Validation

- Active-release pointer validation: pass, zero blockers.
- Controlled-publication mirrors: byte-identical.
- Focused builder, storage, selector, backend package, routing, projection,
  precheck, and publication tests: `170 passed, 2 subtests passed`.
- Approval flags and public audiobook count: unchanged.
- `paid_tts.lock`: untouched.
- Production deployment, HTTP proof, and browser proof: pending.

Next exact command after the 0% deployment is production-green:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  internal/audiobook_lab/scripts/audiobook_active_release_v2.py rollout \
  --slug sredni-vashtar \
  --percentage 5
```
