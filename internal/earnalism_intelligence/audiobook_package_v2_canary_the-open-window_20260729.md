# Audiobook package v2 canary — The Open Window

Status: **candidate package finalized and independently stored; rollout remains
0%; the legacy release remains active**.

This evidence records the completed production-and-DR staging canary for the
already-live audiobook `the-open-window`. It does not approve a new audiobook,
increase rollout, replace the active descriptor, or change the truthful public
audiobook count of four.

## Release selection truth

- Current active legacy descriptor:
  `81da7eb58ffe821cf708b7917af13f066929fccbaed0013394b8bf4f013c7ffe`
- Package-v2 candidate descriptor:
  `0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`
- Candidate rollout: `0%`
- Customer-selected delivery: legacy
- Public audiobooks remain:
  `book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and
  `the-open-window`

The canary therefore proves staged rollback-safe delivery readiness without
claiming a fifth live audiobook.

## Exact package identity

- Descriptor identity SHA-256:
  `0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`
- Descriptor file SHA-256:
  `55baccdf03430d80d4a9b0c55ff44b5637ad5780826061fe3c7833c621f342f8`
- Package version:
  `sha256-4bf8a83a0181bd10f22cfe32aba18f80e1a357dc7e73aa27c026d6d5c36a83fd`
- Final release-manifest SHA-256:
  `736fee5fa4af7b53aab04583455517b0ccffd0699d4f3250be9503ea07a7e292`
- Approved source-audio SHA-256:
  `b23e6720a2434c5a90d2437abf630cf68b6cb4cd7305a827a0d88fe5e586d438`
- Candidate assets: `14`, totaling `48,765,042` bytes
- Final manifest object: `6,470` bytes
- Duration / segments: `392,600 ms / 1`
- Words / paragraphs: `1,208 / 29`
- Narration regenerated: `false`

## Production and DR storage proof

The production and DR accounts are independently identified and use different
regions:

| Role | Account fingerprint | Bucket | Region |
| --- | --- | --- | --- |
| Production | `ed2d6a2923bb8394` | `earnalism-audiobooks-prod-v2-236e72b043e2` | `us-west-004` |
| Disaster recovery | `a9993749440a7aeb` | `earnalism-audiobooks-dr-v2-8af6a3af49d8` | `us-east-005` |

Both stores passed access preflight, have versioning enabled, and reported zero
public ACL grants. Both have Object Lock enabled with default
`GOVERNANCE` mode and a 30-day default-retention floor.

Every one of the 14 candidate assets:

- received an immutable version in production and DR;
- was fully downloaded and matched by exact size and SHA-256 in both stores;
- was recorded with `GOVERNANCE` Object Lock in both receipts; and
- satisfied the requested and receipt-verified minimum retention of 29 days.

The finalized release-manifest object was then uploaded independently to both
stores and passed the same full-download, checksum, version, and Governance
checks. The machine-readable companion lists all 14 asset IDs, exact hashes,
sizes, and verification results.

## Tests

Passing:

- Active-release selector unit suite: `23 passed`.
- Package-builder assertion suite: `34 passed`.
- Full frontend suite: `30 suites / 164 tests passed` after the final
  backslash-network-path origin-bypass regression was added.

The combined builder, storage, selector, backend package, B2-routing, and
Sprint 1 cleanup and Redis-policy regression run completed at
`2026-07-29T20:17:49Z` with `136 passed / 0 failed`. The formerly stale
proxy-asset assertion is resolved. The package-v2 candidate nevertheless
remains at `0%` until the deployed zero-percent checkpoint is proven, followed
by the already-authorized endpoint and browser canary before rollout increases.

## Safety boundary

This evidence contains no credential, application key, token, password,
private object key, or ephemeral local path. It intentionally retains the
non-secret account fingerprints, bucket names, and regions needed to prove
production/DR separation.

This evidence-only task did not generate narration, call a paid provider,
touch `paid_tts.lock`, mutate campaign policy/state, edit controlled
publications or code, perform cloud writes, change the rollout percentage,
flip the active descriptor, or change the public live count.

Machine-readable evidence:

`internal/earnalism_intelligence/audiobook_package_v2_canary_the-open-window_20260729.json`

Next exact command:

```bash
git diff --check
```
