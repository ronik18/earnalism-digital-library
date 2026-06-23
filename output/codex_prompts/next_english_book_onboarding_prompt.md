# Next English Book Onboarding Prompt

Use `onboarding/books/frankenstein.yml` as the source config and keep the onboarding dry-run until every HOLD blocker is cleared.

Current selected TTS model: `kokoro`.
Current selected Kokoro voice: `af_heart`.
Current selected TTS decision: `HOLD_VOICE_RIGHTS`.
Current selected TTS internal-eval status: `HOLD_VOICE_RIGHTS`.
Current selected voice internal-eval status: `HOLD_VOICE_RIGHTS`.
Current model generation status: `HOLD_VOICE_RIGHTS`.

Current selected licensed provider: `elevenlabs`.
Current selected provider voice: `21m00Tcm4TlvDq8ikWAM`.
Current selected provider voice type: `platform_voice`.
Current licensed provider internal-eval status: `HOLD_PROVIDER_REVIEW`.
Current licensed provider production status: `PRODUCTION_BLOCKED`.

Current licensed provider blockers:
- selected provider `elevenlabs` is not eligible for internal evaluation: HOLD_PROVIDER_REVIEW.
- paid provider plan evidence is required before internal evaluation.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected voice attribution requirements require review.
- selected voice restrictions require review.

Required next checks:
- Attach complete source-rights evidence.
- Add owner-approved cover provenance.
- Review TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md and TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md.
- Review TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md and TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md.
- Complete KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md and KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md before any Kokoro af_heart eligibility change.
- Review TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md and TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md.
- Complete ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md and ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md before any ElevenLabs eligibility change.
- Complete TTS model license, voice, commercial-use, speaker-rights, and owner approval evidence before real internal generation.
- Do not generate an audio sample yet; `kokoro` remains `HOLD_VOICE_RIGHTS`.
- Collect owner/legal-reviewed selected voice or speaker-rights evidence, including provenance, commercial internal-eval permission, synthetic/non-human or consent status, and real-person voice-cloning risk review.
- Do not generate a provider audio sample yet; `elevenlabs` remains `HOLD_PROVIDER_REVIEW`.
- Complete ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md and ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md before any provider eligibility change.
- Review the internal highlighted-text sync manifest before any audio release consideration.
- Keep public audio blocked.
- Run the publication, audio, SEO, social, payment-smoke, regression, and frontend build gates.
