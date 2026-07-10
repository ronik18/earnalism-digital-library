# Bengali Paid Audition Run Report

Generated: 2026-07-10T09:31:50Z

## Result

`AUDITION_PASS`

Stage 1F added a repo-enforced bounded OpenAI listening-QA budget gate and ran exactly one `bn-066` Sarvam/pooja representative sample. Sarvam generated a 45 second sample, bounded schema-3 OpenAI listening QA ran, and the audition passed `bengali_audiobook_acceptance_v2_92` with overall listening score `9.3`, confidence `0.95`, no fatal flags, and no frontmatter.

## Budget And Lock

- Authorized cap: `5 USD`
- Inline `MAX_TTS_BUDGET_USD`: `5`
- Representative paid gates: present for the paid command process
- Provider key: `SARVAM_API_KEY` present, value not printed
- Listening QA key: `OPENAI_API_KEY` present, value not printed
- Listening QA env: `EARNALISM_ENABLE_OPENAI_LISTENING_QA=true`, `EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio`
- Listening QA budget gate: `EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=1`
- Temporary lock holder: `audiobook_enablement_sprint_1`
- Lock status before: active with `current_holder: none`, `allowed_next_holders: []`
- Lock status during: held by `audiobook_enablement_sprint_1`
- Lock status after: active with `current_holder: none`, `allowed_next_holders: []`
- Estimated TTS cost: `0.0119 USD`
- Estimated listening-QA cost: `0.05 USD`
- Estimated total spend: `0.0619 USD`
- Actual provider billing: not reported by provider tools
- Public audio approval: none
- Audio upload/publication: none

## Titles Auditioned

`bn-066` completed one representative audition only.

## bn-066 Stage 1F Pooja + Bounded Listening QA

- Provider: `sarvam`
- Selected voice: `pooja`
- Requested style: `literary_warm_pacing`
- Run dir: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa`
- Report: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/bengali_tts_provider_bakeoff_report.json`
- Sample text: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/bakeoff_passages.json`
- Output audio path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d_clipped.mp3`
- Source audio path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d.wav`
- Duration: `45.0` seconds
- Estimated total cost: `0.0619 USD`
- Actual provider billing: not reported by provider tools
- New samples generated: `1`
- Listening QA: `PASS`
- Overall listening score: `9.3`
- Confidence: `0.95`
- Fatal flags: none
- Classification: `AUDITION_PASS`

## Stage 1B Carry-Forward Evidence

- The Stage 1B `--voice-filter sarvam:ratan` syntax was not accepted by the bakeoff selector, which matches `ratan` or `sarvam/ratan`.
- The Stage 1B capability probe listed `pooja`.
- Stage 1D owner scope approved `pooja`; the script selected it successfully.
- The next blocker is QA availability, not voice support.

## Titles Skipped

| Slug | Reason | Next Action |
| --- | --- | --- |
| `bn-066` | Audition passed; still not public audio | Seek owner approval for guarded full-book TTS, then full release gates |
| `muchiram-gurer-jibanchorit` | Conditional only; timeout-prone sample splitting not complete | Create compact split opening sample before retry |
| `book-d19e96859f` | Repair diagnostic only; use group-only cleaned sample | Define targeted repair sample |
| `book-f5d593e1f4` | Repair diagnostic only; use group-only cleaned sample | Define targeted repair sample |
| `pather-panchali` | Rights/source/cover repair track before paid audio | Complete repair review |
| `a-ghost-story` | Out of Bengali-priority scope | Keep reader-first/audio-hidden |

## Public Release Truth

- No new Listen CTA.
- No public audio exposure.
- No static `/audio/...` fallback.
- No browser/system speech fallback.
- No word-level sync claim.
- No AudioObject for non-approved audio.
- No paid Listen approval.

## Full-Book Readiness

- `bn-066`: `AUDITION_PASS`; ready for full-book TTS owner approval prompt, not for public Listen or publication.
- `muchiram-gurer-jibanchorit`: `NEEDS_SEGMENTATION_REPAIR`.
- `book-d19e96859f`: `NEEDS_TEXT_REPAIR`.
- `book-f5d593e1f4`: `NEEDS_TEXT_REPAIR`.
- `pather-panchali`: `NEEDS_RIGHTS_DOCUMENT`.
- `a-ghost-story`: `HOLD_WITH_NEXT_ACTION`.
