# GO LIVE Final Closeout After bn-066 Hotfix

Generated: 2026-07-11T14:31:37+05:30

## Decision

`GO_LIVE_STAGE_1_APPROVED_WITH_AUDIO_LIMITATIONS`

The public library and reader may remain live. `bn-066` is approved for reader access only and is fail-closed for public audio. `book-2b9853ec52` remains the only approved public audiobook in this closeout.

This decision does not approve paid Listen, paid generation, audiobook publication, a release-gate mutation, Lighthouse/a11y green status, or launch-wide 10/10.

## Evaluated Release

- Main commit: `12fc406001bc82be0fd377bde864b64a1694d479`
- Hotfixes: merged PRs #93, #94, and #95
- Production frontend deploy: workflow-managed Vercel deploy passed
- Backend caveat: the merged ETag improvement still awaits a future Railway backend rollout. Versioned frontend manifest requests remove the current browser impact, and direct production API/UI validation passed.

## Main Workflow Status

All latest relevant main runs were terminal and successful. No failed, cancelled, or active run was found.

| Workflow | Commit | Result | Evidence |
| --- | --- | --- | --- |
| GO LIVE regression gate | `12fc406` | PASS | Run 29146484535 |
| Regression suite | `12fc406` | PASS | Run 29146484516 |
| Post-deploy k6 smoke test | `12fc406` | PASS | Run 29146484533 |
| Vercel production deploy job | `12fc406` | PASS | Job 86528996592 |
| Production canary job | `12fc406` | PASS | Job 86529099468 |
| Production observer | `6445dc5` | PASS | Run 29145987798 |

The Railway workflow job concluded successfully after checking secrets, but its checkout/install/deploy steps were skipped. It did not roll out the pending backend ETag change.

## Production API Truth

| Title | API result | Public audio truth |
| --- | --- | --- |
| `bn-066` | Book and reader manifest HTTP 200; 46 chapters; reader enabled | `audio.enabled=false`; provider, voice, URL, and assets empty; audio endpoint HTTP 404 |
| `book-2b9853ec52` | Book and reader manifest HTTP 200 | Manifest release gate `APPROVED`, QA `QA_PASSED`, audio enabled through evidence-gated assets |
| `a-ghost-story` | Book and reader manifest HTTP 200 | Reader-first and audio-hidden |
| `book-d19e96859f` | Book API HTTP 404 | Fail-closed and no public audio |

The `book-2b9853ec52` book-summary flags remain conservative; its reader manifest is the authoritative approved audio evidence.

## Production UI Truth

Fresh settled desktop checks passed for Home, Library, Contact, the Book and Reader routes for `bn-066`, `book-2b9853ec52`, and `a-ghost-story`.

- `bn-066` shows Reader Ready and Audio Hidden, renders `CH. 1 OF 46`, and exposes no Listen CTA, approval badge, narration controls, sync copy, audio element, static audio path, or AudioObject.
- `book-2b9853ec52` retains Audiobook Approved and approved reader audio controls.
- A Ghost Story remains Reader Ready and Audio Hidden with no audio UI.
- Contact surfaces expose `sales@reoenterprise.org`; `sales@reoenterprise.in` was not found.
- The safer tricolor badge is present and the exact Indian flag is not the public default.
- No horizontal overflow was observed at the fresh 1280x720 browser viewport.

The in-app browser remained fixed at 1280x720 during this closeout, so no fresh 390/430 px scroll-width measurement is claimed. Mobile continuity is supported by the passing main regression render suite at 375x900 and 768x1000 plus the prior post-hotfix production mobile validation.

## Bengali Slideshow

- Bengali titles are visible, including `দুই বিঘা জমি`, `দেবদাস`, `পথের পাঁচালী`, and `ক্ষুধিত পাষাণ`.
- The active slide advanced automatically during observation.
- Next and Previous controls both changed the active slide.
- Dracula is not the sole or dominant first story.

## Release Safety

- No public audio files were found under `frontend/public` or `frontend/build`.
- No browser speech fallback was found.
- No word-level sync claim was found.
- No non-approved AudioObject was found.
- No unapproved Listen/player UI was found on the validated title routes.
- `paid_tts.lock` remains active with `current_holder: none` and `allowed_next_holders: []`.
- No paid TTS, Sarvam, ASR, audition, upload, publication, or release-gate mutation ran.

## Approved Now

- Stage 1 public library and reader launch.
- Public reader access for `bn-066`, with audio hidden.
- Approved evidence-gated public audiobook behavior for `book-2b9853ec52` only.

## Not Approved

- Public audio or paid Listen for `bn-066`.
- Paid Listen campaigns for any newly reviewed title.
- Paid TTS, Sarvam, ASR, auditions, uploads, or audiobook publication.
- Audiobook release-gate mutation.
- Lighthouse/a11y green status.
- Launch-wide 10/10.

## Next Exact Command

```bash
cd /tmp/earnalism-bn066-hide-hotfix && gh run list --branch main --limit 5
```
