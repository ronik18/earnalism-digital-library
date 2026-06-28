# Publishing Edition Pipeline Report

- Stage: `PUBLISHING_EDITION_PREPARATION`
- Runs before reader publication prep, audiobook chunking, highlight-sync generation, and SEO/static snapshot generation.
- Raw/source text remains preserved in the original chapter artifacts.
- Reader-facing Dracula content is served from the publishing edition artifacts.
- Audiobook-facing text should derive from the same publishing edition before future generation.

- Book slug: `dracula`
- Raw source path: `data/controlled_publications/dracula/chapters`
- Raw source hash: `bd5f3edbdd2564ac76c6c99fa12ccd60da0cc20519a49dfbcd8d44135e85e7c9`
- Publishing edition output: `data/controlled_publications/dracula/publishing_edition`
- Publishing edition hash: `19010ff811ddcb332f0817ab75ab2a23e6c6255fc1e81a3f927bf6ce5b2c42d8`
- Chapters prepared: `27` of `27`
- Deterministic transformations applied: `13419`
- Owner-review ambiguous items: `0`
- Remaining known artifact hits: `0`
- Reader GO LIVE status: `GO_LIVE_READER_READY`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Audiobook production: `PRODUCTION_BLOCKED`
- Payment behavior changed: `false`

## Visual QA Artifacts

- `output/visual-review/publishing-edition-dracula/reader-chapter-001-desktop-1440.png`
- `output/visual-review/publishing-edition-dracula/reader-chapter-001-mobile-390.png`
- `output/visual-review/publishing-edition-dracula/reader-scene-break-desktop-1440.png`
- `output/visual-review/publishing-edition-dracula/book-dracula-index-desktop-1440.png`
