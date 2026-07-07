# Repo Cleanup Report

Generated: 2026-07-05

## Branch

- Current branch: `codex/hero-dracula-book-rendering-polish`
- Default remote branch: `origin/main`
- No history rewrite or force-push performed.

## Source Changes Kept

- `.gitignore`
  - Added release-factory run directory, heartbeat, PID, JSONL, log, trace, and generated media ignores.
  - Preserves local audit artifacts while preventing new timestamped runs and audio/sidecar outputs from polluting commits.
- `internal/audiobook_lab/scripts/release_catalog_factory.py`
  - Added catalog/per-book JSONL event logging.
  - Added content-size ordering flags and release-order barrier.
  - Added unique-title, duplicate-title, content-size ranking, and cost/time forecast outputs.
  - Added stricter fail-closed audio-quality QA scores so transcript/sync alone cannot claim premium readiness.
  - Added lane-aware scheduling/dashboard fields for preflight, cover, audio reuse, TTS, ASR/sync, upload, metadata, browser, and publish-barrier visibility.
  - Added explicit mandatory listening-quality release gates: naturalness, pronunciation, emotional expression, punctuation pauses, pacing, continuity, anti-robotic cadence, anti-mechanical texture, anti-list-reading rhythm, anti-choppy joins, and listener enjoyment.
  - Bumped catalog QA schema to `3`; missing automated listening-sample evidence now blocks publish.
- `internal/audiobook_lab/scripts/factory_hooks/tts_hook.py`
  - Fixed existing-audio reuse success path.
  - Added `cost_optimization_decision.json` for stale/missing audio repair decisions.
- `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`
  - Added recovery of prior passing `tts_hook_result.json` for resumed per-book runs.
  - Added Bengali ASR normalization/projection lane for script-shifted Bengali/Devanagari/Latin ASR outputs, with fail-closed blocker categories.
  - Added QA schema `3` listening-quality report generation and validation.
  - Produces `listening_quality_report.json` with required sample windows, aggregate naturalness/pronunciation/expression/pause/pacing/continuity/listener-enjoyment fields, anti-robotic flags, and fail-closed blocker categories.
  - Refuses to reuse cached listening QA when the audio hash, schema version, rubric version, hook version, or language changes.
- `internal/audiobook_lab/scripts/factory_hooks/browser_hook.py`
  - Fixed audio-start latency measurement to use actual audio element readiness before older preload resource timings.
- `internal/audiobook_lab/scripts/bengali_asr_normalization.py`
  - Added Bengali script detection, phonetic/shadow matching, mismatch diagnostics, and self-tests.
- `internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - Added regression checks for missing schema-3 listening fields, complete PASS reports, robotic/mechanical blocker flags, and stale schema/hash/rubric/language cache invalidation.

## Generated Artifacts Preserved Locally, Not Intended For Git

- `internal/audiobook_lab/release_gate/catalog_*/`
- `internal/audiobook_lab/release_gate/*_20*/`
- Per-book run logs, heartbeats, PID files, event logs, sidecars, and audio files.
- Playwright traces/screenshots/videos and release-gate local outputs.

## Current Validation

- `python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/factory_hooks/tts_hook.py internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/factory_hooks/browser_hook.py internal/audiobook_lab/scripts/factory_hooks/common.py`
  - PASS
- `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`
  - PASS
- `python3 internal/audiobook_lab/scripts/bengali_asr_normalization.py --self-test`
  - PASS
- `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - PASS
- Factory hook validation:
  - PASS, internal default hooks configured.
- Dry ordered canary:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T095238Z/`
  - Attempted books: 3
  - Published books: 0
  - Stop guard: `stop-after-attempted reached: 3`
  - Content-size ranking path: `internal/audiobook_lab/release_gate/catalog_20260705T095238Z/catalog_content_size_ranking.json`
  - Cost forecast path: `internal/audiobook_lab/release_gate/catalog_20260705T095238Z/catalog_cost_time_forecast.json`
- `git diff --check` on changed factory/hook files:
  - PASS
- Redacted secret scan:
  - No full secret values printed.
  - Findings were env/example placeholders and a redacted command template.

## Current Blockers

- `a-ghost-story` browser latency was remeasured with the corrected Playwright audio-readiness gate:
  - Audiobook endpoint: HTTP `206`
  - Cold backend/API range probe: `1935.96ms`
  - Diagnostic audio resource fetch timing: `1168.6ms`
  - User-visible reader audio readiness: `0.0ms` because the `<audio>` element was already metadata/play-ready.
  - Threshold: `<1000ms`
  - Root cause: browser hook was gating on a cold preload/resource timing instead of the actual reader audio readiness state.
  - Result: browser hook `PASS`; `a-ghost-story` production metadata remains approved with uploaded/checksummed B2/S3 assets and audiobook endpoint `200/206`.
- The 3-book ordered continuation reached terminal fail-closed decisions:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T095238Z/`
  - Attempted books: `3`
  - Published books: `0`
  - Blocked by Bengali audio/manuscript mismatch: `3`
  - Bengali ASR normalization/projection lane executed and failed closed with evidence:
    - `muchiram-gurer-jibanchorit`: raw score `0.039`, normalized score `0.1948`, phonetic score `0.273`, confidence `0.024`
    - `book-d19e96859f`: raw score unavailable/zero, normalized score `0.353`, phonetic score `0.353`, confidence `0.0316`
    - `book-2ddbed8293`: raw score `0.4134`, normalized score `0.1852`, phonetic score `0.211`, confidence `0.0187`
  - Root cause: reused Bengali local audio cannot be proven to match canonical Bengali manuscripts; the ASR/projection lane identified mixed-script output but confidence stayed far below release thresholds.
  - Audio behavior: stale remote audio URLs were detected, valid local audio was reused, and no new TTS was generated.
- Source fixes added:
  - Factory hook result isolation now ignores stale generic `stage_result.json` from previous hook stages.
  - Bengali ASR no longer forces unsupported OpenAI transcription language code `bn`; it allows provider auto-detection.
  - Bengali ASR failures are terminal-blocked with explicit categories/evidence instead of halting the catalog generically.
