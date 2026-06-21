# Social Profile Revamp Report

Status: `READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP`

Recommendation: `NOT_READY_FOR_PAID_SOCIAL_ADS`

Owner action: `OWNER_UPLOAD_REQUIRED`

## Summary

This PR creates a premium Earnalism social media brand kit for manual profile setup across Instagram, YouTube, LinkedIn, Facebook, X, WhatsApp Channel, Telegram, and future social surfaces.

No social profile was created. No asset was uploaded. No social API was called. No email, message, campaign, live payment, paid provider, audiobook, or public publication action was performed.

## Launch Truth

- Dracula by Bram Stoker is the only live approved Tier A core reading title.
- Dracula audio remains disabled.
- Kshudhita Pashan remains pipeline-only.
- Bengali Gothic may be described as coming through a rights-safe pipeline.
- No broad live catalog claim is approved.

## Files Added

- `data/social_brand/earnalism_social_brand.json`
- `data/social_brand/platform_profiles.json`
- `data/social_brand/pinned_posts.json`
- `data/social_brand/asset_manifest.json`
- `scripts/generate_social_brand_assets.py`
- `scripts/validate_social_links.py`
- `assets/social_brand/source/`
- `output/social-brand-kit/latest/`
- `SOCIAL_PROFILE_COPYBOOK.md`
- `SOCIAL_VISUAL_ASSET_GUIDE.md`
- `SOCIAL_ASSET_INDEX.md`
- `SOCIAL_LINK_COLLECTION_RUNBOOK.md`
- `SOCIAL_PINNED_POSTS.md`
- `SOCIAL_PROFILE_OWNER_UPLOAD_CHECKLIST.md`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.md`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.json`

## Safety Controls

- The generator only writes local SVG assets and reports.
- The validator performs local syntax/domain validation only.
- No fake social links are added to production code.
- Footer social links remain env-driven and hidden unless real http/https URLs are configured.
- Paid ads stay blocked until owner-upload verification and valid links exist.

## Current Blockers

- Real social profiles are not verified.
- Owner profile screenshots are not attached.
- Social env URLs are not configured.
- Paid ads have not been owner-approved.

## Next Operator Actions

1. Run `npm run social:brand-kit`.
2. Review SVG assets in `output/social-brand-kit/latest/`.
3. Create social profiles manually.
4. Upload avatar/banner assets manually.
5. Paste copy from `SOCIAL_PROFILE_COPYBOOK.md`.
6. Configure verified social URL env vars.
7. Run `npm run social:links:validate`.
8. Capture owner screenshots before any ad decision.
