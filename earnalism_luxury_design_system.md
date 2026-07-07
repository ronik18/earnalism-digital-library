# Earnalism Luxury Design System

Generated: 2026-07-06

## Brand Direction

Earnalism should feel like a luxury digital reading sanctuary: calm, literary, collectible, intelligent, culturally precise, and trustworthy. The interface should feel editorial rather than SaaS, with high contrast, warm surfaces, disciplined motion, and reader-first hierarchy.

## Principles

- Release truth before persuasion.
- Reader-only experiences must feel complete.
- Audiobook controls are earned by evidence, not by aspiration.
- Bengali and English typography must both feel native and dignified.
- Decorative luxury must not reduce accessibility or speed.

## Tokens

| Token | Use |
| --- | --- |
| Burgundy deep | Primary brand authority, headers, CTA states |
| Readable gold | Premium accents, overlines, focus-visible accents |
| Ivory warm | Main page surface |
| Sepia canvas | Reading ambience |
| Charcoal soft | Longform supporting copy |

## Typography

- Display: Cormorant Garamond / Playfair Display for literary headlines.
- Reader English: Crimson Pro / Lora-style serif rhythm.
- Bengali: Noto Serif Bengali for literary body and Noto Sans Bengali for UI labels.
- Overlines: must meet WCAG AA; decorative gold must be dark enough on ivory or light enough on dark panels.

## Components

### Cover System

- Customer-facing covers must be graphical and content-themed, never plain typography-only panels.
- Missing or failed covers resolve through the shared `BookCoverImage` / cover resolver path to a lightweight graphical fallback.
- AI or generated background art must not contain title or author text baked into the image; exact text belongs in deterministic HTML/SVG overlays or adjacent UI.
- Covers need explicit dimensions or stable aspect ratios to prevent layout shift.
- Non-LCP covers load lazily with async decoding; only the true LCP cover may be eager/high priority.
- Keep approved graphical covers; do not replace good assets merely for novelty.

### Book Cards

- Cover-first.
- Explicit availability badges:
  - Live/Preparation state.
  - Listen approved / Audio hidden.
- Hover/focus should lift gently without noisy animation.

### Book Detail

- Large cover with editorial metadata.
- Primary reader CTA.
- Audiobook CTA only when release gate is approved.
- Trust panel: reader state, audio state, release truth.

### Reader

- Light, sepia, dark modes.
- Sticky controls.
- Premium audio-hidden state.
- No browser/system fallback represented as audiobook.

### Audiobook

- Player is visible only after approved metadata, QA status, release gate, and audio asset are present.
- Hidden/unavailable state should be quiet and intentional.
- Reader-manifest audio may unlock the reader audiobook UI only when the manifest is provider-backed, versioned, enabled, and asset-backed.
- Catalog/detail pages stay conservative unless their production metadata or manifest evidence proves availability.

### Approved Audiobook Spotlight

- Used only for proven audiobook releases.
- Fetches production reader-manifest evidence before rendering.
- Does not render on fetch failure, missing provider/version/assets, blocked status, or absent approval proof.
- Copy must explain that other titles remain reader-only/audio-hidden until release gates pass.

### Luxury UX Index

- No category can be considered final until same-origin deployed route validation passes.
- Localhost CORS limitations must be recorded as validation blockers, not silently ignored.
- A score above 9.7 requires clean diff hygiene, deployed browser evidence, and no release-gate truth gap.

## Accessibility Rules

- WCAG AA contrast for all text, including microcopy.
- Visible keyboard focus on links/buttons/inputs.
- Reduced-motion support for skeleton/motion states.
- No ARIA labels on elements without valid roles.

## Performance Rules

- Do not add heavy UI libraries for decoration.
- Prefer CSS gradients/textures over large image effects.
- Lazy-load non-critical covers.
- Keep runtime graphical fallbacks lightweight and avoid repeating large data URIs in `srcset`.
- Keep generated screenshots/traces out of git.

## Calm Typography Pass

- Hero titles should use conservative `clamp()` or equivalent responsive class caps and should not dominate the viewport.
- Shelf headings should feel editorial and quiet, generally below the old oversized 4xl/5xl feel on first-screen sections.
- Card titles should be compact but readable, with long Bengali/English titles protected from cramped line-height.
- Overlines and badges should use reduced tracking and size where excessive spacing makes the interface feel loud.
