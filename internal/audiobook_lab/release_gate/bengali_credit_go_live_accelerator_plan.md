# Bengali Credit Go-Live Accelerator Plan

Generated: `2026-07-05T22:09:02Z`

## Status

- Latest quota probe status: `PASS`
- Best observed provider/voice: `sarvam/ratan`
- Best observed score: `9.4`
- Existing samples reused: `0`

## Top Bengali Candidates By Popularity

1. `book-2e468c4990` - কাবুলিওয়ালা - score `100.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
2. `pather-panchali` - পথের পাঁচালী - score `99.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
3. `devdas` - দেবদাস - score `98.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
4. `book-ac5a71075e` - পোস্টমাস্টার - score `97.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
5. `book-1090573dff` - ছুটি - score `96.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
6. `bn-007` - নষ্টনীড় - score `95.0` - `needs_controlled_source` - content/source preflight before any audio spend
7. `book-c307a57868` - স্ত্রীর পত্র - score `94.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
8. `book-5aedda79fe` - শাস্তি - score `93.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
9. `book-edfcf810c5` - ক্ষুধিত পাষাণ - score `92.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
10. `book-fbdf2991ab` - সুভা - score `91.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
11. `book-0986aeb7e3` - হৈমন্তী - score `90.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
12. `book-a23625bf36` - সমাপ্তি - score `89.0` - `provider_audition_ready` - reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes
13. `book-4b944e64fa` - একরাত্রি - score `88.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
14. `bn-027` - অপরিচিতা - score `87.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse
15. `bn-031` - মহেশ - score `86.0` - `fresh_provider_only` - clean-manuscript provider audition only; no local-audio reuse

## Next Command

```bash
railway run --project a8533934-35c4-463e-9f43-577a9ac391ee --service 5af42e7e-f518-4f6a-b602-d9950866501f --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- env EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=10 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_ENABLE_OPENAI_LISTENING_QA=true EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py --manifest book_import_manifest.json --candidate-slugs book-ac5a71075e,book-1090573dff,book-4b944e64fa --providers sarvam,google,azure,openai --run-dir internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T220737Z --resume-existing-samples --judge-existing-only --target-near-pass-only --no-new-synthesis --max-passages 5 --max-seconds-per-sample 75 --fail-closed
```
