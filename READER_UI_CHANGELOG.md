# Reader UI Changelog

## Premium Reader Refresh

- Restored the Earnalism burgundy, beige, warm white, gold, and ink palette through reader-specific CSS variables.
- Reworked the top bar into a calm reader toolbar with a truncated book title, chapter/page context, and 40px icon targets.
- Replaced generic `Full Text` presentation with the book title from metadata.
- Added a front-matter parser in the UI layer so leading author, collection, year, and repeated title lines render as a styled book header instead of raw body text.
- Added a centered literary title block, Bengali-friendly heading typography, and an ornamental gold divider.
- Rebuilt the reading surface as a centered warm-white page with subtle paper grain, shadow, and responsive padding.
- Added a drop cap to the first paragraph while preserving Bengali line height and left alignment.
- Refined body typography: Noto Serif Bengali for Bengali, Lora for English, Inter for UI labels.
- Replaced visible raw watermark strings with a faint diagonal DRM watermark overlay that stays out of content flow.
- Upgraded the bottom progress bar with a burgundy-to-gold fill, thumb indicator, and estimated time remaining.
- Reworked the bottom audio/navigation controls into three clear zones with ghost previous/next buttons and a filled narration pill.
- Added a subtle waveform animation while narration is active.
- Rebuilt reading settings as a branded bottom sheet with font size, line spacing, theme, font family, and narration speed controls.
- Added bookmark ribbon styling to the reading card when a bookmark is set.
- Added responsive layouts for mobile, tablet, and desktop, including faint desktop gutter patterns.
- Added reduced-motion handling for page, highlight, sheet, and control animations.

## Scope

Only reader UI-layer files were changed. Backend logic, routing, audio engine behavior, and manifest/import handling were not changed.
