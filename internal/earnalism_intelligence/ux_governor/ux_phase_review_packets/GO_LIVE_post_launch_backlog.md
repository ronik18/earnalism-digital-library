# GO LIVE Post-Launch Backlog

Updated: 2026-07-11T14:31:37+05:30

Stage 1 decision: `GO_LIVE_STAGE_1_APPROVED_WITH_AUDIO_LIMITATIONS`

## Resolved P0

- `bn-066` public audio exposure is closed through merged PRs #93, #94, and #95.
- Reader access remains available with 46 chapters.
- The public manifest returns `audio.enabled=false` with empty provider, voice, URL, and assets.
- Book and Reader surfaces show no Listen CTA, approval badge, narration controls, sync copy, audio element, static audio path, or AudioObject.
- `book-2b9853ec52` approved evidence-gated audio behavior remains intact.

## P1 - Backend ETag Runtime Rollout

- Roll out the merged backend ETag improvement through the normal Railway backend deployment path.
- The latest GO LIVE workflow's Railway job succeeded as a guard job, but checkout/install/deploy were skipped because deployment secrets were unavailable.
- Versioned frontend manifest requests remove the current browser impact, so this does not block Stage 1.
- After rollout, verify ETag/304 behavior and recheck `bn-066`, `book-2b9853ec52`, and A Ghost Story manifest release truth.

## P1 - Release-Truth Monitoring

- Keep the production canary comparison between `/api/books/{slug}` and `/api/reader/book/{slug}/manifest` audio state.
- Keep `bn-066` as a permanent negative canary until a future full release gate explicitly approves it.
- Fail when a non-approved title exposes audio assets, Listen UI, narration controls, sync claims, or AudioObject.

## P1 - bn-066 Private QA Tooling

- Keep local ASR diagnostics commit `b3abe331` out of production until the owner authorizes a separate tooling PR.
- Continue only with bounded ASR language/normalization repair on private artifacts.
- Do not regenerate, upload, publish, or expose audio without later release-gate approval.

## P2 - Production Quality Tooling

- Add a supported Lighthouse production script.
- Add a supported accessibility production script.
- Add a dedicated 390x844 and 430x932 production closeout smoke with an explicit `scrollWidth <= clientWidth` assertion.
- Do not claim Lighthouse/a11y green or launch-wide 10/10 until those gates actually run and pass.

## P2 - Deployment Maintenance

- Configure the Railway GitHub workflow secrets if workflow-managed backend deployment is desired.
- Upgrade local Vercel CLI from `54.15.1` to `55.0.0` or newer before any future owner-authorized local CLI deployment. Recommended command: `npm i -g vercel@latest`.
- No Vercel CLI command or manual deployment ran during this closeout.
- Retain hotfix branches until the owner authorizes cleanup after the production observation window.

## Still Not Approved

- Public `bn-066` audio or paid Listen.
- Paid Listen campaigns.
- Paid TTS, Sarvam, ASR, auditions, uploads, or publication.
- Audiobook release-gate mutation.
- Lighthouse/a11y green status.
- Launch-wide 10/10.

## Next Exact Command

```bash
cd /tmp/earnalism-bn066-hide-hotfix && gh run list --branch main --limit 5
```
