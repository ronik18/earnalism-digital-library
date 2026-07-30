# Audiobook package v2 canary — The Open Window

Status: **package v2 is active for 100% of production delivery and has passed
exact API, reader-manifest, and real-browser validation; the legacy release is
retained only for explicit rollback**.

This evidence records the completed production-and-DR staging canary for the
already-live audiobook `the-open-window`, followed by the completed 5%, 25%,
and 100% production checkpoints. It does not approve a new audiobook or change
the truthful public audiobook count of four.

## Release selection truth

- Current active package-v2 descriptor:
  `0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`
- Active package delivery: `100%`
- Candidate slot: cleared after promotion
- Legacy descriptor retained for explicit rollback:
  `81da7eb58ffe821cf708b7917af13f066929fccbaed0013394b8bf4f013c7ffe`
- Customer-selected delivery: package v2
- Public audiobooks remain:
  `book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and
  `the-open-window`

The original `0%` checkpoint remains part of the evidence history: the
candidate was stored and bound while all customers remained on legacy
delivery. The subsequent `5%` checkpoint proved initial sticky candidate and
legacy delivery. The completed `25%` checkpoint independently reconfirmed both
paths. The completed `100%` checkpoint promoted the exact candidate descriptor
to active package delivery and cleared the candidate slot without claiming a
fifth live audiobook.

## Five-percent production checkpoint

- Rollout commit:
  `7e900197a77f4a90ea4b803d3796ef74a0ae868d`
- Main merge commit:
  `83e806d52787605c3396d61bebefd6aa3e3d742f`
- Rollout salt: `open-window-package-v2-canary-20260729`
- New sticky identities sampled: `62`
- Candidate selections: `1` (sample 62)
- Legacy selections: `61`
- Repeating the candidate cookie returned HTTP `200` and the same immutable
  package version.
- Repeating the legacy cookie returned HTTP `404` with
  `private, no-store`.

The candidate manifest returned HTTP `200`,
`private, max-age=60, must-revalidate`, and package version
`sha256-4bf8a83a0181bd10f22cfe32aba18f80e1a357dc7e73aa27c026d6d5c36a83fd`.
Its segment route returned HTTP `206`, exactly 64 bytes for
`bytes 0-63/4712013`, `audio/mpeg`, the matching package-version header, and
an MP3/ID3 prefix. The measured timestamp sidecar was fetched as 12,839 bytes
with SHA-256
`637ed34e55d13818dac7ddf4421425d58da2fea17300203b4c9365669b2fe070`.
An invalid range returned `416`; a wrong package version and a candidate
segment request from the legacy cohort each returned `404`.

The in-app browser loaded
`https://www.theearnalism.com/reader/the-open-window` in a legacy cohort.
Page 1 correctly kept the audio control disabled with
“Audio starts on reading pages”. On page 2, before user intent, the audio
element had `src=null` and `preload=none`. The first click primed
`/api/reader/book/the-open-window/audiobook` without error; the second click
produced `paused=false`, `readyState=4`, `preload=auto`, and visible
“Pause narration” and “Stop narration” controls. Console logs were empty and
playback was stopped after validation.

That first browser observation is legacy browser no-regression evidence. It
did not itself test candidate playback, and no browser latency was measured.

### Candidate real-browser checkpoint

A subsequent isolated Chromium `149.0.7827.55` production-browser run sampled
19 independent `www.theearnalism.com` contexts to obtain one 5% candidate
context. In that candidate context:

- the reader manifest returned HTTP `200` twice;
- before user intent, the audio element had `src=null`, empty `currentSrc`,
  `preload=none`, `readyState=0`, and `paused=true`;
- on page 2, the first “Start narration” click bound the exact canonical
  package-segment route and received HTTP `206` for `bytes=0-`;
- after that first click, the element had `readyState=4`, `paused=true`,
  duration `392.6` seconds, and no error;
- the second click started playback with `paused=false`, current time about
  `2.06` seconds, `preload=auto`, visible Pause/Stop controls, and a second
  `206` request for `bytes=98304-`;
- a programmatic seek to 300 seconds continued playback at about `302.04`
  seconds and produced `206` for `bytes=3571712-`;
- advancing to page 3 safely stopped and reset audio to `src=null`, after which
  re-priming succeeded;
- reloading returned to page 1 with no pre-intent audio, and page 2 replay then
  succeeded from cached manifest/media with `paused=false`, current time about
  `1.46` seconds, and the exact package route retained; and
- console and page errors remained empty. Only non-error preload warnings were
  observed. Stop reset the source and current time.

The package has one segment, so this checkpoint does not claim cross-segment
auto-advance. No browser latency was measured.

## Twenty-five-percent production checkpoint

PR `#181` merged rollout commit
`68024887cc54823e3238360c8c90eab5891ae083` into main as
`169b6d7143cf9d54408784b43cef87f65e758050`. The main regression suite and
GO LIVE regression gate completed successfully. Repository-linked Railway
deployment `5d5db8a5-5963-4e8a-ba46-9600c6990472` also completed with
`SUCCESS`.

