# Book Factory Audiobook Stage Report

- Book slug: `dracula`
- Mode: `dry-run`
- Provider: `elevenlabs`
- Scope: `selected_chapters`

| Stage | Status | Blockers |
| --- | --- | --- |
| `AUDIOBOOK_CHUNK_HASHING` | `PASS` | none |
| `AUDIOBOOK_CACHE_LOOKUP` | `PASS` | none |
| `AUDIOBOOK_TTS_GENERATION` | `DRY_RUN_READY` | none |
| `AUDIOBOOK_ALIGNMENT_IMPORT` | `HOLD_SYNC_QA_REQUIRED` | none |
| `AUDIOBOOK_SYNC_MANIFEST` | `HOLD_SYNC_QA_REQUIRED` | none |
| `AUDIOBOOK_INTERNAL_PLAYER_PREP` | `HOLD_INTERNAL_PLAYER_PREP` | none |
| `AUDIOBOOK_QA_GATE` | `HOLD_SYNC_QA` | owner listening QA and sync QA are required before public release. |

- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production: `PRODUCTION_BLOCKED`
- Listen Now CTA allowed: `false`
- AudioObject metadata allowed: `false`
