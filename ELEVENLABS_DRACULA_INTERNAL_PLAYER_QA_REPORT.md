# ElevenLabs Dracula Internal Player QA Report

## Current Status

- Player QA status: `HOLD_PLAYER_QA_NOT_STARTED`
- Default player QA decision: `HOLD`
- Internal player test status: `READY_FOR_INTERNAL_PLAYER_TEST`
- Listening QA status: `READY_FOR_INTERNAL_PLAYER_TEST`
- Sync status: `HOLD_SYNC_QA_REQUIRED`
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production status: `PRODUCTION_BLOCKED`

## Imported Chapter Summary

- Book: `dracula`
- Language: `en`
- Chapter: `1`
- Provider: `ElevenLabs`
- Voice: `Rachel`
- Voice ID: `21m00Tcm4TlvDq8ikWAM`
- Imported chunks: `27`
- Full chapter audio hash: `5cea977f3fcffca744f9fa71a8da249943462a9096580d6522b4d80c509bc2c0`
- Audio status: `INTERNAL_FULL_CHAPTER_ONLY`
- Owner listening QA score: `9.4/10`
- Owner listening decision: `READY_FOR_INTERNAL_PLAYER_TEST`

## Player QA Packet

- Internal player test manifest: `internal/audiobook_lab/dracula/en/chapter-1/internal_player_test_manifest.json`
- Internal player QA form: `internal/audiobook_lab/dracula/en/chapter-1/internal_player_test_qa_form.md`
- Sync manifest: `internal/audiobook_lab/dracula/en/chapter-1/sync_manifest.json`

## Remaining Blockers

- Internal player QA has not been completed.
- Highlighted-text sync QA remains required.
- Accessibility player QA remains required.
- Public release review is not approved.
- Production approval is not granted.

## Public Release Guardrails

- Public audio allowed: `false`
- Listen Now CTA allowed: `false`
- AudioObject metadata allowed: `false`
- Public audio URL allowed: `false`
- Production approved: `false`
- Audio binaries committed: `false`

No public release, production approval, public audio URL, Listen Now CTA, or AudioObject metadata is approved by this report.

## Next Action

Run internal-only highlighted-text player QA using the internal manifests and fill the QA form. Do not expose audio publicly.
