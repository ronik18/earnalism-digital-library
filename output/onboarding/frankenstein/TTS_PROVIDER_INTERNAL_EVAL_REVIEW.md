# TTS Provider Internal-Eval Review

This local review is part of the English onboarding orchestrator. It does not call provider APIs, generate audio, or approve production audio.

- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production approval status: `PRODUCTION_BLOCKED` for every provider
- Internal-evaluation eligible providers: `0`
- Real audio generated: `false`
- Paid provider calls: `false`

| Provider | Strategy | Standalone output | Voice rights | Internal eval | Production | Primary blocker |
| --- | --- | --- | --- | --- | --- | --- |
| ElevenLabs | REVIEW_ONLY | ALLOWED | HOLD_REVIEW | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review.; selected voice attribution requirements require review.; selected voice restrictions require review. |
| OpenAI API TTS and Realtime Voices | REVIEW_ONLY | HOLD_REVIEW | HOLD_REVIEW | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | selected_voice_type is missing or requires review.; standalone audio distribution evidence is not approved.; attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review. |
| Google Cloud Text-to-Speech | REVIEW_ONLY | HOLD_REVIEW | HOLD_REVIEW | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | selected_voice_type is missing or requires review.; standalone audio distribution evidence is not approved.; attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review. |
| Azure AI Speech | REVIEW_ONLY | HOLD_REVIEW | HOLD_REVIEW | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | selected_voice_type is missing or requires review.; standalone audio distribution evidence is not approved.; attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review. |
| Amazon Polly | REVIEW_ONLY | HOLD_REVIEW | HOLD_REVIEW | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | selected_voice_type is missing or requires review.; standalone audio distribution evidence is not approved.; attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review. |
| Owner-Controlled Narrator Voice | STRATEGIC_RECOMMENDED_PATH | HOLD_REVIEW | OWNER_REVIEW_REQUIRED | HOLD_PROVIDER_REVIEW | PRODUCTION_BLOCKED | selected_voice_type is missing or requires review.; standalone audio distribution evidence is not approved.; beta feature exclusion evidence is missing or requires review.; selected provider voice is not selected. |

## Provider Evidence

### ElevenLabs

