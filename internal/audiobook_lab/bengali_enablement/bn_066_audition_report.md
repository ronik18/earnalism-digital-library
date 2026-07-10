# bn-066 Audition Report

Generated: 2026-07-10T09:31:50Z

## Classification

`AUDITION_PASS`

`bn-066` is the primary Stage 1 candidate. Stage 1F added a bounded OpenAI listening-QA budget gate, then ran one Sarvam/pooja literary_warm_pacing representative sample. The 45 second sample passed schema-3 listening QA under `bengali_audiobook_acceptance_v2_92` with overall score `9.3`, confidence `0.95`, no fatal flags, and no frontmatter.

## Preflight

- Canonical slug: `bn-066`
- Title: `Anandamath`
- Reader data: present in `content/books`, `data/controlled_publications`, and `backend/data/controlled_publications`
- Source evidence: present
- Rights note: commercial-use rights pass in `content/books/bn-066/source-rights.md`
- Audio state: hidden, not public Listen
- Sample issue: source/page boilerplate appears in the opening chapter and must be stripped before TTS sample synthesis
- Estimated total text characters: `203672`

## Stage 1D Attempt Result

- Provider: `sarvam`
- Selected voice: `pooja`
- Requested style: `literary_warm_pacing`
- Run dir: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition`
- Report path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/bengali_tts_provider_bakeoff_report.json`
- Sample text path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/bakeoff_passages.json`
- Estimated cost: `0.0119 USD`
- Actual spend observed: `0.00 USD`
- Output audio path: none
- Blocker: `LISTENING_QA_NOT_AVAILABLE`
- OpenAI listening QA blocker detail: `EARNALISM_ENABLE_OPENAI_LISTENING_QA is not true`
- Prior and current capability probes listed voice: `pooja`
- New samples generated: `0`

## Stage 1E Attempt Result

- Provider: `sarvam`
- Selected voice: `pooja`
- Requested style: `literary_warm_pacing`
- Intended run dir: `internal/audiobook_lab/bengali_enablement/bn_066_stage1e_pooja_audition_with_listening_qa`
- Report path: none; provider command was not run
- Sample text path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/bakeoff_passages.json`
- Estimated TTS cost carried forward: `0.0119 USD`
- Actual spend observed: `0.00 USD`
- Output audio path: none
- Blocker: `LISTENING_QA_BUDGET_GATE_MISSING`
- OpenAI listening QA blocker detail: no repo-enforced bounded OpenAI/listening-QA USD cap exists under the authorized `5 USD` sprint cap
- New samples generated: `0`

## Stage 1F Attempt Result

- Provider: `sarvam`
- Selected voice: `pooja`
- Requested style: `literary_warm_pacing`
- Run dir: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa`
- Report path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/bengali_tts_provider_bakeoff_report.json`
- Sample text path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/bakeoff_passages.json`
- Output audio path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d_clipped.mp3`
- Source audio path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d.wav`
- Duration: `45.0` seconds
- Estimated TTS cost: `0.0119 USD`
- Estimated listening-QA cost: `0.05 USD`
- Estimated total cost: `0.0619 USD`
- Actual provider billing: not reported by provider tools
- Listening QA: `PASS`
- Overall listening score: `9.3`
- Confidence: `0.95`
- Fatal flags: none
- Frontmatter present: false
- New samples generated: `1`

## Paid Gates

- `MAX_TTS_BUDGET_USD=5`: present inline
- `EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true`: present inline
- `EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true`: present inline
- `EARNALISM_STOP_ON_BUDGET_EXCEEDED=true`: present inline
- `EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=5`: present inline
- `EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=2`: present inline
- `EARNALISM_ENABLE_OPENAI_LISTENING_QA=true`: present inline for Stage 1E
- `EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio`: present inline for Stage 1E
- `EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=1`: present inline for Stage 1F
- `SARVAM_API_KEY`: present, value not printed
- `OPENAI_API_KEY`: present, value not printed
- Bounded listening-QA USD cap: pass

## Proposed Representative Samples

- Opening prose, after stripping source/page header text.
- Mid-book prose sample, capped to a small representative segment.
- Dialogue or difficult phrase sample if budget remains.

## Required Next Action

Prepare a guarded full-book TTS owner approval prompt:

1. Use Sarvam `pooja` and `literary_warm_pacing` unless owner chooses a new bakeoff.
2. Keep `bn-066` audio hidden until full-book source, listening, ASR, sync, upload, metadata, endpoint, and browser gates pass.
3. Do not publish, upload, expose Listen, or mutate public release gates in the full-book preparation step.

Do not run full-book TTS before a representative audition passes.

## Release Truth

No public audio approval changed. `bn-066` remains Stage 1 only while `paid_tts.lock` is active and until future representative plus full release gates pass.
