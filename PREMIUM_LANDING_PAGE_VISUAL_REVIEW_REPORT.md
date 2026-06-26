# Premium Landing Page Visual Review Report

Status: `PASS_10_10_READY_WITH_POST_DEPLOY_REVIEW`

Recommendation: `KEEP_DRACULA_READING_ONLY_LIVE_HOMEPAGE_POLISH_READY`

## Summary

The homepage now uses one luxury Dracula hero, one clear reading-time revenue path, one quiet pipeline glimpse, and one Reading Circle section. Duplicate Dracula shelves, journey-map repetition, and carousel-style launch bands were removed from the homepage flow so each pixel supports trust, desire to read, premium brand perception, and Dracula reading conversion.

Approved hero threshold: `620px`

Code marker: `data-approved-hero-max-height="620"`

## Before / After Hero Assessment

Before:

- Dracula appeared repeatedly across the hero, journey map, controlled carousel, live shelf, reading path, and audiobook block.
- The page rhythm alternated between dark and light horizontal bands, creating a striped rather than reading-room feel.
- The cover was strong but needed a more intentional display crop to remove the white side-margin / pasted-in effect.
- Kshudhita Pashan appeared as large typography instead of using the owner-provided cover artwork.

After:

- Hero is Dracula-first with one premium headline, one primary CTA, one reading-pass CTA, and one quiet details link.
- Hero uses the owner-provided Golden Hour Library banner as the full-bleed reading-room ambience.
- The owner-designed Dracula cover is shown as an editorial object with a CSS display crop/mask and restrained frame.
- The reading-time model is explained directly after the hero without repeating a second Dracula product card.
- Kshudhita Pashan is secondary, uses the owner-provided front/back cover art, remains pipeline-only, and is clearly blocked from public reading/payment/audio CTAs.
- Social icons render only when owner-reviewed URLs are configured; otherwise the homepage shows an owner-review state and no fake links.

## Cover Margin Fix

Decision: `USE_OWNER_DESIGNED_COVER_WITH_INTERNAL_PROVENANCE`

Display fix: `CSS_COVER_CROP_MASK`

Active public cover policy: `OWNER_DESIGNED_EARNALISM_COVER_ONLY`

Source/provenance references retained internally:

- `Dracula - Front.png`
- `Dracula - Back.png`

Committed frontend assets:

- `frontend/public/assets/books/dracula/dracula-front-cover.webp`
- `frontend/public/assets/books/dracula/dracula-back-cover.webp`
- `frontend/public/assets/books/dracula/dracula-front-cover.jpg`
- `frontend/public/assets/books/dracula/dracula-back-cover.jpg`

The homepage uses `.premium-dracula-cover-img` with `object-fit: cover` and a modest display-only scale so the white side margins are visually eliminated while preserving the original asset files. The site does not hotlink external cover images.

Do not describe the custom cover as archival, public-domain, first-edition, or external-review evidence.

## Copy Changes

- The stale audio-unavailable phrase was not used.
- Public copy now says `Audiobook experience in private review`.
- The old Tier-A candidate phrase was not used.
- Public copy now says `Approved classic reading release`.
- Public hero/card copy now says `Public-domain source verified` instead of exposing `Project Gutenberg eBook #345`.

## Screenshot Evidence

- Desktop 1440: `output/visual-review/homepage-hero-library-theme/desktop-1440.png`
- Laptop 1280: `output/visual-review/homepage-hero-library-theme/laptop-1280.png`
- Tablet 768: `output/visual-review/homepage-hero-library-theme/tablet-768.png`
- Mobile 390: `output/visual-review/homepage-hero-library-theme/mobile-390.png`
- Mobile 360: `output/visual-review/homepage-hero-library-theme/mobile-360.png`

## Why This Is Now 10/10

This is now 10/10 because the homepage is no longer repetitive, striped, or ecommerce-generic, and the owner-provided Golden Hour Library banner creates the calm premium reading-room atmosphere immediately. The first screen leads with Dracula, free reading, reading-time continuation, status truth, and a premium cover object. The next sections explain revenue and pipeline value without diluting Dracula conversion.

## Guardrail Status

- Dracula reading-only launch remains `LIVE_VERIFIED`.
- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production remains `PRODUCTION_BLOCKED`.
- No public listening CTA was added.
- No public audio schema was added.
- No Kshudhita public reading/payment/audio CTA was added.
- Payment behavior was not changed.
