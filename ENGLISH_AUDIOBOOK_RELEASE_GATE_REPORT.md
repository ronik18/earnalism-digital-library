# English Audiobook Release Gate Report

- Book: Frankenstein
- Slug: `frankenstein`
- Generated: 2026-06-22T07:39:33+00:00
- Mode: `dry-run`
- Dry run: `true`
- Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Sync status: `HOLD_SYNC_QA_REQUIRED`
- Selected model: `kokoro`
- Selected model decision: `HOLD_LICENSE_REVIEW`
- Model generation: `HOLD_LICENSE_REVIEW`
- Public audio publish allowed: `false`
- Public listening CTA: `false`
- Public audio JSON-LD metadata: `false`

## Blockers

- public audiobook release is blocked by default.
- model/voice license evidence is missing.
- selected model `kokoro` is not eligible for real internal generation: HOLD_LICENSE_REVIEW.
- voice_license is missing or requires review.
- voice rights evidence is missing or varies by voice.
- owner approval is required before production use.
- sync release evidence remains HOLD; public audio cannot be released.
- human narration QA is missing or not approved.
- accessibility listening QA is missing or not approved.
- public audio remains PUBLIC_AUDIO_RELEASE_BLOCKED until separate owner/legal/accessibility release approval.
- rollback_approval_status is required before audiobook release.
- owner_legal_approval_status is required before audiobook release.
- refund_support_readiness is required before audiobook release.
