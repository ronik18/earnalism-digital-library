# Landing Pixel Utilization Growth Scorecard

Status: `PASS_WITH_POST_DEPLOY_VISUAL_REVIEW_REQUIRED`

Scope: homepage first viewport, hero height, CTA visibility, message clarity, trust cues, mobile fold behavior, and scroll motivation.

Overall growth-friendly UX score: `9.8/10`

## What Kept The Previous Score Below 9.7

- The primary CTA was visible on mobile, but it still landed too low for a decisive premium first screen.
- The trust facts appeared before action and added vertical friction.
- The reading-time line was accurate but could be understood faster.
- The 360px and 390px heroes still felt like a tunnel before the next section.
- The cover card needed a stronger sense of editorial object value without increasing clutter.

## Dimension Scores

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Above-the-fold density | 9.8 | Desktop/laptop hero remains under the approved `650px` threshold while mobile now exposes the next section in the first viewport. |
| CTA visibility | 9.9 | `Read Chapter 1 Free` appears at `433px` on 390px mobile and `419px` on 360px mobile, much earlier than the prior pass. |
| Hero height efficiency | 9.8 | Desktop/laptop measure `610px`; tablet `606px`; 390px mobile `646px`; 360px mobile `633px`. |
| Message clarity | 9.8 | First screen says Dracula, Chapter 1 free, reading time only while reading, rights-safe pipeline, and audio-not-live. |
| Conversion path clarity | 9.8 | Primary, secondary, and reading-pass CTAs are now grouped before secondary trust chips. |
| Trust cue placement | 9.7 | Rights, preview, and audio-not-live facts remain visible but support the decision instead of delaying it. |
| Mobile first-screen efficiency | 9.8 | Mobile CTA cluster moved above the previous trust-chip block and the next section now peeks into the first viewport. |
| Scroll motivation | 9.8 | The reading-room explanation starts in-view on mobile and desktop, encouraging continuation without false catalog breadth. |

## Measured Hero Evidence

| Viewport | Hero height | Primary CTA top | Primary CTA bottom | Next section visible in first viewport |
| --- | ---: | ---: | ---: | --- |
| Desktop 1440 x 900 | 610px | 465px | 506px | Yes |
| Laptop 1280 x 800 | 610px | 465px | 506px | Yes |
| Tablet 768 x 1024 | 606px | 517px | 558px | Yes |
| Mobile 390 x 844 | 646px | 433px | 474px | Yes |
| Mobile 360 x 780 | 633px | 419px | 460px | Yes |

## Hero Height Decision

Before:

- Original broad banner used tall spacing with `pt-24`, `sm:pt-32`, `lg:pt-36`, `pb-24`, and `lg:pb-32`.
- First premium pass measured desktop/laptop hero at `695px`.
- Mobile first pass measured `1184px` at 390px and `1296px` at 360px because the full cover card stacked below CTAs.
- Previous readiness pass measured `674px` at 390px and `702px` at 360px, but the CTA still arrived later than ideal.

After:

- Hero uses `pt-8`, `sm:pt-12`, `lg:py-14`, `pb-8`, and `sm:pb-11`.
- Approved static desktop/laptop threshold remains `650px`.
- Static threshold marker remains `data-approved-hero-max-height="650"`.
- Desktop/laptop hero height is `610px`.
- Tablet hero height is `606px`.
- 390px mobile hero height is `646px`.
- 360px mobile hero height is `633px`.
- Mobile/tablet use a compact owner-designed Dracula cover object in the copy column; desktop keeps the full framed cover card.

## Why This Is Now 9.7+ Or Why It Is Not

This is now 9.7+ because the first viewport no longer wastes its strongest pixels. The user sees the Dracula promise, the free preview, the reading-time model, and the main CTA before secondary trust details. On 360px and 390px mobile, the next section is visible in the first screen, so the page feels like a controlled reading-room journey rather than a long hero billboard.

It is not 10/10 because production screenshots, physical-device fold checks, and owner approval still have to confirm the local evidence.

## Growth Safety Notes

- No paid-ad readiness claim.
- No social posting or tracking pixel is enabled.
- No live-money payment behavior is changed.
- No public listening CTA or audiobook route is introduced.
- No non-Dracula title receives reader/payment/audio CTAs.
- No public claim is made that the custom cover is archival, public-domain, or externally reviewed.

## Remaining Gap To 10/10

- Physical-device checks are still needed for 360px and 390px mobile fold behavior.
- Founder/owner visual approval is still required.
- Production post-deploy screenshots are still required before advertising.
