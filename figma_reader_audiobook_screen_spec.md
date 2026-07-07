# Earnalism Reader And Audiobook Screen Spec

## Reader Structure
- Top toolbar: back, title, progress, bookmark, contents, settings.
- Reading canvas: ivory/sepia/night surfaces with centered literary measure.
- Bottom bar: page/chapter controls and audio status/player.
- Mobile: reading content first, bottom controls compact, settings as bottom sheet.

## Settings
- Font size.
- Line height.
- Margin width.
- Theme: Ivory, Sepia, Night.
- Font mode: Serif, Sans.
- Focus mode.
- Reduced motion.
- Highlight intensity.

## Approved Audiobook Layer
- Render only when release gate, provider-backed audio, endpoint, sidecars, QA, and browser evidence exist.
- Controls: play/pause, stop, speed control in settings.
- Paragraph/stanza sync label: `Section-following narration`.
- Internal sync label: `Paragraph/Stanza Sync`.
- Do not claim word-level sync for paragraph/stanza releases.

## Unavailable Audio State
`Reading edition available. Audio will appear only after narration, sync, and browser gates pass.`
