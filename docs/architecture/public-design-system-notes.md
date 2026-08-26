# Public design-system notes

## Reference authority

The immutable boards named in `docs/design-references/reference-manifest.json`
are the visual authority. Their SHA-256 values were verified on 2026-08-26.
The customer lockup is the already committed owner-approved file
`frontend/public/assets/brand/earnalism-brand-lockup.png` (SHA-256
`951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919`).
No logo is redrawn, recolored, remotely fetched, or used as a Canva runtime
dependency.

## Shared primitives

- `EarnalismBrandLockup` is the visible customer-shell logo authority.
- `PublicSurface` provides a semantic page wrapper, editorial or reading-room
  tone, compact eyebrow, page title, and optional action region.
- `PublicInfoCard` provides a single accessible card geometry for trust,
  status, and supporting material.
- Existing `Header`, `Footer`, `AuthPageShell`, and V2 experience primitives
  remain the shell boundary; no new router, store, API client, or CSS framework
  is added.

## Tokens and responsive contract

The implementation uses the existing `frontend/src/design-system` bridge and
the reference contract: 64px navigation, 16/24/40px page gutters, 42px
controls, 10px card radii, 2:3 covers, display serif plus UI sans, warm ivory
discovery surfaces, and near-black experiential surfaces. New shared styles
are feature-local and avoid changing Reader/Listener authorization behavior.

## Product truth

The sole visible preview label is `First 3 pages free preview`. Supporting copy
may state that reading time is used only while reading. Audiobooks remain
fail-closed: no free-audio copy, no public preview, no CTA or player for
unapproved audio, and no change to canonical page or Reading Pass logic.

## Accessibility and performance

Shared controls preserve labels, focus indicators, 44px mobile targets and
reduced-motion-safe behavior. No route adds a data request; static imagery has
dimensions, below-fold work remains lazy, and routes reuse the current
lazy-loaded architecture.
