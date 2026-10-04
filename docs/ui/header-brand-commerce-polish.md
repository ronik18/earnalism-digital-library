# Shared header / Commerce polish

## Architecture inventory

- `components/Layout.jsx` mounts `components/Header.jsx` for Home, Library, BookDetail, Journal/article, About, Contact, Privacy, Terms, Copyright, Pricing, Login, Signup, Account and MyLibrary (including redirects/not-found).
- Public Reader and Listener reuse that same Header through `experiences-v2/shared/ExperienceHeader.jsx`. The existing `onNavigatePath` callback continues to settle their sessions before navigation.
- Legacy Reader retains its intentionally minimal reading controls; admin/login and admin tools remain separate privileged surfaces. Full primary navigation is not added there.
- The header uses `EarnalismBrandLockup.jsx` and the existing 2400 × 720 official PNG `public/assets/brand/earnalism-brand-lockup.png` (existing original-logo fallback retained).
- Header.css owns responsive dimensions and controls; global `--site-header-height` still accounts for Reader usable height. Old route modifiers are no longer emitted, preventing Home-only shadow/border/layout overrides.

## Changes

One identical primary shell class on every route; shared navigation selectors outrank immersive link inheritance (preventing Reader navigation weight drift); existing canonical navigation, active states, auth state, focus trap, Escape/focus restoration, search, social controls and immersive exit callbacks retained.

Logo widths: desktop 300 → 320px; tablet 280 → 288px; mobile cap 240 → 256px, bounded by viewport minus 136px (254px at 390). Intrinsic 10:3 aspect ratio is preserved; no cropping, transforms, CSS zoom or new assets. Header heights remain 104/96/80px. Desktop search can shrink to 128px. At 1280–1439px the existing search icon replaces the full field, retaining all desktop navigation items without a logo/control collision.

Commerce `ReadingPassesSurface.jsx` hero has literal presentation copy `NO` instead of literal `0`; no numeric state, offer, billing, entitlement or renewal logic was changed.

## Verification workflow

Normal production build and frontend suite must pass. For the isolated existing visual fixtures, build locally with `REACT_APP_ENABLE_VISUAL_FIXTURES=1`; never use that flag for deployment. Run `scripts/capture_pr471_canonical_header_matrix.mjs` against a loopback build server. The matrix covers 19 routes × six viewports, official asset loading, route-aware active navigation, mobile menu/focus behavior, document/header overflow and browser errors. Temporary screenshot/zoom artifacts remain outside Git.

No production deployment or catalogue activation is part of this change.

## Local results

Focused Header/Pricing: 5 suites / 33 tests. Full frontend: 97 suites / 618 tests. Normal production build passed; static SEO: 172 snapshots / 3,647 assertions. Chromium: 114 successful route/viewport combinations (19 routes × six sizes) plus 15 additional rendered screenshot comparisons and actual 125% / 150% tab zoom on five representative routes. All checks passed after resolving immersive typography drift and the compact-desktop logo/search collision. No standalone lint/typecheck scripts are defined; the canonical build includes its existing checks.

Local evidence is outside Git: `/tmp/ui-brand-polish-ready/summary.json` and `header-contact-sheet.html`, `/tmp/ui-polish-additional-views/summary.json`, and native zoom captures in `/tmp/ui-polish-verified-zoom125/` and `/tmp/ui-polish-verified-zoom150/`.
