# English Book Publication Gate Report

- Book: Frankenstein
- Slug: `frankenstein`
- Generated: 2026-06-22T06:05:30+00:00
- Mode: `dry-run`
- Dry run: `true`
- Gate status: `HOLD_SOURCE_RIGHTS_QA_REQUIRED`
- GO/HOLD: `HOLD`
- Public publish allowed: `false`
- Start Reading CTA allowed: `false`

## Blockers

- cover_asset_provenance_gate: owner-designed cover provenance is required before public use.
- cover_asset_provenance_gate: cover provenance note is required.
- cover_asset_provenance_gate: owner cover approval is required.
- audiobook_planning_packet: public audiobook release is blocked by default.
- audiobook_planning_packet: model/voice license evidence is missing.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: selected model `kokoro` is not eligible for real internal generation: HOLD_LICENSE_REVIEW.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: voice_license is missing or requires review.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: commercial_use_status is missing or requires review.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: real_person_voice_risk is missing or requires review.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: commercial-use evidence is not approved.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: voice rights evidence is missing or varies by voice.
- TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW: owner approval is required before production use.
- audiobook_sync_dry_run_stage: sync release evidence remains HOLD; public audio cannot be released.
- narration_qa_gate: human narration QA is missing or not approved.
- narration_qa_gate: accessibility listening QA is missing or not approved.
- audiobook_legal_accessibility_compliance_gate: public audio remains PUBLIC_AUDIO_RELEASE_BLOCKED until separate owner/legal/accessibility release approval.
- audiobook_legal_accessibility_compliance_gate: rollback_approval_status is required before audiobook release.
- audiobook_legal_accessibility_compliance_gate: owner_legal_approval_status is required before audiobook release.
- audiobook_legal_accessibility_compliance_gate: refund_support_readiness is required before audiobook release.
- payment_publication_guardrails: owner publication approval is required.
