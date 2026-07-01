# Fast Dracula Audiobook Production Plan

## Status

- Scope: internal audiobook production preflight for editorial QA.
- Public audio remains blocked.
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook public release remains blocked.
- Multiple controlled reader-only books may now be live. Dracula remains the only public audiobook/audio-enabled release candidate.
- No non-Dracula, draft, or pipeline title may expose public audio.
- No Listen Now CTA, AudioObject metadata, public audiobook URLs, payment changes, pricing changes, deployment, or new book publication.

## Source

- Exact source text path: `data/controlled_publications/dracula/chapters/chapter-001.json` through `chapter-027.json`.
- Confirmed chapter count: `27`.
- Total character count: `838684`.
- Total normalized character count: `838684`.
- Source checksum: `462e10ba17074aa50835ac578503a5c6525cbf6553aa090ea6bf827c8aab0c63`.
- Normalized checksum: `462e10ba17074aa50835ac578503a5c6525cbf6553aa090ea6bf827c8aab0c63`.

## Cost

- Flash cost estimate: `838684 / 1000 * 0.05 = $41.93`.
- Premium cost estimate: `838684 / 1000 * 0.10 = $83.87`.
- Budget cap present: `false`.
- Paid generation allowed now: `false`.

## Provider Defaults

- Default voice alias: `elevenlabs:rachel`.
- Default voice ID: `21m00Tcm4TlvDq8ikWAM`.
- First-pass model ID: `eleven_flash_v2_5`.
- Premium model ID for comparison/corrections only: `eleven_multilingual_v2`.
- Output format: `mp3_44100_128`.

## Chunking Strategy

- Chunk by chapter, paragraph, and sentence boundaries with target `3600` characters and max `4500` characters.
- Do not split sentences unless a single sentence exceeds the max target; oversize sentences stay intact and are flagged.
- Preserve epistolary headings, letters, diary entries, telegrams, and section breaks as source text.
- Do not rewrite Dracula text. Normalization is limited to line-ending and whitespace consistency for checksums.
- Total planned chunks: `240`.

## Concurrency, Retry, And Cache

- Concurrency: `3` workers max for paid generation.
- Retry transient provider failures with exponential backoff.
- Never regenerate a chunk whose source checksum, model, voice, output format, and audio checksum already match.
- Reuse existing Chapter 1 cache only when source checksums match; otherwise mark it as checksum mismatch.

## QA Checklist

- Confirm exactly 27 chapters.
- Confirm all chunks are generated or explicitly failed.
- Confirm no missing chunks, zero-byte files, or missing checksums.
- Confirm durations are plausible.
- Confirm no public URLs, no frontend/public or frontend/build audio, no Listen Now CTA, and no AudioObject metadata.
- Confirm non-Dracula reader-only books expose no audio flags, public audio manifests, audio player UI, or waveform UI.
- Confirm public audio remains blocked and payment behavior is unchanged.

## Human Review Checklist

- First 60 seconds of each chapter.
- One middle sample of each chapter.
- Final 60 seconds of each chapter.
- Mark bad chunks/chapters in `REGENERATION_QUEUE.json`.

## Public-Release Blockers

- Public audio remains blocked.
- Human listening QA is required.
- Chunk-level sync is not word-level sync and must not be marketed as word highlighting.
- Accessibility, legal/commercial, and owner release approval are still required.
