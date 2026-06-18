# Phase 7 Audiobook Voice Pipeline

Phase 7 adds a deterministic dry-run audiobook and voice pipeline for Bengali, English, and Hindi. It is designed to prepare narration scripts, provider plans, mastering metadata, QA gates, and reports before any expensive or production audio work happens.

## Voice Identity

The target voice identity is a refined female literary narrator: warm, intelligent, calm, expressive, punctuation-aware, emotionally restrained, and suitable for Bengali, English, and Hindi.

## Dry-Run Safety

The Phase 7 CLI defaults to dry-run and rejects `--commit`, `--publish`, and `--write`.

No external TTS, STT, FFmpeg, OCR, LLM, image, or paid API calls are executed by this phase. Provider and FFmpeg behavior is represented as deterministic hook metadata only.

## Narration Script Processor

The processor supports:

- punctuation-aware chunking
- chapter heading handling
- dialogue handling
- poetry line-break handling
- Bengali, Hindi, and English language detection
- pronunciation dictionary replacements

Language detection is deterministic and based on Unicode script ranges:

- Bengali: `bn`
- Hindi/Devanagari: `hi`
- Latin/English: `en`

## Audio Generation Modes

Supported modes:

- `preview_30s`
- `preview_90s`
- `preview_3m`
- `chapter_audio`
- `full_audiobook_playlist`

Preview modes cap narration chunks and character counts so product, editorial, and QA teams can evaluate voice quality before generating long-form audio.

## Provider Abstraction

Supported provider hooks:

- `openai_tts`
- `ai4bharat_indic_tts`
- `piper_local_tts`
- `manual_audio_upload`

The provider abstraction does not hard-code credentials or lock the pipeline to one vendor. Credentials are detected through environment variables only:

- `OPENAI_API_KEY`
- `AI4BHARAT_TTS_ENDPOINT`
- `INDIC_TTS_COMMAND`
- `PIPER_MODEL_PATH`
- `PIPER_TTS_COMMAND`

When credentials are absent, provider plans remain dry-run only.

## FFmpeg Mastering Plan

The mastering plan records command metadata for:

- loudness normalization
- silence trimming
- MP3 output
- AAC output
- OGG output
- waveform preview

Phase 7 does not execute FFmpeg or create audio binaries.

## Audio QA

QA hooks cover:

- STT transcript comparison
- word error rate
- missing paragraph detection
- repeated line detection
- clipping detection
- long silence detection
- file size checks

No audio can be considered publishable unless QA status is `PASS`.

## Publishing Gates

Phase 7 does not publish audio. The core gate still models publish safety:

- dry-run returns `DRY_RUN_ONLY`
- non-dry-run without a linked approved book returns `BLOCKED_BOOK_APPROVAL`
- unsafe or unapproved rights return `BLOCKED_RIGHTS`
- unconfigured providers return `BLOCKED_PROVIDER`
- missing/failing QA returns `BLOCKED_QA`
- only linked approved books with approved Tier A rights, configured provider/manual upload, and QA pass can reach `PASS`

## Reports

Run:

```bash
npm run audio:voice
```

Outputs:

- `output/audiobook_voice/audiobook_voice_report.json`
- `output/audiobook_voice/audiobook_voice_report.csv`
- `output/audiobook_voice/audiobook_voice_report.md`

Reports are preview-only by default. Full narration chunk text is included only with:

```bash
python3 scripts/audiobook_voice_pipeline.py --sample --include-text
```

## Limitations

- This phase does not synthesize audio.
- This phase does not upload or publish audio.
- This phase does not run FFmpeg.
- This phase does not run STT transcript comparison.
- Human listening review is still required before production narration rollout.