- Provider ID: `elevenlabs`
- Official terms: [terms](https://elevenlabs.io/terms)
- Commercial-use evidence: [commercial evidence](https://help.elevenlabs.io/hc/en-us/articles/13313564663441-Can-I-publish-the-content-I-generate-on-the-platform)
- Voice license evidence: [voice evidence](https://elevenlabs.io/terms)
- Paid plan required: `True`
- Paid plan evidence status: `HOLD_REVIEW`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: General-availability provider use only; beta, experimental, or preview voice features are excluded unless separately approved.
- Standalone audio distribution: `ALLOWED`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `HOLD_REVIEW`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: Account, privacy, voice-library, and data-retention settings require owner/legal review before internal generation.
- Voice rights status: `HOLD_REVIEW`
- Selected voice ID: `21m00Tcm4TlvDq8ikWAM`
- Selected voice display name: Rachel
- Selected voice type: `platform_voice`
- Selected voice license evidence: https://elevenlabs.io/terms
- Selected voice rights summary: Proposed ElevenLabs platform voice for owner/legal review only; internal evaluation is blocked until selected voice rights, plan, attribution, restrictions, and account terms are manually approved.
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- paid plan evidence status is missing or requires review.
- paid plan evidence is required before using this provider for internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

### OpenAI API TTS and Realtime Voices

- Provider ID: `openai-api-tts-realtime`
- Official terms: [terms](https://openai.com/policies/service-terms)
- Commercial-use evidence: [commercial evidence](https://openai.com/policies/terms-of-use)
- Voice license evidence: [voice evidence](https://platform.openai.com/docs/guides/text-to-speech)
- Paid plan required: `True`
- Paid plan evidence status: `HOLD_REVIEW`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: Beta/realtime/preview features excluded unless separately approved.
- Standalone audio distribution: `HOLD_REVIEW`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `HOLD_REVIEW`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: API terms, voice-output restrictions, retention, and commercial audiobook distribution require owner/legal review.
- Voice rights status: `HOLD_REVIEW`
- Selected voice ID: `OWNER_SELECTION_REQUIRED`
- Selected voice display name: OWNER_SELECTION_REQUIRED
- Selected voice type: `unknown`
- Selected voice license evidence: OWNER_SELECTION_REQUIRED
- Selected voice rights summary: HOLD_REVIEW
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- selected_voice_type is missing or requires review.
- standalone audio distribution evidence is not approved.
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected provider voice is not selected.
- selected voice type is unknown.
- selected voice must be a provider/platform voice or generated voice before internal evaluation.
- selected provider voice license evidence is missing.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- paid plan evidence status is missing or requires review.
- paid plan evidence is required before using this provider for internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

### Google Cloud Text-to-Speech

- Provider ID: `google-cloud-text-to-speech`
- Official terms: [terms](https://cloud.google.com/terms)
- Commercial-use evidence: [commercial evidence](https://cloud.google.com/text-to-speech/docs/create-audio)
- Voice license evidence: [voice evidence](https://cloud.google.com/text-to-speech/docs/voices)
- Paid plan required: `True`
- Paid plan evidence status: `HOLD_REVIEW`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: Beta/preview voice features excluded unless separately approved.
- Standalone audio distribution: `HOLD_REVIEW`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `HOLD_REVIEW`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: Cloud account, data processing, voice selection, and output distribution rights require owner/legal review.
- Voice rights status: `HOLD_REVIEW`
- Selected voice ID: `OWNER_SELECTION_REQUIRED`
- Selected voice display name: OWNER_SELECTION_REQUIRED
- Selected voice type: `unknown`
- Selected voice license evidence: OWNER_SELECTION_REQUIRED
- Selected voice rights summary: HOLD_REVIEW
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- selected_voice_type is missing or requires review.
- standalone audio distribution evidence is not approved.
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected provider voice is not selected.
- selected voice type is unknown.
- selected voice must be a provider/platform voice or generated voice before internal evaluation.
- selected provider voice license evidence is missing.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- paid plan evidence status is missing or requires review.
- paid plan evidence is required before using this provider for internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

### Azure AI Speech

- Provider ID: `azure-ai-speech`
- Official terms: [terms](https://azure.microsoft.com/en-us/support/legal/)
- Commercial-use evidence: [commercial evidence](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- Voice license evidence: [voice evidence](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- Paid plan required: `True`
- Paid plan evidence status: `HOLD_REVIEW`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: Beta/preview voice features excluded unless separately approved.
- Standalone audio distribution: `HOLD_REVIEW`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `HOLD_REVIEW`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: Azure account, voice terms, data retention, and output distribution rights require owner/legal review.
- Voice rights status: `HOLD_REVIEW`
- Selected voice ID: `OWNER_SELECTION_REQUIRED`
- Selected voice display name: OWNER_SELECTION_REQUIRED
- Selected voice type: `unknown`
- Selected voice license evidence: OWNER_SELECTION_REQUIRED
- Selected voice rights summary: HOLD_REVIEW
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- selected_voice_type is missing or requires review.
- standalone audio distribution evidence is not approved.
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected provider voice is not selected.
- selected voice type is unknown.
- selected voice must be a provider/platform voice or generated voice before internal evaluation.
- selected provider voice license evidence is missing.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- paid plan evidence status is missing or requires review.
- paid plan evidence is required before using this provider for internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

### Amazon Polly

- Provider ID: `amazon-polly`
- Official terms: [terms](https://aws.amazon.com/service-terms/)
- Commercial-use evidence: [commercial evidence](https://aws.amazon.com/polly/)
- Voice license evidence: [voice evidence](https://docs.aws.amazon.com/polly/latest/dg/voicelist.html)
- Paid plan required: `True`
- Paid plan evidence status: `HOLD_REVIEW`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: Beta/preview voice features excluded unless separately approved.
- Standalone audio distribution: `HOLD_REVIEW`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `HOLD_REVIEW`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: AWS account, service terms, selected voice terms, and audiobook output distribution require owner/legal review.
- Voice rights status: `HOLD_REVIEW`
- Selected voice ID: `OWNER_SELECTION_REQUIRED`
- Selected voice display name: OWNER_SELECTION_REQUIRED
- Selected voice type: `unknown`
- Selected voice license evidence: OWNER_SELECTION_REQUIRED
- Selected voice rights summary: HOLD_REVIEW
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- selected_voice_type is missing or requires review.
- standalone audio distribution evidence is not approved.
- attribution requirements require owner/legal review.
- beta feature exclusion evidence is missing or requires review.
- selected provider voice is not selected.
- selected voice type is unknown.
- selected voice must be a provider/platform voice or generated voice before internal evaluation.
- selected provider voice license evidence is missing.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- paid plan evidence status is missing or requires review.
- paid plan evidence is required before using this provider for internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

### Owner-Controlled Narrator Voice

- Provider ID: `owned-narrator-voice`
- Official terms: [terms](https://theearnalism.com/contact)
- Commercial-use evidence: [commercial evidence](https://theearnalism.com/contact)
- Voice license evidence: [voice evidence](https://theearnalism.com/contact)
- Paid plan required: `False`
- Paid plan evidence status: `NOT_REQUIRED`
- Paid plan evidence URL: missing
- Beta features allowed: `False`
- Beta features allowed alias: `False`
- Beta features excluded evidence: Not applicable to owned narrator workflow.
- Standalone audio distribution: `HOLD_REVIEW`
- Standalone audio distribution evidence: `HOLD_REVIEW`
- Attribution required: `False`
- Commercial internal-eval permission: `HOLD_REVIEW`
- Provider terms review status: `HOLD_REVIEW`
- Data retention review status: `HOLD_REVIEW`
- Data/privacy notes: Requires direct owner/narrator agreement, consent, recording release, and internal legal review before internal evaluation.
- Voice rights status: `OWNER_REVIEW_REQUIRED`
- Selected voice ID: `OWNER_SELECTION_REQUIRED`
- Selected voice display name: OWNER_SELECTION_REQUIRED
- Selected voice type: `unknown`
- Selected voice license evidence: OWNER_SELECTION_REQUIRED
- Selected voice rights summary: HOLD_REVIEW
- Selected voice attribution: `HOLD_REVIEW`
- Selected voice restrictions: `HOLD_REVIEW`
- Owner approval: `OWNER_REVIEW_REQUIRED`
- Legal/internal review: `LEGAL_REVIEW_REQUIRED`
- Internal-eval decision: `HOLD_PROVIDER_REVIEW`
- Internal generation status: `HOLD_PROVIDER_REVIEW`
- Public production status: `PRODUCTION_BLOCKED`

Issues:
- selected_voice_type is missing or requires review.
- standalone audio distribution evidence is not approved.
- beta feature exclusion evidence is missing or requires review.
- selected provider voice is not selected.
- selected voice type is unknown.
- selected voice must be a provider/platform voice or generated voice before internal evaluation.
- selected provider voice license evidence is missing.
- selected voice attribution requirements require review.
- selected voice restrictions require review.
- owner approval is required before provider internal evaluation.
- legal/internal review is required before provider internal evaluation.
- commercial internal-eval permission is missing or requires review.
- standalone audio distribution evidence is missing or requires review.
- provider terms review is missing or requires review.
- data retention review is missing or requires review.

Warnings:
- Strategic preferred path, but still blocked until owner/narrator agreement and legal review exist.
