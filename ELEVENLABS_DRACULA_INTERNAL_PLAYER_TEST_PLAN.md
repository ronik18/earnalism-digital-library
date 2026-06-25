# ElevenLabs Dracula Internal Player Test Plan

## Purpose

Prepare an internal-only highlighted-text player test for the full Dracula Chapter 1 audiobook using the merged internal audio and sync manifests.

## Current Internal Evidence

- Book: `dracula`
- Language: `en`
- Chapter: `1`
- Provider: `ElevenLabs`
- Voice: `Rachel`
- Voice ID: `21m00Tcm4TlvDq8ikWAM`
- Imported chunks: `27`
- Full chapter audio hash: `5cea977f3fcffca744f9fa71a8da249943462a9096580d6522b4d80c509bc2c0`
- Audio status: `INTERNAL_FULL_CHAPTER_ONLY`
- Listening QA status: `READY_FOR_INTERNAL_PLAYER_TEST`
- Owner listening score: `9.4/10`
- Sync status: `HOLD_SYNC_QA_REQUIRED`
- Player test status: `READY_FOR_INTERNAL_PLAYER_TEST`

## Test Inputs

- Internal player test manifest: `internal/audiobook_lab/dracula/en/chapter-1/internal_player_test_manifest.json`
- Internal player QA form: `internal/audiobook_lab/dracula/en/chapter-1/internal_player_test_qa_form.md`
- Imported audio manifest: `internal/audiobook_lab/dracula/en/chapter-1/imported_audio_manifest.json`
- Full chapter audio manifest: `internal/audiobook_lab/dracula/en/chapter-1/full_chapter_audio_manifest.json`
- Sync manifest: `internal/audiobook_lab/dracula/en/chapter-1/sync_manifest.json`

## Internal Test Procedure

1. Load the internal-only manifest and sync manifest in a local or otherwise non-public player environment.
2. Verify that all 27 chunks appear in order from `c001` through `c027`.
3. Confirm that playback starts, pauses, resumes, and moves across chunk boundaries without public-serving audio.
4. Review highlighted-text timing against the current sync manifest.
5. Record player QA results in `internal_player_test_qa_form.md`.
6. Keep `sync_status` as `HOLD_SYNC_QA_REQUIRED` until highlighted-text sync QA is completed.

## Guardrails

- Internal test only.
- No public release.
- No production approval.
- No public audio URL.
- No Listen Now CTA.
- No AudioObject metadata.
- No audio files under `frontend/public`.
- No audio files under `frontend/build`.
- Audio binaries are gitignored and are not committed.

## Next Action

Run internal highlighted-text player QA and fill `internal_player_test_qa_form.md`. Public release remains blocked until player QA, sync QA, accessibility QA, owner review, and release gates pass.
