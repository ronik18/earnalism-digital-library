# Landing Pixel Utilization Growth Scorecard

Status: `PASS_WITH_POST_DEPLOY_VISUAL_REVIEW_REQUIRED`

Scope: homepage first viewport, hero height, CTA visibility, message clarity, trust cues, mobile fold behavior, and scroll motivation.

Overall growth-friendly UX score: `9.6/10`

## Dimension Scores

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Above-the-fold density | 9.7 | Desktop/laptop hero is now 588px, down from 695px, while retaining the cover, headline, truth facts, and CTAs. |
| CTA visibility | 9.7 | Read Chapter 1 Free appears in the first viewport on desktop, laptop, tablet, 390px mobile, and 360px mobile. |
| Hero height efficiency | 9.7 | Static threshold marker is `data-approved-hero-max-height="650"` and regression checks enforce it. |
| Message clarity | 9.6 | First screen communicates Dracula, Chapter 1 free, reading time, pipeline, and audio-not-live truth. |
| Conversion path clarity | 9.5 | Primary, secondary, pricing, and pipeline CTAs remain distinct; pipeline is visually de-emphasized on mobile. |
| Trust cue placement | 9.3 | Rights note and audio-not-live cue remain visible but quieter than the main conversion path. |
| Mobile first-screen efficiency | 9.5 | 390px hero dropped from 1184px to 674px; 360px hero dropped from 1296px to 702px. |
| Scroll motivation | 9.4 | The next section is visible sooner, so readers see how the reading room works without a long hero tunnel. |

## Hero Height Decision

Before:

- Original broad banner used tall spacing with `pt-24`, `sm:pt-32`, `lg:pt-36`, `pb-24`, and `lg:pb-32`.
- First premium pass measured desktop/laptop hero at `695px`.
- Mobile first pass measured `1184px` at 390px and `1296px` at 360px because the full cover card stacked below CTAs.

After:

- Hero uses `pt-11`, `sm:pt-14`, `lg:py-14`, `pb-10`, and `sm:pb-12`.
- Approved static desktop/laptop threshold is `650px`.
- Measured desktop/laptop hero height is `588px`.
- Tablet hero height is `631px`.
- 390px mobile hero height is `674px`.
- 360px mobile hero height is `702px`.
- Mobile/tablet use a compact owner-designed Dracula cover object in the copy column; desktop keeps the full framed cover card.

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
