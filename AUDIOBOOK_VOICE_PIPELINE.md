# Phase 7 Audiobook Voice Pipeline

Phase 7 adds a deterministic dry-run audiobook and voice pipeline for Bengali, English, and Hindi. It is designed to prepare narration scripts, provider plans, mastering metadata, QA gates, and reports before any expensive or production audio work happens.

## Voice Identity

The target voice identity is a refined female literary narrator: warm, intelligent, calm, expressive, punctuation-aware, emotionally restrained, and suitable for Bengali, English, and Hindi.

## Dry-Run Safety

The Phase 7 CLI defaults to dry-run and rejects `--commit`, `--publish`, and `--write`.

No external TTS, STT, FFmpeg, OCR, LLM, image, or paid API calls are executed by this phase. Provider and FFmpeg behavior is represented as deterministic hook metadata only.

The core library also blocks non-dry-run use. Any direct call with `dry_run=False` returns `BLOCKED_NON_DRY_RUN` with the reason `Phase 7 audiobook voice pipeline is dry-run only.`

## Upstream Gates

Audiobook planning requires evidence from earlier phases before narration chunks or planned audio assets are produced:

- Phase 2 rights: `rights_tier=A`, `verification_status=approved`, and no `blocked_reason`
- Phase 3 demand: `action_status=READY_FOR_GENERATION`
- Phase 4 ingestion: `ingestion_status=INGESTED` or `CLEANED`
- Phase 5 edition: `edition_generation_status=READY_FOR_REVIEW`, `PARTIAL_DRY_RUN`, or `QA_PASSED`
- Traceability: `source_hash`, `content_hash`, and `provenance_hash`
- Full local text: `source_text`

Blocking statuses:

- `BLOCKED_NON_DRY_RUN`
- `BLOCKED_RIGHTS`
- `BLOCKED_RIGHTS_REVIEW_REQUIRED`
- `REGION_GATED_REVIEW`
- `BLOCKED_PRIORITY_GATE`
- `BLOCKED_INGESTION`
- `BLOCKED_EDITION_GATE`
- `BLOCKED_TRACEABILITY`
- `BLOCKED_SOURCE_TEXT`

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

Provider hooks are metadata-only in Phase 7. They do not call TTS APIs, local commands, subprocesses, or vendor SDKs.

## FFmpeg Mastering Plan

The mastering plan records command metadata for:

- loudness normalization
- silence trimming
- MP3 output
- AAC output
- OGG output
- waveform preview

Phase 7 does not execute FFmpeg or create audio binaries.

The FFmpeg section records command metadata only. Pandoc, Calibre, FFmpeg, and audio tooling are not invoked by this phase.

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

The STT comparison is a hook placeholder in Phase 7. A later phase must run real transcript comparison, file inspection, and human listening review before production narration rollout.

## Publishing Gates

Phase 7 does not publish audio. The core gate is dry-run only:

- dry-run returns `DRY_RUN_ONLY`
- non-dry-run returns `BLOCKED_NON_DRY_RUN`
- unsafe or unapproved upstream evidence blocks planning before any audio assets are planned
- all planned assets are `publishable=false`

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
