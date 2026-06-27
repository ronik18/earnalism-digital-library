# Homepage Hero Library Theme Review

Status: `PASS_10_10_HERO_READY_WITH_POST_DEPLOY_REVIEW`

Hero background asset: `frontend/public/assets/hero/golden-hour-library-hero.webp`

Latest refinement: `LEFT_LIBRARY_DETAIL_RESTORED`

Cover refinement: `DRACULA_TITLE_FULLY_VISIBLE`

## Summary

The homepage hero now uses the owner-provided Golden Hour Library image as a full-bleed classical reading-room banner instead of a flat brown field. The committed asset is an optimized local WebP derived from the owner-provided image, so it is not hotlinked, does not imply broad catalog availability, and carries no third-party tracking or external dependency.

## Background Treatment Refinement

Before this pass, the left side of the hero used a broad near-opaque dark overlay. It kept text readable, but it also collapsed the bookshelves and wood texture into a flatter chocolate-brown panel.

This pass replaces that heavy mask with a more refined layered treatment:

- Reduced the broad left overlay opacity so bookshelf spines and wood grain remain visible behind the copy.
- Added a localized text scrim behind the headline instead of masking the whole left half.
- Kept a warm vignette at the edges for luxury depth without flattening the library image.
- Kept mobile readability by using a viewport-specific layered contrast stack, not a generic opaque block.

Result: the hero reads more immediately as a real classical library while preserving headline and CTA contrast.

## Dracula Cover Treatment Refinement

Before this pass, the hero cover used a zoomed crop inside the premium frame. The frame felt strong, but the top title area could read as accidentally cut off.

This pass keeps the same premium frame, glow, and shadow treatment while changing the displayed cover image to a contained, top-aligned presentation. The full `Dracula` title is now visible, the jacket no longer feels cropped, and the cover remains the flagship conversion object beside the hero copy.

## Hero Design Rationale

- The Golden Hour Library banner establishes a quiet reading-room atmosphere before the user reads any copy.
- The left content zone keeps the message simple: Earnalism, Dracula, one approved classic, free Chapter 1, reading-time continuation.
- The owner-designed Dracula cover remains the featured object on the right and is framed as an editorial library artifact.
- The hero avoids the old broad-shelf claim pattern while using a real library-room visual language.

## Copy Used

- Overline: `The Earnalism Digital Library`
- Headline: `Begin with Dracula.`
- Supporting line: `A quiet digital reading room for timeless books.`
- Body: `The Earnalism launch begins with one approved classic. Read Chapter 1 free, continue with reading time, and return to your place whenever you wish.`
- Helper line: `Reading time is used only while you read.`

## CTA Hierarchy

1. `Read Chapter 1 Free`
2. `Start Dracula`
3. `Get 7-Day Reading Pass`

## Screenshot Evidence

- Desktop 1440: `output/visual-review/homepage-hero-cover-polish/desktop-1440.png`
- Laptop 1280: `output/visual-review/homepage-hero-cover-polish/laptop-1280.png`
- Tablet 768: `output/visual-review/homepage-hero-cover-polish/tablet-768.png`
- Mobile 390: `output/visual-review/homepage-hero-cover-polish/mobile-390.png`
- Mobile 360: `output/visual-review/homepage-hero-cover-polish/mobile-360.png`

## Guardrail Status

- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production remains `PRODUCTION_BLOCKED`.
- No public listening CTA was added.
- No public audio schema was added.
- No Kshudhita public reading/payment/audio CTA was added.
- No broad catalog/live-shelf claim was added.
- Payment behavior was not changed.
