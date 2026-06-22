# Audiobook Generation Sync Pipeline Report

- Book slug: `dracula`
- Chapter: `1`
- Language: `en`
- Model candidate: `kokoro`
- Mode: `dry-run`
- Status: `DRY_RUN_COMPLETE`
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Output directory: `internal/audiobook_lab/dracula/en/1`
- Sync manifest: `internal/audiobook_lab/dracula/en/1/sync_manifest.json`

## Blockers

- `MODEL_LICENSE_HOLD` (HIGH): Model license status is not approved: HOLD_LICENSE_REVIEW.
- `SOURCE_RIGHTS_EVIDENCE_MISSING` (HIGH): source_rights_evidence_missing is required before internal generation or release.
- `DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING` (HIGH): derivative_audiobook_rights_missing is required before internal generation or release.
- `VOICE_RIGHTS_MISSING` (HIGH): voice_rights_missing is required before internal generation or release.
- `TEXT_FIDELITY_EVIDENCE_MISSING` (HIGH): text_fidelity_evidence_missing is required before internal generation or release.
- `HUMAN_LISTENING_QA_MISSING` (HIGH): human_listening_qa_missing is required before internal generation or release.
- `ACCESSIBILITY_LISTENING_QA_MISSING` (HIGH): accessibility_listening_qa_missing is required before internal generation or release.

## Safety

- No public audio was generated.
- No audio file was written to `frontend/public` or `frontend/build`.
- No Listen Now CTA or AudioObject metadata was added.
- No book was published.
- No payment behavior was changed.
