# Audiobook package v2 canary — A Ghost Story

Status: **the exact approved audiobook is immutable in production and
independent DR, and its package-v2 candidate is staged at zero percent.**

This is a delivery migration for an audiobook that was already approved and
live. It does not regenerate narration, change release gates, or increase the
public audiobook count of four.

## Exact package identity

- Title / author: `A Ghost Story` / `Mark Twain`
- Candidate descriptor:
  `cec2bb829531e0f820b8fd11d0881ecb42fc2d088adc5e93e7259e41d6026b40`
- Legacy descriptor, still active:
  `c0504fda3db7ac07f48580acf23aa97670a8bdad4b74708707274915faddfc6d`
- Package version:
  `sha256-9f036b8f55e834684aac2ed2710efad2be66ccd96ca8d3e38eee982150e5b422`
- Final manifest SHA-256:
  `5f5be1e54d165326bacafcf6aa18a74f2f0e3fc2cfc1590d7baf64c6c7f28477`
- Narrated manuscript SHA-256:
  `0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4`
- Approved source audio SHA-256:
  `c0e52985ee1e3e178b81d83157189251a667d64ecbc22bbc0940e6e4fc7bf904`
- Duration / segments: `880,922 ms / 2`
- Narration regenerated: `false`

The two delivery segments are `267.348` and `613.574` seconds. The final
manifest binds their exact audio, timestamp, VTT, metadata, production and DR
version identities.

## Existing release truth

The approved audiobook remains ASR `9.88`, coverage `0.995571`, listening
`9.4`, confidence `0.95`, no fatal flags, first/last and ordered-content pass,
and measured section sync `1.0` with no estimated sync.

## Storage proof

Production and DR passed the combined release preflight with independent
accounts, private buckets, versioning, no destructive lifecycle rules, and
30-day default Governance Object Lock.

All 20 payload objects (`102,547,050` bytes) and the final `11,937`-byte
release manifest were:

- uploaded to production and fully downloaded for exact size/SHA-256 proof;
- verified again against exact production version IDs;
- replicated from verified production bytes into the separate DR account; and
- fully downloaded and verified again in DR.

No immutable key was overwritten.

## Zero-percent selection truth

The approved legacy descriptor remains active. The package-v2 descriptor is
receipt-bound but staged at `0%`, so no customer selects it yet. Both
descriptors are retained for controlled rollback/promotion.

## Validation

- Active-release pointer: valid, zero blockers.
- Controlled-publication mirrors: byte-identical.
- Builder, selector, storage, package API, B2 routing, projection safety,
  A Ghost Story routability, source cleanup, Redis policy, precheck and
  publication tests: `178 passed`.
- Focused frontend manifest, release-truth, playback, timestamp, reader,
  service-worker and static-route safety tests: `70 passed`.
- `git diff --check`: pass.
- Approval flags, narration and public audiobook count: unchanged.
- `paid_tts.lock`: untouched.
- Production zero-percent deployment, HTTP proof and browser proof: required
  after merge.

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/audiobook_active_release_v2.py status --slug a-ghost-story
```