- A second smallest ordered continuation proved blocked-order skip can move past the first Bengali ASR blockers:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T150741Z/`
  - Excluded: `book-63afd5e9be`, `muchiram-gurer-jibanchorit`, `book-d19e96859f`, `book-2ddbed8293`
  - Attempted books: `3`
  - Published books: `0`
  - Blocked by Bengali audio/manuscript mismatch: `3`
  - Evidence:
    - `book-f5d593e1f4`: raw score `0.0892`, normalized score `0.287`, phonetic score `0.287`, confidence `0.0269`
    - `book-0deb35c750`: raw score `0.2152`, normalized score `0.249`, phonetic score `0.249`, confidence `0.0219`
    - `book-754da4eab8`: raw score `0.0331`, normalized score `0.214`, phonetic score `0.214`, confidence `0.0195`
  - Result: terminal-blocked with evidence; no unsafe publish, no new TTS generation.
- A local six-book continuation found credential-sensitive cover work and more Bengali ASR terminal blockers:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T155242Z/`
  - Attempted books: `6`
  - Published books: `0`
  - Terminal Bengali audio/manuscript mismatch: `3`
    - `book-c7f3ce526c`
    - `book-a74c1a1451`
    - `book-2e468c4990`
  - Local-only cover blockers: `book-d2fe532e1c`, `bn-031`, `bn-027`
  - Root cause for cover blockers: Cloudinary credentials were not available locally; this was not a book-quality failure.
- A Railway-env targeted repair reran the three local cover blockers with production credentials:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T160304Z/`
  - Attempted books: `3`
  - Published books: `0`
  - `book-d2fe532e1c`: terminal Bengali audio/manuscript mismatch.
  - `bn-031`: terminal Bengali audio/manuscript mismatch.
  - `bn-027`: manuscript/content-integrity blocked by `page_number_line`; no TTS/upload/publish attempted.
- The exact next content-size-ranked six-book Railway wave was executed:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/`
  - Attempted books: `6`
  - Published books: `0`
  - Stale remote audio URLs detected: `3`
  - Valid local audio reused: `3`
  - New TTS generated: `0`
  - Estimated TTS spend: `$0.00`
  - Terminal Bengali audio/manuscript mismatch:
    - `book-2b9853ec52`: score `0.0`
    - `book-4968248842`: score `0.0655`
    - `book-fbdf2991ab`: score `0.1939`
  - English ASR transcript mismatch:
    - `the-open-window`: score `2.7796`
    - `the-student`: score `2.9296`
  - Premium audio-quality evidence missing:
    - `the-selfish-giant`: naturalness/expression/pause/pacing/overall scores remained `0.0`, confidence `0.8`; blocked fail-closed.
  - Result: no unsafe publish. `a-ghost-story` remains the only confirmed audiobook-live title.
- A lane-aware parallel wave was started after adding lane counters and separate worker budget flags:
  - Command used Railway production variables and excluded `book-63afd5e9be`, `a-ghost-story`, and all known evidenced blockers.
  - The wave advanced multiple books in parallel through cover, manuscript, rights metadata, audio reuse, and ASR/sync lanes.
  - It was intentionally stopped when the audiobook naturalness/expressiveness requirement was clarified as mandatory release policy.
  - No upload, metadata approval, browser publish, or new public audiobook exposure happened from that interrupted wave.
  - Validation after the policy update:
    - `python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/factory_hooks/browser_hook.py internal/audiobook_lab/scripts/bengali_asr_normalization.py`
    - `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`
    - `python3 internal/audiobook_lab/scripts/bengali_asr_normalization.py --self-test`
  - All three checks passed.
- New audiobook release policy:
  - Do not publish an audiobook merely because audio exists, ASR passes, sync passes, upload/checksum passes, or metadata can be approved.
  - `naturalness_score`, `pronunciation_score`, `emotional_expression_score`, `punctuation_pause_score`, `pacing_score`, and `continuity_score` must each be at least `9.7`.
  - The QA evidence must explicitly prove no robotic cadence, mechanical texture, list-reading rhythm, choppy joins, repeated identical sentence endings, abrupt TTS paragraph resets, fallback/system/browser/offline TTS, or placeholder audio.
  - Automated listening QA must include first/middle/final samples, random sections, dialogue/emotional sections, and regenerated/repaired regions where applicable.
  - If audio quality cannot reach the threshold, the audiobook remains hidden and is classified under audio provider quality limits instead of being published.
- Latest resume plan:
  - Path: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/catalog_resume_plan.json`
  - Next content-size-ranked candidates after excluding known blockers begin with:
    - `book-ac5a71075e`
    - `book-1090573dff`
    - `book-4b944e64fa`
    - `sredni-vashtar`
    - `book-5704b31005`
    - `the-gift-of-the-magi`
- Audio-quality judging is now enforced fail-closed; books without explicit premium audio-quality evidence will not publish.
- Latest QA schema-3 implementation validation:
  - Gap report: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/listening_qa_schema3_gap_report.json`
  - Terminal exclusion list: `internal/audiobook_lab/release_gate/terminal_blocker_exclusions.txt`
  - Hook validation: PASS after schema-3 changes.
- Latest six-book continuation after schema-3 listening QA implementation:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/`
  - Excluded: `book-63afd5e9be`, `a-ghost-story`, and known evidenced terminal blockers from `terminal_blocker_exclusions.txt`.
  - Attempted books: `6`
  - Published books: `0`
  - Terminal blockers: `4`
  - Terminal blockers skipped by order policy: `4`
  - Terminal exclusion file updated to include `bn-060` and `radharani`.
  - Valid local audio reused: `4`
  - New TTS generated: `0`
  - Estimated TTS spend: `$0.00`
  - Bengali audio/manuscript mismatch:
    - `bn-060`: score `0.1191`
    - `radharani`: score `0.0547`
  - Cover blockers:
    - `the-art-of-money-getting`: Cloudinary credentials required for generated cover upload in local environment.
    - `nishkriti`: Cloudinary credentials required for generated cover upload in local environment.
  - Rights metadata blocker:
    - `bn-035`/`bn-036` did not advance to publish; dashboard reports one rights-metadata-missing blocker and current bottleneck as cover lane.
  - Listening QA was not reached for this wave because earlier ASR/cover/rights gates failed first.
  - No upload, metadata approval, browser publish, or new public audiobook exposure happened.
- Railway-backed six-book continuation after rebuilding the terminal exclusion list:
  - Run: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/`
  - Railway credentials were available through `railway run`; cover blockers caused by missing local Cloudinary credentials were retried.
  - Attempted books: `6`
  - Published books: `0`
  - Cover repairs completed: `6` cover-lane passes in the active dashboard.
  - Valid local audio reused: `3`
  - New TTS generated: `0`
  - Estimated TTS spend: `$0.00`
  - New terminal Bengali audio/manuscript mismatch:
    - `bn-035`: score `0.0381`
  - Rights metadata/evidence blockers:
    - `the-art-of-money-getting`: missing `author_death_year`, `original_publication_year`, and deterministic public-domain evidence.
  - Prepared but not published/incomplete stage candidates:
    - `bn-036`: still at `asr_sync_queue`
    - `nishkriti`: cover PASS and TTS PASS; still at `asr_sync_queue`
    - `book-ac5a71075e`: cover PASS; still before rights/TTS completion
    - `book-1090573dff`: cover PASS; still before manuscript/rights/TTS completion
  - Zero-publish diagnosis: `internal/audiobook_lab/release_gate/zero_publish_wave_diagnosis.json`
  - Terminal exclusion file updated to include `bn-035`; current exclusion count: `25`.
  - Listening QA was not reached because earlier ASR/rights gates failed first.
  - No upload, metadata approval, browser publish, or new public audiobook exposure happened.
