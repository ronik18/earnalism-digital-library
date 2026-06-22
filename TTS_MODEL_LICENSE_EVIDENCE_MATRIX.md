# TTS Model License Evidence Matrix

This local report does not approve production audio. It records evidence status only.

| Candidate | Official repo | Model card | Commercial use | Code license | Weights license | Voice license | Internal eval | English | Bengali | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kokoro | [repo](https://github.com/hexgrad/kokoro) | [card](https://huggingface.co/hexgrad/Kokoro-82M) | ALLOWED | Apache-2.0 | Apache-2.0 | HOLD_REVIEW | HOLD_VOICE_RIGHTS | HIGH_INTERNAL_EVAL | LOW | HOLD_VOICE_RIGHTS |
| MeloTTS | [repo](https://github.com/myshell-ai/MeloTTS) | [card](https://huggingface.co/myshell-ai/MeloTTS-English) | ALLOWED | MIT | MIT | HOLD_REVIEW | HOLD_VOICE_RIGHTS | MEDIUM_INTERNAL_EVAL | LOW | HOLD_VOICE_RIGHTS |
| Piper / Piper active fork | [repo](https://github.com/rhasspy/piper) | [card](https://github.com/rhasspy/piper/blob/master/VOICES.md) | HOLD_REVIEW | MIT | MIT_OR_VARIES_BY_VOICE | VARIES_BY_VOICE | HOLD_VOICE_RIGHTS | MEDIUM_INTERNAL_EVAL | LOW | HOLD_LICENSE_REVIEW |
| Indic Parler-TTS | [repo](https://huggingface.co/ai4bharat/indic-parler-tts) | [card](https://huggingface.co/ai4bharat/indic-parler-tts) | ALLOWED | HOLD_REVIEW | Apache-2.0 | HOLD_REVIEW | HOLD_VOICE_RIGHTS | MEDIUM_INTERNAL_EVAL | HIGH_INTERNAL_EVAL | HOLD_LICENSE_REVIEW |
| IndicF5 | [repo](https://github.com/AI4Bharat/IndicF5) | [card](https://huggingface.co/ai4bharat/IndicF5) | ALLOWED | HOLD_REVIEW | MIT | HOLD_REVIEW | HOLD_VOICE_RIGHTS | MEDIUM_INTERNAL_EVAL | HIGH_INTERNAL_EVAL | HOLD_LICENSE_REVIEW |
| StyleTTS2 | [repo](https://github.com/yl4579/StyleTTS2) | [card](https://github.com/yl4579/StyleTTS2) | UNKNOWN | MIT | HOLD_REVIEW | HOLD_REVIEW | BLOCKED | LICENSE_REVIEW_ONLY | LOW | BLOCKED |

## Evidence Detail

### Kokoro

- Official repository: https://github.com/hexgrad/kokoro
- Official model card: https://huggingface.co/hexgrad/Kokoro-82M
- License URL: https://www.apache.org/licenses/LICENSE-2.0
- Dataset/license notes: Official model card lists Apache-licensed model/weights, permissive/non-copyrighted training-data notes, and named CC BY training data. This is sufficient for model-license review but not enough for Earnalism voice/speaker-rights approval.
- Attribution required: `True`
- Voice rights evidence URL: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- Voice rights summary: Upstream voice list is documented, including selectable Kokoro voices, but no Earnalism-reviewed evidence yet proves the selected voice is non-human/synthetic or otherwise cleared for internal generation. Owner/legal review must document selected-voice speaker provenance and commercial internal-eval permission.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `OPEN_WEIGHT_VOICE_UNVERIFIED`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `MEDIUM`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Internal eval blockers: selected Kokoro voice/speaker rights evidence missing; selected voice synthetic/non-human status not owner-verified; owner internal-eval approval pending; legal internal-eval review pending.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Evidence sources reviewed: https://github.com/hexgrad/kokoro, https://huggingface.co/hexgrad/Kokoro-82M
- Evidence notes: Official GitHub README and Hugging Face card document Apache-2.0 model/weights, commercial deployment language, local inference, and English suitability. The linked VOICES.md identifies available voices but does not provide Earnalism-complete speaker identity, consent, or selected-voice commercial rights approval.
- Decision reason: voice_license is missing or requires review.; voice rights evidence is missing or varies by voice.; speaker identity or voice provenance remains unresolved.; synthetic voice status remains unresolved.

### MeloTTS

- Official repository: https://github.com/myshell-ai/MeloTTS
- Official model card: https://huggingface.co/myshell-ai/MeloTTS-English
- License URL: https://opensource.org/license/mit
- Dataset/license notes: Official GitHub README and Hugging Face model card state MIT license and free commercial/non-commercial use. Speaker/checkpoint voice-rights provenance still requires review before Earnalism internal generation.
- Attribution required: `True`
- Voice rights evidence URL: https://huggingface.co/myshell-ai/MeloTTS-English
- Voice rights summary: Model card lists English accent/speaker options, but Earnalism has not completed selected-speaker provenance, consent, or voice-rights review for internal generation.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `MODEL_CARD_SPEAKERS_UNVERIFIED`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `MEDIUM`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Internal eval blockers: selected MeloTTS speaker/voice rights evidence missing; selected speaker synthetic/non-human status not owner-verified; owner internal-eval approval pending; legal internal-eval review pending.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Evidence sources reviewed: https://github.com/myshell-ai/MeloTTS, https://huggingface.co/myshell-ai/MeloTTS-English
- Evidence notes: Official GitHub README and Hugging Face card document MIT licensing, commercial/non-commercial use, English accents, and local model loading. The model card lists speaker/accent examples but does not provide Earnalism-complete speaker identity, consent, or selected-speaker commercial rights approval.
- Decision reason: voice_license is missing or requires review.; voice rights evidence is missing or varies by voice.; speaker identity or voice provenance remains unresolved.; synthetic voice status remains unresolved.

### Piper / Piper active fork

- Official repository: https://github.com/rhasspy/piper
- Official model card: https://github.com/rhasspy/piper/blob/master/VOICES.md
- License URL: https://github.com/rhasspy/piper/blob/master/LICENSE.md
- Dataset/license notes: Rhasspy Piper code and Hugging Face piper-voices metadata are MIT, but each voice/config must be reviewed individually; active forks or repackages may have different obligations.
- Attribution required: `True`
- Voice rights evidence URL: https://github.com/rhasspy/piper/blob/master/VOICES.md
- Voice rights summary: Voice catalog is public, but each voice requires separate provenance, commercial, and speaker-rights review.
- Speaker identity status: `VARIES_BY_VOICE`
- Synthetic voice status: `VOICE_DEPENDENT_REVIEW_REQUIRED`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `MEDIUM`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Internal eval blockers: per-voice rights review required; commercial status hold; owner internal-eval approval pending.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Evidence sources reviewed: https://github.com/rhasspy/piper, https://huggingface.co/rhasspy/piper-voices
- Evidence notes: Official Piper code license is MIT and piper-voices metadata is MIT, but per-voice provenance and active-fork/package obligations require manual legal review before any internal generation.
- Decision reason: commercial_use_status is missing or requires review.; commercial-use evidence is not approved.; weights license evidence is missing or varies by voice.; voice rights evidence is missing or varies by voice.

### Indic Parler-TTS

- Official repository: https://huggingface.co/ai4bharat/indic-parler-tts
- Official model card: https://huggingface.co/ai4bharat/indic-parler-tts
- License URL: https://www.apache.org/licenses/LICENSE-2.0
- Dataset/license notes: Official Hugging Face metadata lists Apache-2.0 and GLOBE-annotated dataset, but model card access is gated and speaker/voice consent needs manual review.
- Attribution required: `True`
- Voice rights evidence URL: https://huggingface.co/ai4bharat/indic-parler-tts
- Voice rights summary: Gated model/dataset metadata prevents complete speaker-rights verification from local public evidence.
- Speaker identity status: `UNVERIFIED_GATED_CARD`
- Synthetic voice status: `INDIC_MODEL_VOICE_REVIEW_REQUIRED`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `MEDIUM`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Internal eval blockers: gated evidence review required; code license review pending; owner internal-eval approval pending.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Evidence sources reviewed: https://huggingface.co/ai4bharat/indic-parler-tts
- Evidence notes: Official Hugging Face API/card metadata documents Apache-2.0 weights and Indic language coverage; gated card/data and unresolved voice rights keep this HOLD.
- Decision reason: code_license is missing or requires review.; voice_license is missing or requires review.; code license evidence is missing.; voice rights evidence is missing or varies by voice.

### IndicF5

- Official repository: https://github.com/AI4Bharat/IndicF5
- Official model card: https://huggingface.co/ai4bharat/IndicF5
- License URL: https://opensource.org/license/mit
- Dataset/license notes: Official Hugging Face metadata lists MIT model license and Rasa/IndicVoices-R datasets; GitHub repo lacks a clear LICENSE file and voice consent needs manual review.
- Attribution required: `True`
- Voice rights evidence URL: https://huggingface.co/ai4bharat/IndicF5
- Voice rights summary: Model card identifies datasets, but speaker consent and voice rights require manual review before internal generation.
- Speaker identity status: `UNVERIFIED`
- Synthetic voice status: `INDIC_MODEL_VOICE_REVIEW_REQUIRED`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `MEDIUM`
- Real-person voice clone risk: `MEDIUM`
- Internal eval allowed: `False`
- Internal eval blockers: voice rights review required; repo code license review pending; owner internal-eval approval pending.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `LEGAL_REVIEW_REQUIRED`
- Evidence sources reviewed: https://github.com/AI4Bharat/IndicF5, https://huggingface.co/ai4bharat/IndicF5
- Evidence notes: Official Hugging Face metadata documents MIT weights and Bengali-language support; missing repo license file plus dataset/speaker-rights review keep this HOLD.
- Decision reason: code_license is missing or requires review.; voice_license is missing or requires review.; code license evidence is missing.; voice rights evidence is missing or varies by voice.

### StyleTTS2

- Official repository: https://github.com/yl4579/StyleTTS2
- Official model card: https://github.com/yl4579/StyleTTS2
- License URL: https://github.com/yl4579/StyleTTS2/blob/main/LICENSE
- Dataset/license notes: Official README documents pre-trained model voice-use restrictions and requires listener disclosure or permission for cloned voices; pretrained weights/license and speaker rights are not approved.
- Attribution required: `True`
- Voice rights evidence URL: https://github.com/yl4579/StyleTTS2#pre-trained-models
- Voice rights summary: Official README includes pretrained voice-use restrictions and permission/disclosure requirements; Earnalism treats this as blocked for generation.
- Speaker identity status: `CLONING_PERMISSION_REQUIRED`
- Synthetic voice status: `PRETRAINED_MODEL_RESTRICTIONS`
- Local inference feasible: `True`
- Network required: `False`
- Real-person voice risk: `HIGH`
- Real-person voice clone risk: `HIGH`
- Internal eval allowed: `False`
- Internal eval blockers: high voice-cloning risk; pretrained model restrictions; legal review blocked for generation.
- Owner internal-eval approval: `OWNER_REVIEW_REQUIRED`
- Legal internal-eval review: `BLOCKED`
- Evidence sources reviewed: https://github.com/yl4579/StyleTTS2, https://huggingface.co/yl4579/StyleTTS2-LJSpeech, https://huggingface.co/yl4579/StyleTTS2-LibriTTS
- Evidence notes: Official repo code is MIT, but pre-trained model rules and high voice-cloning risk make this blocked for Earnalism generation.
- Decision reason: weights_license is missing or requires review.; voice_license is missing or requires review.; commercial_use_status is missing or requires review.; commercial-use evidence is not approved.
