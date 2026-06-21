# Audiobook Legal Accessibility Compliance Gate

Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

This is an internal compliance gate for future Earnalism audiobook releases. It does not enable audio, approve public audio, expose audio URLs, or generate audio. It does not make a legal guarantee. It records the evidence required before any audiobook can move from internal review to public release.

## Current Product Truth

- Dracula is live only as an approved core reading release.
- Dracula audio remains disabled.
- Kshudhita Pashan remains pipeline-only.
- PR #44 and PR #45 remain Draft evidence and cannot be used as public release approval.
- No audiobook is public/live.
- No Listen Now CTA, AudioObject metadata, public audio URL, or public audio asset is approved.

## Required Evidence Before Any Public Audiobook Release

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Approved source text | Exact source text, source URL, source license, source hash, content hash, provenance hash, and source approval | incomplete for audiobook release |
| Derivative audiobook rights | Explicit derivative/audio rights for the exact source, edition, language, region, and use case | missing |
| Model commercial-use rights | Model/provider license reviewed for commercial audiobook generation and distribution | missing |
| Voice/narrator rights | Synthetic voice, narrator, or provider voice rights reviewed for commercial public audiobook use | missing |
| Real-person voice cloning | Confirmed no unresolved real-person cloning, imitation, or consent issue exists | unresolved |
| Storage/CDN/public serving | Rights and terms reviewed for storage, CDN delivery, caching, and public serving | missing |
| Attribution | Source, model, provider, and voice attribution requirements reviewed and satisfied | missing |
| Public claims | Marketing, accessibility, and audio claims reviewed against evidence | missing |
| Human listening QA | Bengali and English scorecards complete with scores at or above 9.5 | missing |
| Accessibility listening QA | Keyboard, screen-reader, mobile assistive-tech, transcript, and sync checks complete | missing |
| Support/refund readiness | Support contact, refund path, takedown path, paid-access issue handling, and owner escalation ready | missing |
| Owner/legal approval | Owner and legal/compliance approval recorded for the exact release | missing |
| Rollback approval | Rollback owner, takedown command, refund handling, and metadata removal plan approved | missing |

## Blocking Rules

The release gate must block if any of the following are true:

- Audio is generated from unapproved source text.
- Derivative audiobook rights are missing, unclear, or region-incompatible.
- Model license or commercial-use permission is unknown.
- Voice/narrator rights are unknown.
- Real-person voice cloning risk is unresolved.
- Storage, CDN, public-serving, or caching rights are unknown.
- Required attribution is missing or unreviewed.
- Public copy claims audiobooks are live before approval.
- Public copy claims WCAG compliance, blind-user testing, screen-reader certification, or a fully accessible audiobook platform without evidence.
- Refund/support readiness is missing for paid audiobook access.
- Owner/legal approval is missing.
- Rollback approval is missing.
- PR #44 or PR #45 evidence is treated as final release approval.
- Any audio-like file exists under `frontend/public` or `frontend/build`.

## Current Decision

`PUBLIC_AUDIO_RELEASE_BLOCKED`

This is the correct current state. The gate is suitable for governance and internal QA only. It is not evidence that any audiobook is public-ready.

## Owner Review Checklist

- [ ] Confirm exact book, edition, language, and release region.
- [ ] Confirm source text and source/license evidence.
- [ ] Confirm derivative audiobook rights.
- [ ] Confirm model/provider commercial-use rights.
- [ ] Confirm voice/narrator rights and no unresolved cloning risk.
- [ ] Confirm storage/CDN/public-serving terms.
- [ ] Confirm attribution requirements.
- [ ] Confirm public audio and accessibility claims.
- [ ] Confirm refund/support/takedown readiness.
- [ ] Confirm human listening QA at or above 9.5.
- [ ] Confirm keyboard, screen-reader, transcript, and sync evidence.
- [ ] Confirm rollback owner and rollback procedure.
- [ ] Confirm owner/legal approval.

## Rollback Requirements

If any audiobook evidence is later found unsafe:

- Keep `audio_enabled_slugs` empty.
- Remove public audio URLs and AudioObject metadata.
- Remove Listen Now or equivalent CTAs.
- Remove public audio entries from sitemap, social previews, and static snapshots.
- Pause audiobook paid-access copy.
- Preserve internal evidence and audit logs.
- Run `npm run launch:audio-audit`, `npm run audiobook:release-gate`, and post-deploy canaries before restoring any public audio path.
