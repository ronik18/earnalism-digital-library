# Home Hero Editorial Coverflow v3

Status: `SOURCE_VALIDATED_BRANCH_READY`

## Diagnosis

The previous hero implementation paginated four equal-width covers and crossfaded whole frames. Each jacket owned its own shallow transform, but the group had no shared coverflow perspective, no active-book hierarchy, and no mathematical previous/active/next state. Permanent `will-change`, frame remounting, and a transparent stage plane also made smooth pointer-safe 3-D behavior fragile.

The production v4 Home feed separately regressed known visual placeholders back into the hero. The first live candidate, `book-2b9853ec52`, is explicitly blocked by the owner-reviewed graphical-cover report but was still marked cover-valid by v4. This was a release-truth issue, not a CSS issue.

## Implemented result

- One stable, non-cloned Sprint 1 slide set with circular index math.
- Exactly three meaningful slides on desktop: previous, active, and next.
- Shared `1100px` perspective with separate slide-position, book-tilt, and front-face wrappers.
- Consistent front, spine, outer page block, bottom page block, contact shadow, amber rim light, and active radial glow.
- Equalized rendered left/right gaps by matching the perspective origin to the visual coverflow center.
- Localized depth-safe mask behind the live jackets so the baked reference jackets do not compete with runtime covers.
- Compact active-title plaque and controls on full desktop; safe compressed treatment at 1024x768.
- Native previous, next, and rotation controls; keyboard arrows; side-book selection; active-book navigation; pointer swipe.
- Autoplay starts only after the initial image decodes, pauses for hover, drag, focus, and hidden tabs, and does not resume after focus without explicit play.
- Reduced motion disables autoplay and uses a 120 ms opacity transition.
- Initial cover alone receives high fetch priority; adjacent covers preload next; distant covers stay lazy.
- Backend v4 now reuses the existing owner-reviewed cover exclusion report for the hero only. Audiobook availability and other shelves are unchanged.

## Browser evidence

Production baselines and post-change captures:

| Viewport | Before | After |
| --- | --- | --- |
| 1536x864 | `before/home-1536x864.png` | `after/home-1536x864.png` |
| 1440x900 | `before/home-1440x900.png` | `after/home-1440x900.png` |
| 1366x768 | `before/home-1366x768.png` | `after/home-1366x768.png` |
| 1024x768 | `before/home-1024x768.png` | `after/home-1024x768.png` |
| 768x1024 | `before/home-768x1024.png` | `after/home-768x1024.png` |
| 390x844 | `before/home-390x844.png` | `after/home-390x844.png` |

The after captures use the live production Home payload projected through the updated checked-in visual-cover exclusions, matching the backend result after deployment.

Measured outcomes:

- Meaningful visible slides: exactly `3` at every target viewport.
- Desktop rendered gaps: `22/21px`, `22/21px`, and `20/19px`.
- Tablet rendered gaps: `13/13px` and `18/18px`.
- Mobile rendered gaps: `4/3px`, with no overlap.
- Horizontal overflow: `0px` at all six viewports.
- Hidden focus targets: `0`.
- Browser console errors in the controlled runtime pass: `0`.
- Touch targets: `44px` at 768px and 390px widths.
- 200% text resize horizontal overflow: `0px`.

Full metrics: `HOME_hero_coverflow_v3_browser_metrics.json`.

## Asset review

The 13 graphically eligible Sprint 1 carousel covers were inspected. Twelve are 1024x1536; `book-d19e96859f` is a full-bleed 1122x1402 variation. None has an alpha channel and none contains a removable baked cream card. No derivative was generated because a blind crop would remove real cover art or typography.

## Validation

- Frontend: 26 suites / 132 tests passed.
- Backend Home and release-truth slice: 49 tests passed.
- Focused Home v4 tests: 15 passed.
- Browser regression: passed.
- Production frontend build: passed.
- Responsive browser interaction audit: passed.

## Deliberate constrained-height adaptation

At 1024x768 the photographic hero leaves only a narrow vertical band between the upper benefits panel and the baked bottom feature rail. The live active book is therefore 138px and the visible caption is suppressed at that one constrained breakpoint. This is intentional: it preserves the phone/tablet artwork, keeps all three covers separated, and prevents panel or rail collisions. The accessible slide label still exposes position, title, and author.

## Next exact command

```bash
git push -u origin codex/editorial-hero-coverflow
```
