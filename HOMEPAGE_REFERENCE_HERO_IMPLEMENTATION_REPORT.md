# Homepage Reference Hero Implementation Report

## Scope

- Implemented the reference-style homepage hero and Shelf 2 pipeline section.
- Preserved the existing Earnalism logo, header layout, navigation labels, sign-in link, and Start Dracula header CTA.
- Kept Dracula as the only live approved reading release.
- Kept pipeline books as Coming Soon with Notify Me only.

## Header / Logo Confirmation

No header, logo, navigation, sign-in, or header CTA files were changed in this pass. The implementation work is scoped to the homepage, shared launch copy, static SEO fallback copy, visual styles, and regression evidence.

## Hero Background Treatment

- Uses the local optimized `frontend/public/assets/hero/golden-hour-library-hero.webp`.
- Keeps visible classical library shelves and warm lamp ambience.
- Uses layered gradients and a warm vignette for readability instead of a flat chocolate overlay.
- Keeps the hero efficient with `data-approved-hero-max-height="650"`.
- No external hotlinks were added.

## Dracula Cover Treatment

- Dracula remains the primary conversion object on the right side of the hero.
- The full top title remains visible.
- The hero now uses a display-only hard-copy object extracted from the owner-provided reference mockup: `/assets/books/dracula/dracula-hero-hardcopy.webp`.
- The hard-copy asset includes the book spine/depth and the approved-release plaque shown in the reference image.
- The crop was converted into a transparent display cutout so it overlaps the hero background smoothly instead of carrying a rectangular source-image edge.
- Pixel audit result: 0 opaque outer-edge pixels and 0 near-white opaque outer-edge pixels on the hard-copy asset.
- The hero shell has no border, no ivory background, and no white frame.
- Original Dracula cover assets remain preserved for provenance and non-hero public surfaces.
- Public plaque remains truthful: Approved classic reading release and public-domain source verified.

## Shelf 2 Pipeline Treatment

- Added a cream/ivory Shelf 2 section directly below the hero.
- Heading: Coming Through the Rights-Safe Pipeline.
- Pipeline copy explicitly says the books are not live products and have Notify Me CTAs only.
- Cards included:
  - Kshudhita Pashan, by Rabindranath Tagore
  - Frankenstein, by Mary Wollstonecraft Shelley
  - Sherlock Holmes, by Arthur Conan Doyle
  - Sultana's Dream, by Rokeya Sakhawat Hossain
- Kshudhita, Frankenstein, and Sherlock Holmes use local cover artwork.
- Sultana's Dream uses a premium placeholder because no rights-safe local cover evidence was found in this pass.

## Copy Changes

- Replaced the old Dracula-first hero with:
  - Step into the classics.
  - Stay with the story.
  - Timeless stories. Beautifully presented. Yours to read, reflect, and remember.
- Public audio copy now uses: Audiobook experience in private review.
- Public-facing internal tier language was softened to approved classic reading release.
- Removed public-facing stale/pessimistic copy such as Audio is not available yet.

## Social Row Status

The footer/contact social system was not redesigned in this pass. The homepage retains the existing lower Reading Circle/social area and only renders social links when configured by the existing settings layer.

## Public Claims Audit

Confirmed in the implementation and regression coverage:

- No public audiobook availability claim.
- No public listening CTA.
- No public audio structured-data metadata.
- No pipeline Start Reading, payment, or audio CTA.
- No broad catalog live claim.
- No unsupported accessibility/WCAG claim.
- No buy/own-forever claim.
- Payment behavior unchanged.

## Visual Evidence

- `output/visual-review/homepage-reference-hero-shelf/homepage-desktop-1440.png`
- `output/visual-review/homepage-reference-hero-shelf/homepage-laptop-1280.png`
- `output/visual-review/homepage-reference-hero-shelf/homepage-tablet-768.png`
- `output/visual-review/homepage-reference-hero-shelf/homepage-mobile-390.png`
- `output/visual-review/homepage-reference-hero-shelf/homepage-mobile-360.png`
- `output/visual-review/homepage-reference-hero-shelf/library-desktop-1440.png`

## Screenshot QA Result

Local production build screenshots were captured from `http://127.0.0.1:4173` with production API calls safely aborted. The UI rendered from committed fallback data. Results:

- Render-breaking page errors: 0
- Local screenshot capture intentionally aborted API requests; those network messages were not product render failures.
- Broken images: 0
- Horizontal overflow: false at 1440, 1280, 768, 390, and 360 widths
- First-visit tour was marked complete for clean design screenshots

## Performance / LCP Note

- Hero background asset remains local and optimized.
- Golden Hour Library hero asset is approximately 107 KB.
- Display-only Dracula hard-copy hero asset is approximately 66 KB.
- Pipeline covers are local optimized WebP assets.
- The four Shelf 2 covers are eager-loaded so visual evidence and first landing scroll do not show blank lazy placeholders.
- Build size impact remained small: main CSS increased by only a few bytes after overflow containment, and one JS chunk increased by about 10 bytes after eager-loading logic.

## Recommendation

GO for review as a homepage design improvement, provided the full launch validation suite passes.
