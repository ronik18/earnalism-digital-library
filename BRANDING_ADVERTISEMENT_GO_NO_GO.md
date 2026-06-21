# Branding Advertisement GO/NO-GO

## Environment

- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Branch: `codex/premium-site-tour-video-package`

## Recommendation

Decision: `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`
Owner recommendation: `KEEP_DRACULA_LIVE`

Dracula may stay live. Paid ads, broad branding, and acquisition campaigns remain held until overlay export, captions, checksums, duration verification, production canaries, real-user UX evidence, and human owner review all pass.

## Brand Site-Tour Evidence

- Overlay status: `PASS`
- Caption status: `MUXED_IN_MASTER_MP4`
- Score: `9.0/10`
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

Never mark `GO_FOR_BRANDING_AND_ADVERTISEMENT` while overlays are missing, backend catalog truth fails, raw production SEO/social-preview fails, Playwright fails, or unapproved titles expose live CTAs.

No publication, ad, email, social post, payment, provider call, audio enablement, or production data mutation was performed by this package.
