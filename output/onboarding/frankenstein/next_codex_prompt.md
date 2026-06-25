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
Current licensed provider internal-eval status: `ELIGIBLE_INTERNAL_EVAL`.
Current licensed provider production status: `PRODUCTION_BLOCKED`.

Current licensed provider blockers:
- No provider blocker recorded.

Current Dracula Chapter 1 internal audiobook state:
- Full Chapter 1 internal audio import: `INTERNAL_FULL_CHAPTER_ONLY`.
- Imported chunks: `27`.
- Owner listening QA status: `READY_FOR_INTERNAL_PLAYER_TEST`.
- Owner listening score: `9.4/10`.
- Internal player test status: `READY_TO_PREPARE_INTERNAL_PLAYER_TEST`.
- Highlighted-text sync status: `HOLD_SYNC_QA_REQUIRED`.
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Production status: `PRODUCTION_BLOCKED`.
- Next action: prepare internal-only highlighted-text player test using existing internal manifests and audio hashes; do not expose audio publicly.

Required next checks:
- Attach complete source-rights evidence.
- Add owner-approved cover provenance.
- Review TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md and TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md.
- Review TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md and TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md.
- Complete KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md and KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md before any Kokoro af_heart eligibility change.
- Review TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md and TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md.
- Complete ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md and ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md before any ElevenLabs eligibility change.
- Complete internal/legal/elevenlabs/creator-membership-internal-eval-evidence.md before any ElevenLabs internal sample import is approved.
- Complete TTS model license, voice, commercial-use, speaker-rights, and owner approval evidence before real internal generation.
- Review AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md for the automated dry-run narration, chunking, cost, provider, sync, and public-release gate evidence.
- Do not generate an audio sample yet; `kokoro` remains `HOLD_VOICE_RIGHTS`.
- Collect owner/legal-reviewed selected voice or speaker-rights evidence, including provenance, commercial internal-eval permission, synthetic/non-human or consent status, and real-person voice-cloning risk review.
- Future separate task may prepare an internal-only 2-3 minute Dracula Chapter 1 sample with `elevenlabs` after owner/legal/provider evidence remains attached and public audio remains blocked.
- Keep provider sample generation local/internal and outside `frontend/public` and `frontend/build`.
- Review the internal highlighted-text sync manifest before any audio release consideration.
- If owner/legal approve ElevenLabs internal evaluation, manually generate only the Dracula 2-3 minute sample in the ElevenLabs UI and import it with npm run elevenlabs:sample-import.
- Keep public audio blocked.
- Run the publication, audio, SEO, social, payment-smoke, regression, and frontend build gates.