- The worktree remains noisy from earlier generated/imported content:
  - `179` modified tracked entries
  - `1` deleted tracked entry
  - `1135` untracked path entries from `git status --short`

## Bengali Audio Closure - 2026-07-07

- Updated intelligence memory and reports only.
- No Sarvam/OpenAI/Google/Azure calls were run.
- No TTS, ASR, sync, upload, metadata approval, browser publishing, or production mutation was run.
- No generated audio, sidecars, release_gate run folders, screenshots, traces, signed URLs, or caches should be staged from this closure.
- Keep for source-only review if desired:
  - `internal/earnalism_intelligence/provider_performance_memory.json`
  - `internal/earnalism_intelligence/decision_ledger.jsonl`
  - `internal/earnalism_intelligence/title_decision_history.json`
  - `internal/earnalism_intelligence/sprint_learnings.md`
  - `internal/earnalism_intelligence/audiobook_acceptance_policy.json`
  - `bengali_reader_only_final_sprint_status.json`
  - `bengali_audiobook_future_strategy.md`
  - `sprint_go_live_dashboard.md`
  - `repo_cleanup_report.md`

## PR87 Continuation Status - 2026-07-07

- No merge, commit, deploy, provider call, or production metadata mutation was performed.
- Latest `gh pr checks 87` still reports failed `backend + frontend + browser regression` and failed `regression gate`.
- Vercel deploy/canary jobs remain skipped because pre-deploy checks failed and Vercel preview was canceled by ignored build step.
- Before more Vercel preview/deploy work, upgrade the outdated Vercel CLI with `npm i -g vercel@latest` or `pnpm add -g vercel@latest`.

## Merge Safety

Not safe to merge as-is without selective staging. The intended source changes are limited to the factory scripts, hook scripts, `.gitignore`, and this cleanup report. Generated run artifacts should remain local/ignored unless a specific evidence artifact is intentionally promoted.

## Next Resume Command

```bash
railway run --project a8533934-35c4-463e-9f43-577a9ac391ee \
  --service 5af42e7e-f518-4f6a-b602-d9950866501f \
  --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- \
env \
EARNALISM_APPROVE_PAID_OPENAI_TTS=true \
EARNALISM_TTS_MAX_ESTIMATED_USD=25 \
EARNALISM_STOP_ON_BUDGET_EXCEEDED=true \
python3 internal/audiobook_lab/scripts/release_catalog_factory.py \
  --manifest book_import_manifest.json \
  --languages eng,ben \
  --max-books-active 6 \
  --max-preflight-workers 4 \
  --max-audio-reuse-workers 4 \
  --max-tts-workers 1 \
  --max-paid-workers 1 \
  --max-asr-workers 1 \
  --max-cover-workers 1 \
  --max-upload-workers 1 \
  --max-metadata-workers 1 \
  --max-browser-workers 1 \
  --max-attempts 2 \
  --wave-size 6 \
  --priority ready-first \
  --order-by content-size \
  --release-order ascending-content-size \
  --enforce-release-order \
  --allow-blocked-order-skip \
  --exclude-slugs "$(cat internal/audiobook_lab/release_gate/terminal_blocker_exclusions.txt)" \
  --publish-approved \
  --resume-from-latest \
  --fail-closed \
  --stop-after-attempted 6 \
  --max-run-minutes 90
```

## Recommendation

Do not rerun the terminal Bengali blockers blindly. They now have Bengali ASR normalization/projection evidence showing low-confidence audio/manuscript mismatch. Continue with small content-size waves and use Railway-backed execution when cover/upload/metadata credentials are needed. QA schema `3` listening-quality evidence is now wired, but no audiobook should publish until an approved structured listening judge emits passing schema-3 scores. Do not start a 20-book or 40-book wave until a six-book continuation publishes another title or produces clean terminal evidence for all candidates. English titles that fail ASR or lack premium audio-quality scores need targeted audio/provenance repair before they can publish. Robotic or mechanically stitched audiobooks must remain hidden.

## Next-Publish Wave Close-Out - 2026-07-05

- Run: `internal/audiobook_lab/release_gate/catalog_20260705T161042Z/`
- Command class: Railway-backed next-publish wave with `--stop-after-published 1` and `--stop-after-terminal-books 12`.
- Published before run: `a-ghost-story`
- Newly published this run: `0`
- Total published after run: `1`
- Attempted books: `12`
- Terminal blocked this wave: `6`
- Retryable blocked this wave: `6`
- TTS spend: `$0.00`; all audio candidates were local reuse, no paid TTS generation ran.
- Listening QA reached: `0` books; all candidates failed earlier ASR or rights gates.
- New terminal Bengali audio/manuscript mismatch blockers added to `internal/audiobook_lab/release_gate/terminal_blocker_exclusions.txt`:
  - `bn-036`
  - `nishkriti`
  - `book-ac5a71075e`
  - `book-1090573dff`
  - `book-4b944e64fa`
  - `book-5704b31005`
- Retryable blockers that should not be added to terminal exclusions:
  - `the-art-of-money-getting`: rights metadata/evidence incomplete.
  - `sredni-vashtar`: English ASR transcript match `1.4099`.
  - `the-gift-of-the-magi`: English ASR transcript match `6.7837`.
  - `the-tell-tale-heart`: English ASR transcript match `9.5558`.
  - `dsires-baby`: English ASR transcript match `9.4039`.
  - `the-cop-and-the-anthem`: English ASR transcript match `3.3748`.
- Required next repair before another publish attempt:
  - Add a targeted English ASR/source-provenance repair lane for local reused audio, especially near-threshold failures like `the-tell-tale-heart`.
  - For English candidates, confirm whether the reused local audio includes title/edition/source text differences or is the wrong narration before regenerating.
  - If correct local audio cannot reach `transcript_match_score >= 9.7`, regenerate from clean manuscript only with approved paid TTS budget, then run schema-3 listening QA before upload.
- Zero-publish diagnosis: `internal/audiobook_lab/release_gate/next_publish_failure_diagnosis.json`
- Current terminal exclusion count: `31`
- Merge hygiene:
  - Keep reusable source changes only: factory code, hooks, tests, docs, `.gitignore`, and this report.
  - Do not commit release-gate outputs, dashboards, generated covers, MP3/WAV/FLAC, sidecars, logs, caches, heartbeats, signed URLs, or screenshots.

## Targeted Second-Live Push - The Tell-Tale Heart - 2026-07-05

