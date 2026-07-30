# Audiobook package v2 canary — A Ghost Story

Status: **production-green at twenty-five percent, with full package-v2
promotion prepared for review and deployment. The approved legacy descriptor
remains retained for immediate rollback.**

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

## Production zero-percent proof

- Merge commit:
  `00567312d862191795951daa03d9a191f70bd019`
- GitHub main regression runs: `30538825285` and `30538826025`, both pass.
- Railway deployment:
  `a1467723-7101-47da-a155-de73e5e9a031`, exact merge commit, `SUCCESS`,
  root `/backend`, config `/backend/railway.json`.
- Independent HTTP matrix: `18/18` pass.
  - Candidate manifest: `404`, `private, no-store`.
  - Legacy Range: `206`, exactly `1,024` bytes,
    `Content-Range: bytes 0-1023/7047789`.
  - Invalid legacy Range: `416`, empty body.
  - Candidate segment and wrong package version: `404`.
  - Home curation: `200`, exactly the four approved audiobook slugs.
- Real customer-browser checkpoint:
  - Before intent the audio element had no `src`, empty `currentSrc`,
    `preload="none"`, `readyState=0`, and no observed audiobook asset.
  - Exactly one enabled `Start narration` control was present.
  - One click selected
    `/api/reader/book/a-ghost-story/audiobook`, reached `readyState=4`,
    stayed unpaused, and advanced from `2.397746` to `37.582244` seconds.
  - Duration was `880.944` seconds; media error and console error counts were
    zero.
  - Playback was paused after capture at `44.884889` seconds.

This checkpoint intentionally does not claim package-v2 or cross-segment
browser playback: at zero percent, the package candidate must remain
unselectable.

## Five-percent canary preparation

After the zero-percent checkpoint passed, the guarded rollout tool changed
only the candidate percentage from `0` to `5` in both controlled-publication
mirrors and regenerated their matching checksum manifests.

- Candidate identity:
  `earnalism_audiobook_rollout=a-ghost-story-canary-identity-000059`,
  deterministic bucket `3`.
- Legacy identity:
  `earnalism_audiobook_rollout=a-ghost-story-canary-identity-000000`,
  deterministic bucket `47`.
- Active legacy descriptor, candidate descriptor, rollout salt, package,
  storage receipts, approval evidence, narration and four-title public count:
  unchanged.

The five-percent deployment completed on merge
`2e5497ec7ca3be1c2b27416dd465a462d08a3a6d` and Railway deployment
`d2a92637-0b66-4948-83c9-159a62d20ea4`.

- The deterministic candidate/control HTTP matrix passed `63/63` checks.
- The candidate identity received the exact two-segment package manifest,
  both `206` Range streams, both exact timestamp sidecars, and `416` for both
  invalid ranges.
- Stale version, unknown segment and cross-title routes failed closed.
- The legacy control identity received no candidate manifest, segment or
  timestamp route and retained its exact monolithic `206` stream.
- The public home catalog stayed at exactly four approved audiobooks.
- The real browser naturally selected the legacy control. Before intent it
  had no source or observed audiobook asset. One click played the legacy route,
  reached `readyState=4`, advanced from `3.221962` to `5.438094` seconds, and
  produced no media or console errors. It was paused at `12.242585` seconds.

Because cookie inspection or manipulation is prohibited, the natural legacy
browser result is recorded as control-cohort proof, not misrepresented as
candidate proof.

## Twenty-five-percent canary preparation

The guarded rollout tool changed only `5%` to `25%` and regenerated the
matching checksum manifests. Active/candidate descriptors, salt, packages,
receipts, storage, approvals, narration and the four-title public count remain
unchanged.

The twenty-five-percent deployment completed on merge
`2f1c0ae3f5276ab356e2fee7b8cafd8e2eb46ce9` and Railway deployment
`f625d4c5-2786-4f75-8c67-61d60172ef63`.

- The deterministic candidate/control matrix passed `63/63` checks again.
- Both package segments, both timestamp sidecars, invalid ranges, negative
  isolation routes, legacy continuity and the four-title public catalog
  remained exact.
- The natural browser remained in the legacy cohort. It again proved no
  pre-intent audio, one-click playback, advancing time and zero errors before
  being paused.

## Full package-v2 promotion preparation

The guarded promotion operation makes descriptor
`cec2bb829531e0f820b8fd11d0881ecb42fc2d088adc5e93e7259e41d6026b40`
active, clears the candidate and percentage-canary fields, and retains legacy
descriptor
`c0504fda3db7ac07f48580acf23aa97670a8bdad4b74708707274915faddfc6d`
for rollback.

The promotion is not production-green merely because the pointer is prepared.
After deploy:

- every deterministic identity and the public request must receive the exact
  package manifest;
- one click in the real browser must play `c001-s001`;
- controlled near-boundary playback must auto-advance to `c001-s002`;
- both timestamp sidecars and negative routes must remain exact;
- media and console errors must stay zero; and
- the public audiobook count must remain four.

Any failure requires immediate pointer rollback to the retained legacy
descriptor.

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
- Production zero-percent deployment, HTTP proof and browser proof: pass.

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q internal/audiobook_lab/scripts/test_audiobook_package_builder_v2.py internal/audiobook_lab/scripts/test_audiobook_active_release_v2.py internal/audiobook_lab/scripts/test_audiobook_package_storage_v2.py backend/tests/test_audiobook_packages.py backend/tests/test_b2_audiobook_routing.py backend/tests/test_package_v2_public_projection_safety.py backend/tests/test_sprint1_audio_source_cleanup.py backend/tests/test_redis_cache_policy.py backend/tests/test_controlled_publication_precheck.py backend/tests/test_controlled_publication_publish.py backend/tests/test_a_ghost_story_routability.py
```
