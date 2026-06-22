# Next English Book Onboarding Prompt

Use `onboarding/books/frankenstein.yml` as the source config and keep the onboarding dry-run until every HOLD blocker is cleared.

Current selected TTS model: `kokoro`.
Current selected TTS decision: `HOLD_VOICE_RIGHTS`.
Current selected TTS internal-eval status: `HOLD_VOICE_RIGHTS`.
Current model generation status: `HOLD_VOICE_RIGHTS`.

Required next checks:
- Attach complete source-rights evidence.
- Add owner-approved cover provenance.
- Review TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md and TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md.
- Review TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md and TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md.
- Complete TTS model license, voice, commercial-use, speaker-rights, and owner approval evidence before real internal generation.
- Do not generate an audio sample yet; `kokoro` remains `HOLD_VOICE_RIGHTS`.
- Collect owner/legal-reviewed selected voice or speaker-rights evidence, including provenance, commercial internal-eval permission, synthetic/non-human or consent status, and real-person voice-cloning risk review.
- Review the internal highlighted-text sync manifest before any audio release consideration.
- Keep public audio blocked.
- Run the publication, audio, SEO, social, payment-smoke, regression, and frontend build gates.