- Target: `the-tell-tale-heart`
- Result: not published.
- Current fully audiobook-live count remains `1`: `a-ghost-story`.
- Exact local controlled-publication audit:
  - Controlled `public_book.json` files: `161`
  - Reader-ready/local reader-live count: `161`
  - Reader-only count: `160`
  - Audiobook release-gate approved count: `1`
- Evidence written:
  - Live audit: `internal/audiobook_lab/release_gate/live_status_audit.json`
  - Repair plan: `internal/audiobook_lab/release_gate/the-tell-tale-heart_20260705T181723Z/the_tell_tale_heart_repair_plan.json`
  - English ASR/source provenance: `internal/audiobook_lab/release_gate/the-tell-tale-heart_20260705T181723Z/english_asr_source_provenance_report.json`
  - Terminal/retry report: `internal/audiobook_lab/release_gate/the-tell-tale-heart_20260705T181723Z/the_tell_tale_heart_terminal_or_retry_report.json`
- Source/provenance repair completed:
  - Existing historical audio was rejected as release-unsafe because sidecar provenance showed `provider_used=piper` and synthetic alignment.
  - TTS hook now blocks release-unsafe existing provenance and falls through to approved OpenAI TTS when paid approval/budget are present.
- ASR scoring repair completed:
  - The prior English ASR score `1.1593` was caused by long-string character `SequenceMatcher` behavior, despite token coverage `0.9953`.
  - ASR scoring now uses token-order similarity plus coverage, with `autojunk=False`.
  - Regression test added: `internal/audiobook_lab/scripts/test_asr_transcript_similarity.py`.
  - Current regenerated OpenAI audio ASR/sync evidence: `transcript_match_score=9.9219`, `sync_score=9.9219`, `auto_estimated_sync=false`.
  - Additional safety guard added: first and last narrated spans must match, otherwise ASR blocks even if aggregate score is high.
- Listening QA implementation completed:
  - Added opt-in internal OpenAI listening QA via `EARNALISM_ENABLE_OPENAI_LISTENING_QA=true`.
  - Railway model availability probe showed `gpt-audio` and `gpt-audio-1.5` are available; `gpt-4o-audio-preview` is not available in this project.
  - Listening samples are now regenerated from the current final audio on every attempt to avoid stale sample evidence.
  - Listening window selection now preserves first/middle/final plus three random samples.
- TTS attempts:
  - `verse` + `mystery_suspense_narrator`: ASR/sync passed after scoring fix, but schema-3 listening QA failed with worst-sample overall around `9.4`; not uploaded.
  - `marin` + `mystery_suspense_narrator`: regenerated full audio, estimated spend `$0.1723`; ASR/sync score `9.9219`, but listening QA failed with aggregate `overall_listening_score=8.4`, `naturalness_score=8.5`, `emotional_expression_score=8.2`, `punctuation_pause_score=8.0`, `pacing_score=8.3`, `confidence_score=0.9`.
- Publish gate outcome:
  - Upload/checksum: not run.
  - Metadata approval: not run.
  - Browser gate: not run.
  - Production publish: not attempted.
  - Reason: schema-3 listening QA failed; current `marin` ASR ending check is also not clean.
