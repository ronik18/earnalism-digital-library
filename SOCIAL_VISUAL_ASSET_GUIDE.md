# Social Visual Asset Guide

Status: `READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP`

The social brand kit uses deterministic SVG masters. No external fonts, stock photos, copyrighted images, AI image generation, upload, or platform API call is required.

## Visual Direction

- Deep black or near-black backgrounds.
- Warm ivory text and panels.
- Antique gold hairline rules.
- Subtle paper texture made from inline SVG shapes.
- Literary serif fallback: Georgia, Times New Roman, system serif.
- Quiet reading-room mood.
- Minimal ornament.

Avoid:

- cheap horror graphics
- neon color
- fake leather texture
- cluttered AI-art compositions
- fake human narration badges
- audiobook claims
- broad live catalog claims

## Asset Outputs

SVG masters are generated under:

- `output/social-brand-kit/latest/`
- `assets/social_brand/source/`

The expected masters include:

- avatar-master.svg
- avatar-square.svg
- platform avatars for Instagram, YouTube, LinkedIn, Facebook, X, WhatsApp Channel, and Telegram
- youtube-banner.svg
- linkedin-cover.svg
- facebook-cover.svg
- x-header.svg
- Instagram highlight covers
- first-post-dracula.svg
- first-post-story-reel-cover.svg
- pinned-post-return-to-reading.svg
- dracula-launch-card.svg
- bengali-gothic-coming-card.svg
- journal-collaboration-card.svg

If a local SVG rasterizer is unavailable, PNG/JPG export is marked `OPERATOR_EXPORT_REQUIRED`. Do not invent raster files or upload generated files externally from this PR.

## Platform Notes

- Instagram: use `avatar-square.svg`, `first-post-dracula.svg`, and highlight covers.
- YouTube: use `youtube-avatar.svg` and `youtube-banner.svg`.
- LinkedIn: use `linkedin-avatar.svg` and `linkedin-cover.svg`.
- Facebook: use `facebook-avatar.svg` and `facebook-cover.svg`.
- X: use `x-avatar.svg` and `x-header.svg`.
- WhatsApp Channel: use `whatsapp-avatar.svg`.
- Telegram: use `telegram-avatar.svg`.

## Review Gate

Before paid social advertising, the owner must confirm:

- avatar renders cleanly at small sizes
- cover text is not cropped on platform previews
- no broad live catalog claim appears
- no audiobook claim appears
- Dracula is the only live title named as available
- Bengali Gothic remains future/pipeline phrasing
- final screenshots are saved for evidence
