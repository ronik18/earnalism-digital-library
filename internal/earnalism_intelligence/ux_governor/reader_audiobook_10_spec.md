# Reader and Audiobook 10/10 Spec

## Intent

The Reader must feel like a quiet reading room. Audiobook UI is an evidence-backed layer, not a default promise.

## Reader Requirements

- Centered reading column with generous max width.
- Calm top toolbar with back, title, progress, contents, settings, and audio toggle only if approved.
- Light, sepia, and night themes.
- Font size, line-height, margin width, and theme controls.
- Bengali font mode and English font mode.
- Focus or distraction-free mode.
- Reading progress and table of contents.
- Reduced motion support.

## Bengali and English Typography

- Bengali reader default: 19px-21px with 1.8-2.0 line-height.
- English reader default: 18px-20px with 1.65-1.8 line-height.
- UI labels must remain readable and compact.

## Audiobook Requirements

- Approved audiobook mini-player only when reader manifest, endpoint, sidecars, and release gate pass.
- Play/pause, skip, speed, progress, elapsed/duration, and accessible labels.
- Paragraph/stanza sync support.
- Customer-facing copy: section-following narration.
- Internal/evidence copy: PARAGRAPH_OR_STANZA_SYNC_PREMIUM.
- No word-level claim for paragraph/stanza sync.
- No fallback speech as audiobook.

## Mobile Requirements

- Reading content first.
- Settings in bottom sheet or drawer.
- Audio player collapses gracefully.
- Controls are keyboard and touch accessible.