Fresh production API sampling found a package-v2 candidate at identity index
1 and a retained legacy cohort at index 3 within three new identities.
Repeating the candidate identity returned HTTP `200` and the same immutable
package; repeating the legacy identity returned HTTP `404` for package
discovery.

The candidate manifest returned HTTP `200` and matched descriptor
`0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`
and package version
`sha256-4bf8a83a0181bd10f22cfe32aba18f80e1a357dc7e73aa27c026d6d5c36a83fd`.
The exact segment passed:

- `HEAD` at HTTP `200` with `Content-Length: 4712013`;
- `Range: bytes=0-63` at HTTP `206` with exactly 64 bytes from a total of
  `4,712,013`;
- invalid range rejection at HTTP `416`;
- measured timestamps at HTTP `200`, 12,839 bytes, SHA-256
  `637ed34e55d13818dac7ddf4421425d58da2fea17300203b4c9365669b2fe070`;
- wrong package version rejection at HTTP `404`; and
- the same candidate segment rejected at HTTP `404` for the legacy cohort.

The retained legacy monolith independently returned HTTP `206` for a 64-byte
range from a total of `6,283,053` bytes. `/api/home/curated` continued to
report exactly four public audiobooks:
`book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`.

An isolated Chromium run sampled two new production contexts and obtained one
candidate and one legacy context. Neither context loaded audio before user
intent.

- The candidate context played through the exact package route with
  `readyState=4`, `paused=false`, and duration `392.6` seconds. A seek to 180
  seconds continued playback at about `181.53` seconds. Console and page error
  counts were both zero.
- The legacy context played through the exact monolith route with
  `readyState=4`, `paused=false`, and duration `392.6` seconds, with no page
  errors. Its two network-console `404` entries were the expected package
  manifest fallback only; unexpected console errors remained zero.

The package still contains one segment, so cross-segment auto-advance is not
claimed. This 25% checkpoint supported advancing the separately prepared 100%
active-pointer promotion; at that historical checkpoint the promotion was not
yet claimed as deployed.

## One-hundred-percent production promotion

PR `#182` merged as
`d01482c20b2e9c081ebf5cf0f9334f014566d6ed`. Main workflow runs
`30514196370` and `30514196277` completed successfully. Repository-linked
Railway deployment `152b8e25-d119-4e5f-9c18-bfdeae74548a` completed with
`SUCCESS`; the prior 25% deployment
`5d5db8a5-5963-4e8a-ba46-9600c6990472` is `REMOVED`.

All eight fresh production identities returned package manifests at HTTP
`200`, bound to exact package version
`sha256-4bf8a83a0181bd10f22cfe32aba18f80e1a357dc7e73aa27c026d6d5c36a83fd`
and active descriptor
`0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`.
An identity retained from the former legacy cohort also returned HTTP `200`
with the same exact package. This proves the active pointer replaced cohort
selection.

Fresh and former-legacy identities each received HTTP `206` and exactly 64
bytes for `Range: bytes=0-63` from the 4,712,013-byte package segment, with
the exact package-version header. Invalid range remained `416`; a wrong
package version remained `404`. The retained legacy monolith independently
remained byte-range readable at HTTP `206`, 64 bytes from a total of
6,283,053 bytes, solely for explicit rollback.

The production reader manifest returned HTTP `200` with audio enabled,
`APPROVED`, `QA_PASSED`, and the package-manifest asset present. Its
`package_version` remains an empty string by contract; this evidence does not
claim otherwise. Home curation still reports exactly:
`book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`.

In the production in-app browser:

- reloading page 1 left both `src` and `currentSrc` empty;
- page 2 before intent had `src=null`, `preload=none`, `readyState=0`, and
  `paused=true`;
- the first click bound the exact package-segment route, reached
  `readyState=4` with duration `392.6` seconds, no error, and remained paused;
- the second click played with `paused=false`, current time about `1.63`
  seconds, and visible Pause/Stop controls;
- developer error logs remained empty; and
- Stop reset source, current time, and ready state.

The package contains one segment, so this final promotion still does not claim
cross-segment auto-advance. Package v2 is now the validated production-active
delivery, the candidate slot is cleared, and the legacy descriptor remains
retained only for explicit rollback.

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
proxy-asset assertion is resolved. The production checkpoint then passed at
`5%`, and the later main regression, GO LIVE gate, Railway deployment, and
sticky-cohort HTTP/browser validation passed at `25%`. The final main
workflows, Railway deployment, eight-identity package proof, reader manifest,
and in-app browser playback passed after promotion to `100%`.

## Safety boundary

This evidence contains no credential, application key, token, password,
private object key, or ephemeral local path. It intentionally retains the
non-secret account fingerprints, bucket names, and regions needed to prove
production/DR separation.

This evidence update did not generate narration, call a paid provider, touch
`paid_tts.lock`, mutate campaign policy/state, edit controlled publications or
code, perform cloud writes, flip the active descriptor, or change the public
live count. It records the independently completed 100% promotion checkpoint
while preserving the earlier 0%, 5%, and 25% history.

Machine-readable evidence:

`internal/earnalism_intelligence/audiobook_package_v2_canary_the-open-window_20260729.json`

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/audiobook_active_release_v2.py status --slug sredni-vashtar
```
