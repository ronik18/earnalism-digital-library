# Audiobook Chapter Pipeline Report

- Book: `dracula`
- Language: `en`
- Chapter: `1`
- Status: `BLOCKED_UNTIL_EXPLICIT_EXECUTE_AND_PROVIDER_EVIDENCE`
- Mode: `generate-internal`
- Execute: `true`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Production: `PRODUCTION_BLOCKED`

| Stage | Status | Notes |
| --- | --- | --- |
| LOAD_CHAPTER_SOURCE | PASS | No blocker. |
| SANITIZE_NARRATION_TEXT | PASS | No blocker. |
| VALIDATE_NARRATION_TEXT | PASS | No blocker. |
| BUILD_SENTENCE_MAP | PASS | No blocker. |
| BUILD_CHUNK_MANIFEST | PASS | No blocker. |
| COST_ESTIMATE_AND_BUDGET_GATE | PASS | No blocker. |
| PROVIDER_EVIDENCE_GATE | BLOCKED | attribution requirements require owner/legal review.; beta feature exclusion evidence is missing or requires review. |
| ELEVENLABS_GENERATION_DRY_RUN_OR_EXECUTE | BLOCKED | ELEVENLABS_API_KEY is required for execute mode; provider evidence status must be ELIGIBLE_INTERNAL_EVAL_ONLY |
| IMPORT_AND_HASH_AUDIO | DRY_RUN_NO_AUDIO | No blocker. |
| BUILD_SYNC_MANIFEST | PASS | No blocker. |
| BUILD_QA_PACKETS | PASS | No blocker. |
| PUBLIC_RELEASE_BLOCK_GATE | PASS | No blocker. |
