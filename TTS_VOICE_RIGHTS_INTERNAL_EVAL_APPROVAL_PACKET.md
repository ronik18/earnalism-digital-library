# TTS Voice Rights Internal-Eval Approval Packet

This packet is part of the English onboarding orchestrator. It does not approve production audio.

- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production approval status: `PRODUCTION_BLOCKED` for every candidate
- Real audio generation: `false`
- Model downloads or paid APIs: `false`

## Kokoro

- Candidate ID: `kokoro`
- Internal-eval status: `HOLD_VOICE_RIGHTS`
- Voice rights evidence URL: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- Voice rights summary: Voice list is documented upstream, but Earnalism has not completed speaker-rights, voice provenance, or owner approval review.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `OPEN_WEIGHT_VOICE_UNVERIFIED`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Blockers: voice rights approval pending; owner internal-eval approval pending; legal review pending.
- Public production: `PRODUCTION_BLOCKED`

## MeloTTS

- Candidate ID: `melotts`
- Internal-eval status: `HOLD_VOICE_RIGHTS`
- Voice rights evidence URL: https://huggingface.co/myshell-ai/MeloTTS-English
- Voice rights summary: Model card lists speaker IDs, but Earnalism has not completed speaker-rights or voice provenance review.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `MODEL_CARD_SPEAKERS_UNVERIFIED`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Blockers: voice rights approval pending; owner internal-eval approval pending; legal review pending.
- Public production: `PRODUCTION_BLOCKED`

## Piper / Piper active fork

- Candidate ID: `piper`
- Internal-eval status: `HOLD_VOICE_RIGHTS`
- Voice rights evidence URL: https://github.com/rhasspy/piper/blob/master/VOICES.md
- Voice rights summary: Voice catalog is public, but each voice requires separate provenance, commercial, and speaker-rights review.
- Speaker identity status: `VARIES_BY_VOICE`
- Synthetic voice status: `VOICE_DEPENDENT_REVIEW_REQUIRED`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Blockers: per-voice rights review required; commercial status hold; owner internal-eval approval pending.
- Public production: `PRODUCTION_BLOCKED`

## Indic Parler-TTS

- Candidate ID: `indic-parler-tts`
- Internal-eval status: `HOLD_VOICE_RIGHTS`
- Voice rights evidence URL: https://huggingface.co/ai4bharat/indic-parler-tts
- Voice rights summary: Gated model/dataset metadata prevents complete speaker-rights verification from local public evidence.
- Speaker identity status: `UNVERIFIED_GATED_CARD`
- Synthetic voice status: `INDIC_MODEL_VOICE_REVIEW_REQUIRED`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Blockers: gated evidence review required; code license review pending; owner internal-eval approval pending.
- Public production: `PRODUCTION_BLOCKED`

## IndicF5

- Candidate ID: `indicf5`
- Internal-eval status: `HOLD_VOICE_RIGHTS`
- Voice rights evidence URL: https://huggingface.co/ai4bharat/IndicF5
- Voice rights summary: Model card identifies datasets, but speaker consent and voice rights require manual review before internal generation.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `INDIC_MODEL_VOICE_REVIEW_REQUIRED`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Blockers: voice rights review required; repo code license review pending; owner internal-eval approval pending.
- Public production: `PRODUCTION_BLOCKED`

## StyleTTS2

- Candidate ID: `styletts2`
- Internal-eval status: `BLOCKED`
- Voice rights evidence URL: https://github.com/yl4579/StyleTTS2#pre-trained-models
- Voice rights summary: Official README includes pretrained voice-use restrictions and permission/disclosure requirements; Earnalism treats this as blocked for generation.
- Speaker identity status: `CLONING_PERMISSION_REQUIRED`
- Synthetic voice status: `PRETRAINED_MODEL_RESTRICTIONS`
- Real-person voice clone risk: `HIGH`
- Internal eval allowed: `False`
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `BLOCKED`
- Blockers: high voice-cloning risk; pretrained model restrictions; legal review blocked for generation.
- Public production: `PRODUCTION_BLOCKED`
