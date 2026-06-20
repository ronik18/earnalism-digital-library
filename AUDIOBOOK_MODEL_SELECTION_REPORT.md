# Audiobook Model Selection Report

Final status: `NO_MODEL_APPROVED_YET`

No model is approved for public preview or full audiobook release. This bake-off is internal-review-only and dry-run by default.

## Current Recommendation

- Best Bengali pronunciation: `AI4Bharat Indic-TTS` as baseline only.
- Best literary naturalness candidate: `Svara-TTS v1` pending local sample and license review.
- Best emotion/style candidate: `Svara-TTS v1` pending documentation-confirmed style tags.
- Best commercial/license readiness candidate: `MahaTTS/MahaTTSv2` pending exact license verification.
- Best local generation cost candidate: `AI4Bharat Indic-TTS` or `MahaTTS` after installation/resource check.
- Final recommended model: `NO_MODEL_APPROVED_YET`.
- Required next step: generate owner-approved internal samples, complete license review, then complete human listening review.

## Safety

- Kshudhita Pashan remains pipeline-only.
- Dracula remains the only live approved reading title.
- No public audio URL was created.
- No Listen Now CTA was added.
- No paid or cloud provider API was called.

## Model Statuses

| Model | Status | License status | Audio generated |
| --- | --- | --- | --- |
| svara-tts-v1 | PRIMARY_BENCHMARK | LICENSE_REVIEW_REQUIRED | False |
| mahatts-v2 | PRIMARY_BENCHMARK | LICENSE_REVIEW_REQUIRED | False |
| ai4bharat-indic-tts | PRONUNCIATION_BASELINE | LICENSE_REVIEW_REQUIRED | False |
| f5-tts | RESEARCH_ONLY_LICENSE_CHECK_REQUIRED | LICENSE_REVIEW_REQUIRED | False |
| xtts-v2 | RESEARCH_ONLY_UNSUPPORTED_BENGALI | NOT_EVALUATED_BY_ADAPTER | False |
| chatterbox-multilingual-v3 | RESEARCH_ONLY_UNSUPPORTED_BENGALI | NOT_EVALUATED_BY_ADAPTER | False |
| dia | EXCLUDED_FOR_BENGALI | NOT_EVALUATED_BY_ADAPTER | False |
