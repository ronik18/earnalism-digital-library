# Audiobook package v2 canary evidence — book-2b9853ec52

Status: **private package and storage integrity verified; production package-v2
migration not authorized or complete**.

This canary reuses the exact already-approved narration for `book-2b9853ec52`.
It does not generate narration, approve a new audiobook, or change the title's
existing customer release state.

## Verified build

- Title: `দুই বিঘা জমি` by `রবীন্দ্রনাথ ঠাকুর`
- Approved source MP3 SHA-256:
  `a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5`
- Release descriptor SHA-256:
  `e00ec647012b90a2f2d5324ac59eec8f755e6353c3a736497495e53d9a21f26a`
- Canonical immutable prefix:
  `v1/prod/sprint1/book-2b9853ec52/releases/e00ec647012b90a2f2d5324ac59eec8f755e6353c3a736497495e53d9a21f26a/`
- Duration: `327069 ms`
- Segments: `2`
- Words / paragraphs: `546 / 74`
- Planned assets: `11`, totaling `40,579,264` bytes
- Narration regenerated: `false`
- Final package version and release manifest: not built

## Verified private staging

The private-QA preflight passed with versioning enabled and no public ACL grant.
The same report explicitly records `PRIVATE_QA_STAGING_ONLY` and
`release_eligible: false`. It does not prove independent production/DR
accounts, production Object Lock Governance, or production lifecycle policy.

All 11 planned assets were uploaded to private staging. Every object received a
VersionId and passed a complete post-upload download with exact SHA-256 and
size verification. A separate receipt-bound verification then repeated the
complete download checks for all 11 objects.

The receipt is a `private_qa_staging` receipt with one-day staging retention.
It is not a production-primary receipt and there is no independent DR receipt.

## Public projection boundary

Focused tests inject package-v2 manifests, release hashes, immutable storage
keys, buckets, replicas, and VersionIds into an approved controlled artifact.
The public catalog and Home v4 projections retain the same-origin reader audio
URL while excluding every internal package/storage field and value.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  backend/tests/test_package_v2_public_projection_safety.py -q
```

Result: `3 passed`.

## Objective ASR revalidation

The exact approved production audio and clean manuscript were hash-bound before
local ASR:

- Audio:
  `a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5`
- Controlled chapter content:
  `1e1d0b25627df784b861b8c6314b8bade1baabc554122dabf00dd8c5f2ae4dd9`
- Clean narrated manuscript:
  `788851c603ab1700f9e33bdfdc6a3e3c04f2ebb79890b88bc8c88f138270095d`

The clean manuscript equals the controlled chapter content plus one terminal
newline.

Cached multilingual Whisper-base completed the full audio in `114.04` seconds
but emitted an unusable punctuation-only transcript. Its raw ASR score and
coverage were both `0.0`; first and last spans failed.

Cached multilingual Whisper-medium was hash-verified. The word-timestamp run
reached 23% after `661.07` seconds and was stopped as a bounded-runtime
decision; it produced no transcript or accuracy score. A no-timestamp retry
was stopped on coordinator direction after `37.63` seconds and also produced
no result.

The authoritative prior audio-derived transcript for this exact audio and
manuscript remains `SUPPORTING_DIAGNOSTIC_WEAK`: raw ASR `1.1258`, coverage
`0.1126`, character similarity `0.4064`, token-order similarity `0.1466`, and
raw first/last span failures. The historical `10.0` transcript/source score is
a clean-TTS-source construction audit; it cannot replace the current raw
audio-derived ASR floor of `9.7`.

Classification: `FAIL_CLOSED_NO_NEW_ASR_9_7_PASS`. This closes neither the ASR
blocker nor the package-v2 migration hold. It does not revoke or mutate the
title's existing approved live delivery.

## Production hold

The existing audiobook remains approved and live through its current delivery
contract. Package-v2 has not been promoted. Production migration remains
blocked on:

- a passing current audio-derived ASR policy revalidation; the bounded local
  attempts failed or were inconclusive;
- a hash-bound provider/voice-rights snapshot;
- independent production-primary and DR storage;
- production Object Lock Governance and lifecycle evidence;
- verified primary and replica receipts;
- final package manifest and canonical package version;
- controlled-publication binding review; and
- production manifest, Range, and browser playback parity.

No TTS, paid provider call, paid-lock mutation, production upload, DR
replication, controlled-publication mutation, deployment, or production browser
validation was performed in this canary. Local ASR attempts ran only against
the exact hash-bound approved audio and did not produce a qualifying result.

## Evidence

The machine-readable companion report records SHA-256 bindings for the build,
upload plan, preflight, staging receipt, upload report, and independent verify
report. The objective-ASR companion report is also hash-bound into the
machine-readable canary evidence:

`internal/earnalism_intelligence/audiobook_package_v2_canary_book-2b9853ec52_20260729.json`

`internal/earnalism_intelligence/objective_qa/book-2b9853ec52_local_asr_revalidation_20260729.json`

A durable sanitized projection preserves the six source-artifact hashes and
the exact hash, size, B2 VersionId, and verification outcome for all 11 assets
without retaining credentials, account identifiers, endpoints, regions,
bucket names, object keys, or local asset paths:

`internal/earnalism_intelligence/audiobook_package_v2_private_canary_sanitized_evidence_book-2b9853ec52_20260729.json`

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  internal/audiobook_lab/scripts/audiobook_package_storage_v2.py preflight \
  --report /private/tmp/earnalism-package-v2-production-dr-preflight.json
```
