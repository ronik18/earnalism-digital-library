# Archived Audio Action Plan

Status: `HISTORICAL_NON_AUTHORITATIVE`

This file is retained only as a historical note from an earlier audio automation pass. It is not a production deployment plan and must not be used to publish, upload, sync, or enable audiobook assets.

The authoritative launch posture is now:

- No audiobook is production-ready unless linked book rights are approved.
- No audiobook is production-ready unless listening QA, timestamp sync QA, duration checks, and storage/provider routing checks pass.
- Public audiobook promotion remains blocked when rights or QA are unknown.
- Cloudinary/B2 upload or live flag sync must never run from this file.

## Required Guards For Non-Dry Audio Actions

Any non-dry audio upload, provider call, or production sync must require all of these environment variables:

- `EARNALISM_ALLOW_AUDIO_UPLOAD=true`
- `EARNALISM_ALLOW_PROVIDER_CALLS=true`
- `EARNALISM_CONFIRM_PRODUCTION_AUDIO=true`

Use the current guarded scripts and launch readiness reports instead:

- `npm run launch:audio-audit`
- `AUDIOBOOK_READINESS_REPORT.md`
- `scripts/open_source_audiobook_onboarding.py`

No deploy, public publishing, provider call, TTS/STT call, or production content mutation is authorized by this archived file.
