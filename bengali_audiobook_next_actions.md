# Bengali Audiobook Campaign Next Actions

Status: `BENGALI_AUDIOBOOK_CAMPAIGN_ACTIVE`
Policy: `bengali_audiobook_acceptance_v2_92`
Campaign titles: `29`
Published Bengali audiobooks: `0`
Representative-passed titles: `0`

## Immediate Next Step

Run adaptive representative auditions for the shortest eligible title.

## Exact Command

```bash
railway run --project a8533934-35c4-463e-9f43-577a9ac391ee --service 5af42e7e-f518-4f6a-b602-d9950866501f --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- env EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN=true EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD=75 EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=8 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_ENABLE_OPENAI_LISTENING_QA=true EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio EARNALISM_LISTENING_POLICY_VERSION=bengali_audiobook_acceptance_v2_92 python3 internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py --manifest book_import_manifest.json --target-reader-only-approved-31 --goal-score 9.2 --policy bengali_audiobook_acceptance_v2_92 --adaptive-optimizer --resume --fail-closed --max-run-minutes 180
```
