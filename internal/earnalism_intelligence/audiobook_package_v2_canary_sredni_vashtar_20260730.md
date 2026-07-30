# Audiobook package v2 canary — Sredni Vashtar

Status: **the 0% production checkpoint passed and the package-v2 candidate is
prepared for a controlled 5% canary**.

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

The candidate rollout percentage is now `5%` in this isolated branch. The
legacy descriptor remains active and retained, and the package-v2 descriptor
remains the candidate. This is a delivery-only canary: it does not change the
audio approval flags or the public audiobook count.

At production `0%`, the exact merged commit
`6954b7387beaf0f9e8ceeca01d72928e5b371ede` deployed successfully through
Railway deployment `74fcae57-0878-4c41-bde9-c12c05f98f57`.

- Candidate package manifest: `404` as expected.
- Legacy `Range: bytes=0-1023`: `206`, exactly 1,024 bytes.
- Invalid legacy range: `416`.
- Public catalog: exactly four approved audiobooks.
- Reader before intent: no audio `src`, `readyState=0`, zero console errors.
- One click: legacy audio reached `readyState=4`, remained playing, and advanced
  to `25.047581` seconds of `636.84` seconds with zero console errors.

## Validation

- Active-release pointer validation: pass, zero blockers.
- Controlled-publication mirrors: byte-identical.
- Focused builder, storage, selector, backend package, routing, projection,
  precheck, and publication tests: `170 passed, 2 subtests passed`.
- Approval flags and public audiobook count: unchanged.
- `paid_tts.lock`: untouched.
- Production `0%` deployment, HTTP proof, and browser proof: pass.
- `5%` pointer mutation: local green in an isolated branch.
- `5%` focused builder, selector, storage, backend package, routing,
  publication, Redis policy, and source-cleanup tests: `172 passed`.
- Production `5%` cohort HTTP and browser proof: pending merge/deployment.

Next exact command:

```bash
git diff --check && git status --short
```
