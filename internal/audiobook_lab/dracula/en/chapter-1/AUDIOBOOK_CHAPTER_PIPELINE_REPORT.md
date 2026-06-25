# Audiobook Chapter Pipeline Report

- Book: `dracula`
- Language: `en`
- Chapter: `1`
- Status: `DRY_RUN_READY`
- Mode: `dry-run`
- Execute: `false`
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
| PROVIDER_EVIDENCE_GATE | PASS | No blocker. |
| ELEVENLABS_GENERATION_DRY_RUN_OR_EXECUTE | PASS | No blocker. |
| IMPORT_AND_HASH_AUDIO | DRY_RUN_NO_AUDIO | No blocker. |
| BUILD_SYNC_MANIFEST | PASS | No blocker. |
| BUILD_QA_PACKETS | PASS | No blocker. |
| PUBLIC_RELEASE_BLOCK_GATE | PASS | No blocker. |
