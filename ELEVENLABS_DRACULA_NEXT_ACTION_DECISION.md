# ElevenLabs Dracula Next Action Decision

Decision: `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY`

The first ElevenLabs Dracula sample import succeeded as an internal-only artifact, and human listening QA recorded `9.5/10` for every required dimension. The sample is ready only for the full Chapter 1 internal-only manual generation/import workflow.

## Current Evidence

- Imported audio manifest: `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-sample/imported_audio_manifest.json`
- Sync manifest: `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-sample/sync_manifest.json`
- Audio status: `INTERNAL_SAMPLE_ONLY`
- Sync status: `HOLD_SYNC_QA_REQUIRED`
- Public audio allowed: `false`
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production status: `PRODUCTION_BLOCKED`
- production_approved: false
- listen_now_cta_allowed: false
- audio_object_metadata_allowed: false
- full_book_generation_allowed: false
- Audio hash: `fad97e83e4590adea2cd2b597ca0625765b1b04c9a99a3abd4ea820e0138309a`
- Sentence sync items: `19`
- Timed sync items: `0`

## Next Action

Recommended next action: `PREPARE_FULL_CHAPTER_INTERNAL_ONLY_CHUNKED_GENERATION`

Use `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full/` to manually generate Chapter 1 in chunks through the ElevenLabs UI/Studio only. Do not call the ElevenLabs API from this repository and do not generate audio automatically.

Full Chapter 1 generation is approved only as `INTERNAL_FULL_CHAPTER_ONLY`. Public audio remains blocked.

## Conditional Decision Path

| Condition | Next Decision | Required Notes |
| --- | --- | --- |
| No human listening scores are filled | `HOLD_HUMAN_LISTENING_QA_REQUIRED` | No full Chapter 1 generation recommendation. |
| Overall human score below `9.5` | `REGENERATE_SMALL_CHUNK` | Exact issue notes must identify the sentence range, problem type, and desired correction. |
| Overall human score `9.5` or above | `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY` | Public audio remains blocked and production remains blocked. |

Current path: `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY`.

## Release Guardrails

- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Imported audio remains internal only.
- Sync remains `HOLD_SYNC_QA_REQUIRED`.
- Production remains `PRODUCTION_BLOCKED`.
- No audio may be moved to `frontend/public` or `frontend/build`.
- No Listen Now CTA may be added.
- No AudioObject metadata may be added.
- No public player or public audio URL may be exposed.