- Tests run:
  - `python3 -m py_compile internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/test_asr_transcript_similarity.py internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - `python3 internal/audiobook_lab/scripts/test_asr_transcript_similarity.py`
  - `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`
  - `git diff --check -- internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/factory_hooks/tts_hook.py internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/test_asr_transcript_similarity.py`
- Merge hygiene:
  - Keep reusable source changes: `asr_sync_hook.py`, `tts_hook.py`, `release_catalog_factory.py`, `test_asr_transcript_similarity.py`, and this report.
  - Do not commit generated release-gate outputs, generated MP3s/samples/sidecars, dashboards, logs, or signed URLs.
- Next safe target recommendation:
  - `sredni-vashtar` is the next smallest candidate from the latest broad content-size ranking among the provided English fallback list.
  - Use targeted English source-provenance repair and OpenAI listening QA; do not reuse mismatched local audio blindly.

## Targeted Second-Live Push - Sredni Vashtar - 2026-07-05

- Target: `sredni-vashtar`
- Result: not published.
- Current fully audiobook-live count remains `1`: `a-ghost-story`.
- Release plan: `internal/audiobook_lab/release_gate/sredni-vashtar_20260705T181723Z/sredni_vashtar_release_plan.json`
- Audio provenance report: `internal/audiobook_lab/release_gate/sredni-vashtar_20260705T181723Z/sredni_vashtar_audio_provenance_report.json`
- Terminal/retry report: `internal/audiobook_lab/release_gate/sredni-vashtar_20260705T195720Z/sredni_vashtar_terminal_or_retry_report.json`
- Source/content, rights metadata, and covers passed.
- Existing Cloudinary audio was rejected as a release shortcut after ASR/source validation failed (`transcript_match_score=1.4099`, first/last span mismatch).
- Factory repair completed:
  - Reused existing/local audio that fails ASR source-provenance now routes back to TTS instead of being reused repeatedly.
  - TTS hook now writes an audio provenance report and bypasses the failed reused asset before paid OpenAI regeneration.
  - ASR boundary checks now use fuzzy token-span matching so a single ASR proper-name spelling variant does not falsely fail an otherwise complete ending.
  - ASR stage reruns now clear stale ASR/listening blockers before adding current evidence.
- TTS attempt:
  - `gpt-4o-mini-tts`, voice `verse`, profile `classic_literary_narrator`.
  - Estimated TTS spend: `$0.1556`.
  - Audio regenerated from clean manuscript; no fallback TTS used.
- Gate outcome:
  - ASR transcript/sync score: `9.7997`.
  - Real timestamp method: `openai_verbose_json_word_timestamps`.
  - `auto_estimated_sync=false`, VTT drift `0`.
  - Schema-3 listening QA failed: `overall_listening_score=9.4`, `naturalness_score=9.5`, `pronunciation_score=9.6`, `emotional_expression_score=9.4`, `punctuation_pause_score=9.3`, `pacing_score=9.2`, `continuity_score=9.5`, confidence `0.95`.
  - Upload/checksum, metadata approval, and browser gates were correctly not run.
- Publish gate outcome:
  - Production publish was not attempted.
  - Reason: schema-3 listening QA remains below the strict `9.7` release threshold.
- Tests run:
  - `python3 -m py_compile internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/factory_hooks/tts_hook.py internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/test_asr_transcript_similarity.py`
  - `python3 internal/audiobook_lab/scripts/test_asr_transcript_similarity.py`
  - `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`
- Merge hygiene:
  - Keep reusable source changes: `asr_sync_hook.py`, `tts_hook.py`, `release_catalog_factory.py`, `test_asr_transcript_similarity.py`, and this report.
  - Do not commit generated release-gate outputs, generated MP3s/samples/sidecars, dashboards, logs, or signed URLs.
- Next target recommendation:
  - `the-gift-of-the-magi`, unless a targeted stronger voice/instruction repair strategy is approved for `sredni-vashtar`.
  - `sredni-vashtar` has been added to `internal/audiobook_lab/release_gate/terminal_blocker_exclusions.txt` to prevent blind reruns.

## Bengali TTS Provider Bakeoff - 2026-07-05

- Script added: `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py`
- Provider adapter added: `internal/audiobook_lab/scripts/providers/sarvam_tts_adapter.py`
- Result: no Bengali audiobook provider path is production-safe yet.
- Combined fast-path summary: `internal/audiobook_lab/release_gate/bengali_provider_fast_path_summary.json`
- OpenAI baseline report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T201833Z/bengali_tts_provider_bakeoff_report.json`
- Sarvam probe report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T204419Z/bengali_tts_provider_bakeoff_report.json`
- Google/Azure probe report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T204439Z/bengali_tts_provider_bakeoff_report.json`
- Azure diagnostic report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T204515Z/bengali_tts_provider_bakeoff_report.json`
- Global status: `internal/audiobook_lab/release_gate/bengali_provider_bakeoff_status.json`
- Providers detected without printing secrets:
  - OpenAI: detected and auditioned.
  - Google Cloud TTS: env detected, but voice listing failed because application-default credentials require reauthentication.
  - Azure Speech TTS: env detected, but synthesis failed with `AuthenticationFailure` / WebSocket 401 for the configured key-region pair.
  - Sarvam: key detected and adapter implemented, but the account returned `insufficient_quota_error` / no credits available before sample synthesis could complete.
  - Human/licensed import: not detected.
- Voices tested:
  - OpenAI: `marin`, `cedar`, `verse`, `coral`, `sage`, `alloy`.
  - Sarvam smoke: `aditya`, `ritu`, `ashutosh` from the current Bulbul v3-compatible speaker list.
  - Azure smoke: `bn-IN-TanishaaNeural`, plus earlier attempted Bengali neural voices.
- Best available audition: OpenAI `cedar`, `overall_listening_score=8.3`, `confidence_score=0.90`.
- Required release threshold: every schema-3 listening field `>=9.7` and confidence `>=0.95`.
- Decision: `EXTERNAL_ACTION_REQUIRED` for the native-provider fast path because Sarvam/Google/Azure are blocked by provider account/auth issues; OpenAI remains a below-threshold fallback baseline.
- No full Bengali pilot generation, upload, metadata approval, browser publish, or audiobook exposure was attempted.
- Estimated costs: Sarvam smoke `$0.0345`, Google/Azure smoke `$0.023`, OpenAI baseline `$0.5664`; actual cost was not available from provider telemetry.
- Tests run:
  - `python3 -m py_compile internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/factory_hooks/*.py`
  - `python3 -m py_compile internal/audiobook_lab/scripts/providers/*.py`
  - `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py`
  - `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`
- Merge hygiene:
  - Keep reusable source changes: `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py` and `internal/audiobook_lab/scripts/providers/sarvam_tts_adapter.py`.
  - Do not commit generated bakeoff samples, reports, dashboards, MP3s, logs, or signed URLs.

## Bengali Premium MVP Policy - 2026-07-06

- Policy implemented: `bengali_premium_mvp_v1`.
- Policy decision record: `internal/audiobook_lab/release_gate/bengali_premium_mvp_policy_decision.json`.
- Reason: universal schema-3 `9.7` listening threshold remains appropriate for English, but current Bengali provider evidence shows the best native Bengali automated voices can be premium/non-robotic around `9.3-9.5` while still failing a universal multilingual judge calibration.
- Scope: Bengali only. English remains on the universal schema-3 `9.7` gate.
- Hard gates not relaxed:
  - source/content/TOC integrity,
  - rights metadata,
  - cover QA,
  - fresh provider provenance,
  - no stale local audio,
  - no fallback/placeholder audio,
  - ASR/source match,
  - no missing/duplicated/reordered content,
  - measured/provider-derived sync or explicit audio-only-with-reader mode,
  - upload/checksum,
  - metadata approval,
  - browser playback,
  - empty unresolved blocker list.
- Regression coverage added:
  - Bengali MVP passes ratan-like `9.4` scores only for Bengali.
  - Bengali MVP fails if any fatal audio flag is true.
  - Bengali MVP fails if ASR/source hard gates fail.
  - Bengali MVP fails if fallback audio is used.
  - Bengali MVP does not apply to English.
  - Duplicate passage labels no longer falsely block a voice that passed every expected audition sample.
- Latest guarded Sarvam run:
  - Run folder: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260706T032542Z`.
  - Report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260706T032542Z/bengali_tts_provider_bakeoff_report.json`.
  - MVP quality report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260706T032542Z/bengali_mvp_quality_report.json`.
  - Pilot plan: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260706T032542Z/bengali_pilot_generation_plan.json`.
  - Result: audition path found under Bengali MVP, but no full Bengali pilot generated or published.
  - Best provider/voice: `sarvam/pooja`.
  - Raw aggregate listening score: `9.3`; confidence: `0.95`.
  - Fatal flags: false in the passing voice aggregate.
  - Selected pilot candidate: `book-ac5a71075e`.
  - Sync launch preference: `audio_only_with_reader`, `highlight_sync_enabled=false`, until Bengali highlight sync is separately proven reliable.
- Commands run:
  - Railway Sarvam MVP audition with `--policy bengali_premium_mvp_v1 --generate-full-pilot-if-policy-pass --allow-audio-only-with-reader --disable-fragile-highlight-sync`.
  - Local no-new-synthesis resume on the same run folder after fixing duplicate-passage aggregation.
  - `python3 -m py_compile internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py internal/audiobook_lab/scripts/providers/*.py internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`.
  - `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py`.
  - `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`.
  - `git diff --check -- internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/test_listening_qa_schema3.py`.
- Merge hygiene:
  - Keep reusable source changes: `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py`, `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`, `internal/audiobook_lab/scripts/test_listening_qa_schema3.py`, and this report.
  - Do not commit generated bakeoff WAV/MP3 samples, release-gate reports, dashboards, logs, or signed URLs.
- Next exact command:
  - Use the selected `sarvam/pooja` pilot plan to implement or run the guarded full-pilot generation path for `book-ac5a71075e`; do not publish until full-book ASR/source, sync mode, upload/checksum, metadata, and browser gates pass.

## Strict Bengali Provider Bakeoff Resume - 2026-07-06

- Run folder: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T205630Z`.
- Current task policy: universal schema-3 listening threshold remains strict at `9.7`; Bengali MVP policy was not used for this resume.
- Quota preflight: `PASS` in `openai_listening_qa_quota_probe.json`.
- Existing interrupted Sarvam assets preserved: `46` audio files / `23` canonical samples from the original run.
- Existing-sample judging completed: `20` existing sample slots reused; `18` had complete schema-3 judgments.
- Targeted second-pass polishing completed: `48` new short audition samples for near-pass Sarvam voices only (`ritu`, `priya`, `ashutosh`) across focused style/text-preparation variants.
- Full pilot generation: not run.
- Upload, metadata approval, browser gates, or publishing: not run.
- Best individual sample: `sarvam/ritu`, `warm_bengali_literary_storyteller`, `emotional`, `overall_listening_score=9.5`, `confidence_score=0.95`; still `BLOCKED` because it is below `9.7`.
- Final strict voice-level decision: `AUDIO_PROVIDER_QUALITY_LIMIT`; no provider/voice/style passed every required schema-3 9.7 field.
- Primary report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T205630Z/bengali_tts_provider_bakeoff_report.json`.
- Existing sample report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T205630Z/bengali_existing_sample_judging_report.json`.
- Provider limit report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260705T205630Z/bengali_audio_provider_limit_report.json`.
- Interrupted progress file updated to `RESUMED_COMPLETED`.
- Recommendation under strict policy: keep Bengali audiobooks reader-only/audio-hidden until a provider or approved human/licensed audio path can pass schema-3 9.7.
- Reusable source change kept: `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py` now counts resume-loaded sample hits as reused samples.

## Bengali Publishing Governor Pass - 2026-07-06

- Installed the missing permanent intelligence layer under `internal/earnalism_intelligence/`.
- Built Bengali catalog truth:
  - `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_catalog_truth.json`
  - `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_catalog_truth.csv`
- Discovered Bengali titles: `106`.
- Reader-live precheck: `31` titles have detail and reader routes returning `200` with local content/rights/covers precheck.
- Reader-only/audio-hidden recommended: `19`.
- Audio-decommission/reader-live recommended: `12`.
- Full title blocked with evidence: `75` because local source/control evidence is incomplete or not mapped to production reader status.
- Provider status: OpenAI listening-QA quota `PASS`; resumed Sarvam existing-sample judging did not pass universal schema-3 `9.7` (`best_provider=sarvam`, `best_voice=ritu`, `best_score=7.9`, `best_confidence=0.85`).
- No full Bengali audiobook generation, upload, metadata approval, browser publish, or audiobook exposure was run.
- No broad Bengali audiobook wave was run because the current factory lacks reader-only/audio-decommission production mutation support; running it now would retry known audio failures instead of safely advancing reader-only availability.

Generated Bengali reports:

- `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_reader_only_publish_report.json`
- `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_audio_decommission_report.json`
- `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_audiobook_candidate_report.json`
- `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_provider_status_report.json`
- `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_go_live_dashboard.json`

Validation:

- `python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py` - PASS
- `python3 -m py_compile internal/audiobook_lab/scripts/factory_hooks/*.py` - PASS
- `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py` - PASS
- `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py` - PASS
- `git diff --check` - PASS

## Achievement-Aware Cost Governor - 2026-07-07

- `git diff --check` PASS after activating the cost governor.
- No paid operations, provider calls, deployment calls, TTS, ASR, listening-QA, or production mutations were run.
- Duplicate Bengali production mutations were skipped because the latest integration dashboard already reports 31 reader-only approvals, 6 newly repaired approvals, 0 rights blockers, and hidden audiobook endpoints.
- Full visual/Lighthouse matrices were skipped because no source changed after the latest graphical-cover validation; current evidence remains partial with Lighthouse performance 90/LCP 3.6s.
- The dirty checkout is not merge-ready. Use a clean worktree from `origin/main` and copy only source/config/test/docs files explicitly.

## Performance Rescue - 2026-07-07

- Activated achievement-aware cost governor and froze Bengali reader-only, Sarvam provider-limit, graphical cover, visual smoke, and audio-safety wins.
- Root cause: Lighthouse LCP was held by the mobile hero image, then by automatic first-visit tour text and early idle prefetch/settings work.
- Fix: responsive compressed Dracula hero variants, mobile procedural cover face, lazy/delayed first-visit tour, delayed route prefetch/settings fetch, optimized bundled brand mark.
- Lighthouse: performance `90` -> `96`, LCP `3.6 s` -> `2.7 s`, total byte weight `Total size was 417 KiB` -> `Total size was 239 KiB`.
- Cover audit remains PASS: 164 covers, 0 typography-only covers.
- Visual smoke remains PASS. Audio safety remains PASS. Accessibility and SEO remain 100.
- No paid operations, provider calls, Bengali mutations, deployments, or broad catalog waves were run.

## Bengali Audiobook Campaign Activation - 2026-07-06T21:54:41Z

Source/state changes to keep:

- `AGENTS.md`
- `internal/earnalism_intelligence/bengali_audiobook_campaign_policy.md`
- `internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py`
- `internal/audiobook_lab/scripts/test_bengali_audiobook_campaign_controller.py`
- `internal/earnalism_intelligence/bengali_audiobook_campaign_state.json`
- `internal/earnalism_intelligence/bengali_audiobook_campaign_queue.json`
- `internal/earnalism_intelligence/bengali_audiobook_campaign_ledger.jsonl`
- `bengali_audiobook_31_campaign_queue.json`
- `bengali_audiobook_campaign_dashboard.json`
- `bengali_audiobook_next_actions.md`
- `next_best_codex_prompt.md`

Generated or unsafe artifacts to exclude:

- release gate run folders
- generated audio
- sidecars
- raw listening-QA outputs not intentionally summarized
- screenshots/traces
- build output
- provider credentials, signed URLs, and logs

Validation:

- Campaign controller compiled.
- Sarvam adapter and Bengali bakeoff scripts compiled.
- Campaign controller regression tests passed.
- Listening QA schema-3 regression test passed.
- No paid/provider/ASR/upload/metadata/production mutation calls were run.

## Bengali Audiobook 9.2 Rescue - 2026-07-06T21:48:08Z

- Policy: `bengali_audiobook_acceptance_v2_92`.
- Representative audition: PASS.
- Provider/model/voice/style: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- Representative score/confidence: 9.3 / 0.95.
- Fatal red flags: none for the passing arm.
- Pilot candidate: `book-2b9853ec52`.
- Full pilot generated: false.
- Production publish: false; ASR/sync/upload/metadata/browser gates not run.
- Reader-only/audio-hidden Bengali state remains protected.
- Report: `bengali_representative_audition_report.json`.

## Bengali Sarvam Full Pilot - 2026-07-07T04:13Z

Source changes to keep:

- `internal/audiobook_lab/scripts/factory_hooks/tts_hook.py`: guarded Sarvam full-pilot TTS hook and TTS-only Bengali frontmatter stripping.
- `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`: fail-closed transcription fallback when a model rejects `verbose_json`.
- `internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py`: offline regression coverage for approval gates, Bengali policy, frontmatter stripping, and ASR response-format fallback.

Generated or unsafe artifacts to exclude:

- `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T040427Z/`
- `internal/audiobook_lab/release_gate/catalog_20260707T040427Z/`
- generated MP3/WAV audio chunks
- ASR transcripts, sidecars, and raw gate evidence unless intentionally summarized
- provider credentials, logs, caches, and signed URLs

Validation:

- Full-pilot TTS generated one hidden pilot audio asset only.
- ASR/manuscript gate failed: score `7.0199 < 9.7`, first/last boundary checks failed, no word/segment timestamps returned.
- Upload, metadata approval, endpoint exposure, and browser gates were not run.
- `python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/factory_hooks/tts_hook.py internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py internal/audiobook_lab/scripts/providers/sarvam_tts_adapter.py` passed.
- `python3 internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py` passed.
- `python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py` passed.
- `python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py` passed.
- `git diff --check` passed.

Merge safety:

- Do not stage release-gate run folders or generated audio.
- Do not publish the generated Bengali pilot.
- A repaired second pilot requires explicit owner approval because the one-pilot guard has already been consumed.

## Visual Brand System Hardening - 2026-07-07T04:54:30+00:00

- Cover inventory: 164 active/public covers audited; 0 typography-only covers found; 0 remaining in customer UI.
- Graphical coverage: 106 deterministic runtime graphical fallbacks; 164 effective front/back cover pairs.
- Typography: home/library/book-card/book-detail scales reduced for calmer premium hierarchy without shrinking below readable sizes.
- Validation: Lighthouse performance 96, LCP 2641.1ms, accessibility 100, SEO 100; visual smoke PASS with 72/72 checks; audio safety PASS 4/4.
- Preview: protected Vercel preview remains blocked by login shell without `VERCEL_AUTOMATION_BYPASS_SECRET` or a shareable preview link; local same-origin proxy remains canonical evidence for this pass.

## 2026-07-07T05:06:15.040184+00:00 Bengali Pilot ASR Forensics
- `book-2b9853ec52` full pilot remains hidden and unpublished.
- ASR score `7.0199`; no word/segment timestamps; upload/checksum, metadata, and browser gates were not run.
- Forensics diagnosis: current TTS input contains disallowed frontmatter/source metadata; `tts_by_construction_verified=false`.
- Reports: `book_2b9853ec52_bengali_asr_forensics_plan.json`, `book_2b9853ec52_tts_source_provenance_report.json`, `book_2b9853ec52_bengali_asr_provider_comparison.json`, `book_2b9853ec52_bengali_pilot_closeout.json`.

## Bengali Pilot Clean Repair - 2026-07-07T05:21:38.249911+00:00
- Source changes: `internal/audiobook_lab/scripts/factory_hooks/tts_hook.py`, `internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py`.
- Generated evidence reports are local run artifacts and should not be staged unless intentionally promoted.
- No audio upload, metadata approval, browser publish, or production mutation was run.

## Bengali Pilot Audio QA PASS - 2026-07-07T05:54:36Z

- Source changes to keep: `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`, `internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py`, and concise root summary/intelligence reports if intentionally promoted.
- Generated artifacts to exclude: `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T053510Z/`, generated MP3/WAV chunks, listening samples, ASR transcripts, sidecars, screenshots, logs, caches, signed URLs, and credentials.
- Current gate state: TTS provenance PASS, measured paragraph/stanza sync PASS, listening QA PASS, upload/metadata/browser NOT RUN.
- No production upload, metadata mutation, endpoint exposure, or browser publish was run by this report update.
- Merge hygiene: use explicit `git add` paths only; do not stage release_gate run folders or generated audio/sidecars.

## Bengali Pilot Final Gate Blocked - 2026-07-07T07:27:10Z

- Source changes to keep: `internal/audiobook_lab/scripts/factory_hooks/metadata_hook.py`, `internal/audiobook_lab/scripts/release_catalog_factory.py`, `internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py`, `internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py`, and concise intelligence/report updates if intentionally promoted.
- Generated artifacts to exclude: `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T053510Z/`, `internal/audiobook_lab/release_gate/catalog_20260707T053510Z/`, uploaded audio/sidecars, transcripts, browser traces, logs, caches, signed URLs, and credentials.
- Current gate state: upload/checksum PASS, metadata API PASS, endpoint verification BLOCKED at `404`, browser NOT RUN, published `false`.
- Do not rerun TTS, ASR, sync, listening QA, provider bakeoff, or canary waves for this blocker.
- Resume only after backend deploy/restart or controlled-launch/audio-route refresh, with TTS/ASR/upload workers disabled.

## Bengali Pilot Endpoint Materialization - 2026-07-07T07:43:30Z

- Reports to keep if intentionally promoted: `book_2b9853ec52_endpoint_materialization_plan.json`, `book_2b9853ec52_endpoint_404_diagnosis.json`, `book_2b9853ec52_endpoint_404_closeout.json`.
- Generated artifacts to exclude remain unchanged: release_gate run folders, uploaded audio/sidecars, raw logs, caches, screenshots/traces, signed URLs, and secrets.
- Do not run `railway up` from this dirty workspace; it currently has broad unrelated tracked and untracked changes.
- Clean deploy scope should be limited to backend controlled-launch materialization source/data and any regression tests needed to prove unapproved audio remains hidden.

## Homepage Figma Alignment Cleanup - 2026-07-07T10:45:00Z

Source files changed for this pass:

- `frontend/src/pages/Home.jsx`
- `frontend/src/components/ComingSoonBoard.jsx`
- `frontend/src/components/Header.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/components/Footer.jsx`
- `frontend/src/components/FirstVisitSiteTour.jsx`
- `frontend/src/index.css`
- `frontend/public/index.html`
- `frontend/scripts/generate-static-seo-snapshots.mjs`

Reports/evidence intentionally written:

- `homepage_figma_live_gap_report.json`
- `homepage_typography_figma_alignment_report.json`
- `earnalism_luxury_ux_index.json`
- `ux_rebirth_evidence.md`
- `frontend_luxury_sprint_report.md`
- `repo_cleanup_report.md`
- `sprint_go_live_dashboard.md`
- `internal/earnalism_intelligence/decision_ledger.jsonl`
- `internal/earnalism_intelligence/sprint_learnings.md`

Generated files to exclude from staging unless deliberately promoted:

- `frontend/build/`
- `frontend/public/sitemap.xml`
- `book_cover_audit_report.json`
- `book_cover_audit_report.csv`
- `book_cover_visual_inventory.json`
- `book_cover_visual_inventory.csv`
- `ux_visual_regression_report.json`
- `/tmp/earnalism-homepage-figma-lighthouse.json`
- screenshots/traces/logs/caches/release_gate/audio/sidecars/signed URLs/secrets

Validation:

- `npm ci --prefix frontend` PASS with existing peer/deprecation/audit warnings.
- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` PASS 4/4.
- `REACT_APP_BACKEND_URL=/api npm --prefix frontend run build` PASS.
- `node frontend/scripts/audit-book-covers.mjs` PASS 164/0 typographic-only.
- `VISUAL_SMOKE_BASE_URL=http://127.0.0.1:4173 node frontend/scripts/visual-luxury-smoke.mjs` PASS 72/72.
- Lighthouse local production-equivalent PASS: performance 98, accessibility 100, SEO 100.
- `git diff --check` PASS.
## 2026-07-07 Figma UX Source Scope

Intended source/report changes from this pass:

- `frontend/src/components/Header.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/components/ComingSoonBoard.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/index.css`
- `frontend/public/index.html`
- `frontend/src/lib/funnelAnalytics.js`
- `figma_home_library_reader_master_plan.json`
- `figma_earnalism_design_tokens.json`
- `figma_component_inventory.md`
- `figma_home_screen_spec.md`
- `figma_library_screen_spec.md`
- `figma_reader_audiobook_screen_spec.md`
- `figma_interaction_spec.md`
- `figma_responsive_spec.md`
- `figma_vs_live_gap_report.json`
- `figma_typography_system_report.json`
- `figma_10_ux_scorecard.json`

Generated or validation side effects to exclude from commit unless separately reviewed:

- `frontend/build/`
- `frontend/public/sitemap.xml`
- `book_cover_audit_report.json`
- `book_cover_audit_report.csv`
- `ux_visual_regression_report.json`
- screenshots, traces, caches, release_gate outputs, audio, sidecars, signed URLs, and secrets.

Validation summary: audioReleaseSafety PASS, build PASS, cover audit PASS 164/0, visual smoke PASS 72/72, Lighthouse performance 97/accessibility 100/SEO 100, git diff --check PASS.

## 2026-07-07 Parallel Go-Live Acceleration Scope

New coordination/report files intentionally created:

- `parallel_go_live_sprint_dashboard.json`
- `parallel_go_live_sprint_dashboard.md`
- `bengali_next_3_canary_preflight.json`
- `internal/earnalism_intelligence/locks/production_metadata.lock`
- `internal/earnalism_intelligence/locks/backend_deploy.lock`
- `internal/earnalism_intelligence/locks/paid_tts.lock`

Existing intelligence/report files intentionally updated:

- `internal/earnalism_intelligence/decision_ledger.jsonl`
- `internal/earnalism_intelligence/sprint_learnings.md`
- `sprint_go_live_dashboard.md`
- `repo_cleanup_report.md`

Generated or validation side effects to exclude:

- `frontend/build/`
- `frontend/public/sitemap.xml` unless separately reviewed.
- `internal/audiobook_lab/release_gate/` run outputs.
- Generated audio, sidecars, logs, browser traces, screenshots, caches, signed URLs, and secrets.

Merge hygiene note: the main workspace remains dirty with unrelated catalog/content/frontend changes. Do not stage from this workspace without a source-only promotion pass.

## 2026-07-07 Bengali Audiobook Pilot Live Scope

Source changes intentionally made during final browser-gate closure:

- `frontend/src/pages/Reader.jsx` and `frontend/src/index.css` in clean worktree `/private/tmp/earnalism-frontend-prod-main`, committed as `bbf5c17f06643c12c52a4aff4062b25da0f0cc6b`.
- `internal/audiobook_lab/scripts/factory_hooks/browser_hook.py` to fail closed while waiting for real audio metadata without CSP-blocked eval.
- `internal/audiobook_lab/scripts/release_catalog_factory.py` to clear stale blockers from resumed PASS stages and refresh published go-live evidence.

Reports intentionally created/updated:

- `frontend_bengali_audio_ship_source_report.json`
- `frontend_bengali_audio_production_deploy_verification.json`
- `book_2b9853ec52_goliveevidence.json`
- `bengali_audiobook_campaign_dashboard.json`
- `sprint_go_live_dashboard.md`
- `internal/earnalism_intelligence/decision_ledger.jsonl`
- `internal/earnalism_intelligence/provider_performance_memory.json`
- `internal/earnalism_intelligence/title_decision_history.json`
- `internal/earnalism_intelligence/sprint_learnings.md`

Generated artifacts excluded from source promotion:

- `frontend/build/`
- `internal/audiobook_lab/release_gate/` audio, sidecars, logs, browser traces, and run outputs.
- Signed URLs, secrets, caches, screenshots, and transient Vercel/Railway logs.

Validation summary: production endpoint/browser PASS, audio safety previously PASS 4/4, factory stop-guard regression PASS, py_compile PASS, and targeted `git diff --check` PASS for touched factory/browser hook source.

## 2026-07-07 Repo Hygiene Clean Integration

Created a clean source-only integration worktree from `origin/main`:

- `/private/tmp/earnalism-source-only-clean-integration`
- Branch: `sprint/source-only-clean-integration`

Inventory and preservation reports:

- `repo_hygiene_inventory.json`
- `repo_hygiene_inventory.md`
- `local_evidence_preservation_manifest.json`
- `gitignore_hygiene_report.json`
- `source_promotion_plan.json`
- `clean_integration_promotion_report.json`
- `dirty_workspace_cleanup_dryrun_report.md`

Generated artifacts and local evidence intentionally excluded from source promotion:

- `internal/audiobook_lab/release_gate/` run folders, generated audio, sidecars, logs, browser traces, and rollback evidence.
- `frontend/build/`
- `frontend/public/sitemap.xml`
- generated cover/visual smoke outputs.
- screenshots, traces/videos, logs, caches, signed URLs, and secrets.
- imported book/content noise under `content/books/`.

Owner-review items remaining in the original workspace:

- `frontend/package-lock.json`: excluded because it broke `npm ci` against clean `origin/main` by dropping Playwright lock entries while `package.json` requires Playwright.
- `frontend/public/sitemap.xml`: generated by frontend build and restored in the clean integration worktree after validation.

Validation summary in clean integration worktree: release factory py_compile PASS, factory hook py_compile PASS, stop-guard tests PASS, listening QA schema PASS, backend route tests PASS 8/8, `npm ci` PASS, audioReleaseSafety PASS 4/4, frontend build PASS, cover audit PASS with 0 typographic-only covers, visual smoke PASS with Playwright browser execution 72/72, and `git diff --check` PASS.

Operating rule: future deploys and production mutations must run from clean source-only worktrees. The original workspace may retain local evidence, rollback payloads, and imported content inputs, but it must not be used for deploy unless `git status --short` is source-only and intentionally staged.
