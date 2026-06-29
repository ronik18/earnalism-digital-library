# ElevenLabs Dracula Full Chapter Internal Report

## API Automation Status

- Mode: `dry-run`
- Endpoint: `POST /v1/text-to-speech/:voice_id/with-timestamps`
- Voice: `Rachel / 21m00Tcm4TlvDq8ikWAM`
- Model: `eleven_multilingual_v2`
- Output format: `mp3_44100_192`
- Chunk selector: `all`
- Chunks considered: `27`
- Total characters: `30651`
- Concurrency: `1`
- Max retries: `2`
- Retry count: `0`
- Resume failed mode: `false`
- Elapsed seconds: `0.022`
- Cache manifest: `internal/audiobook_lab/cache/elevenlabs/cache_manifest.json`
- Cache hits: `0`
- Cache misses: `27`
- Cache stale entries: `0`
- Preflight report: `internal/audiobook_lab/dracula/en/chapter-1/generation_preflight_report.json`
- API key present: `false`
- Expected request fields: `language_code, model_id, next_text, text, voice_settings`
- Unsupported fields omitted: `none`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production: `PRODUCTION_BLOCKED`
- Listen Now CTA allowed: `false`
- AudioObject metadata allowed: `false`
- Full-book generation allowed: `false`
