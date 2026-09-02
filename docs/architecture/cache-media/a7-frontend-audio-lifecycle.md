# A7 frontend audio lifecycle and main-integration evidence

## Integration

- PR: #345 (`codex/cache-media-architecture-baseline`)
- Starting PR head: `ba05a8cc60cbb5ecdad821e304347b15615660f5`
- Merged mainline head: `1a23ad2f2a04176faa0afb753f7144af2f437d0d`
- Normal merge commit: `b277cc3129a4b9f87f4af93f56352b2af208ac02`
- Merge result: clean `ort` merge; no conflict resolution and no overlapping cache/media paths.

The A7 pre-merge checkpoint verified the PR worktree, index, expected PR head,
remote PR head, merge base, changed-file inventories, and hashes. It reported
`PASS`, with zero hash mismatches, no missing checkpoint files, and no worktree
contamination. The post-merge overlap inventory remains empty.

## Lifecycle finding and correction

`FRONTEND_AUDIO_LIFECYCLE_CLASSIFICATION: MANIFEST_FETCH_NOT_CANCELLED`

Reader and Listener route effects previously prevented stale state updates with a
boolean flag, but their reader-manifest requests continued after client-side
navigation. Reader canonical-page requests had the same gap. A7 adds one
`AbortController` per route-owned request, passes the signal through the shared
page client, aborts during effect cleanup, and suppresses only standard Axios or
DOM cancellation errors. Non-cancellation failures keep their existing user
messages. This changes neither authorization, Reading Pass creation or renewal,
media URL construction, range behavior, cache policy, nor public-audio policy.

The audio element remains created only after authorized, approved release truth;
fixture and unentitled states still render no media element. React-owned event
handlers are removed with the element, the existing lease-renewal interval is
cleared on cleanup, and the existing unmount session-close request remains
unchanged. No additional source attachment, retry loop, or player mechanism was
introduced.

## Deterministic validation

- Backend cache/media and protected-audio selection: 186 passed.
- Two `test_unapproved_public_audio_asset_safety.py` failures are baseline data
  failures: the test file and both cited controlled-publication inputs are
  byte-identical between the pre-merge PR head and merged mainline state.
- Focused frontend contracts: 4 suites, 22 tests passed.
- Fixture build: passed. Its SEO prebuild logged unavailable loopback API
  sources and used its existing deterministic local fallback; static snapshot
  verification passed 2,502 assertions.
- `scripts/cache_media/verify_frontend_audio_lifecycle.mjs`: passed eight cases
  each in Chromium, Firefox, and WebKit: cancellation plus desktop, 390px, and
  320px-at-200% Reader and Listener fixtures. It delays only local fixture
  manifest responses, performs client-side navigation, and observes each pending
  request fail as cancelled. It uses no production API, credentials,
  entitlement, Reading Pass consumption, audio payload, or storage access.

The in-app browser was unable to open the loopback fixture URL because its local
client blocks that origin. The three engine-specific Playwright runs above are
the browser evidence for A7. Firefox logged one static-fixture font transport
warning; no application console or page errors occurred.

## Boundary confirmation

No deployment, release, PR merge, rebase, force push, cache-policy widening,
media delivery change, binary cache change, signed URL, real-audio playback, or
customer-content change was performed. This is development/testing evidence
only.
