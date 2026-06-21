# Branding Advertisement GO/NO-GO

## Environment

- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Branch context: `codex/premium-social-brand-kit` rebased after the site-tour and audiobook governance work.

## Recommendation

Decision: `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`
Owner recommendation: `KEEP_DRACULA_LIVE`

Dracula may stay live. Paid ads, broad branding, and acquisition campaigns remain held until overlay export, captions, checksums, duration verification, production canaries, real-user UX evidence, real social profile URLs, and human owner review all pass.

## Current Evidence

| Area | Status |
| --- | --- |
| Brand site-tour overlay | `PASS` |
| Brand site-tour captions | `MUXED_IN_MASTER_MP4` |
| Brand site-tour score | `9.0/10` |
| Human video review | Owner approval still required before paid ads. |
| Backend catalog truth | Must pass again after deployment. |
| Real-user hydrated UX | Existing artifacts remain evidence; rerun before ads. |
| Static Dracula book SEO | Local snapshot audits pass. |
| Social preview tags | Local social preview audit passes. |
| Social profile brand kit | `READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP`; owner upload required. |
| Social link validation | `OPERATOR_REQUIRED` until real profile URLs are configured. |
| Dracula audio | Disabled as required. |
| Non-Dracula books | Pipeline-only; no live reader, preview, or audio CTA allowed. |

## Brand Site-Tour Evidence

- Recommendation: `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`
- Master video: `output/brand-site-tour/latest/earnalism-site-tour-master.mp4`
- Artifact index: `BRAND_SITE_TOUR_VIDEO_INDEX.md`
- Human review form: `BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md`

## Required Before Ads

- `npm run launch:backend-catalog-truth-canary`
- `npm run launch:seo-audit`
- `npm run launch:social-preview-audit:prod`
- `npm run release:post-production-canary`
- `npm run release:ux-go-no-go`
- Human owner must approve the final master and social cutdowns.
- Real owner-created social profile URLs must be configured and validated.

Never mark `GO_FOR_BRANDING_AND_ADVERTISEMENT` while overlays are missing, backend catalog truth fails, raw production SEO/social-preview fails, Playwright fails, unapproved titles expose live CTAs, social links are unverified, or owner approval is missing.

The social brand kit is not an ads approval. Paid social remains blocked until real owner-created profiles, valid public profile URLs, and owner-approved screenshots exist.

No publication, ad, email, social post, payment, provider call, audio enablement, or production data mutation was performed by this package.
