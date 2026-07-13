# Sprint 1 Parallel Execution Reconciliation Log

Completed paid-checkpoint cutoff: `2026-07-12T22:08:44Z`

Prior reconciliation cutoff: `2026-07-12T21:25:46Z` at `$8.33828`

## Scope

- Reconciled repository evidence only.
- Edited only `sprint1_parallel_execution_board.json`, `sprint1_parallel_execution_log.md`, and `sprint1_budget_ledger.json`.
- No provider call, lock inspection/change, audio operation, code change, matrix change, release-gate change, publication, upload, or deployment was performed by this reconciliation.

## Coordinator Checkpoint

- Branch: `codex/sprint1-paid-execution` at `b76f1e313299e4920eb8f732cbcb4dd8e8ee7fd5`.
- Completed conservative estimated spend: `$9.75400 / $175.00000`.
- Completed-checkpoint budget remaining: `$165.24600`.
- Actual provider billing: `UNKNOWN_NOT_REPORTED_BY_PROVIDERS`.
- Estimate boundary: `$9.75400` is the latest completed serialized paid-stage checkpoint, not invoice truth.
- Paid calls remain serialized at one bounded stage at a time. This reconciliation authorizes no paid stage.

## Assigned Lanes

| Lane | Assignment | State |
| --- | --- | --- |
| 0 | Coordinator / budget / serialization | `COMPLETED_CHECKPOINT_RECONCILED_PLATEAUS_HELD_D19_ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED` |
| 1 | `book-2b9853ec52`, `a-ghost-story` | `TWO_APPROVED_AUDIOBOOKS_MONITOR_ONLY` |
| 2 | D19, Muchiram, F5 | `D19_ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED_PRIVATE_TTS_PASS; MUCHIRAM_AND_F5_AUTOMATED_PLATEAU` |
| 3 | Sredni, Gift, Tell-Tale | `BOUNDED_AUTOMATED_TTS_PLATEAUS; AUDIO_HIDDEN` |
| 4 | Medium/long English | `NO_NEW_PAID_ASSIGNMENT` |
| 5 | Bengali long/repair | `NO_NEW_PAID_ASSIGNMENT` |
| 6 | Release-truth validation | `NO_RELEASE_GATE_OR_PUBLICATION_MUTATION` |

## Reconciled Decisions

### Approved Public Audio

- `book-2b9853ec52` remains `PUBLIC_AUDIO_APPROVED`; its release evidence records listening `9.4`, confidence `0.95`, measured paragraph/stanza sync, and passed endpoint/browser gates.
- `a-ghost-story` remains `YES_PLUS_YES_PRODUCTION_VALIDATED`; its release evidence records ASR/source `9.88`, six listening samples at `9.4-9.5`, confidence `0.95`, and production HTTP `206`.
- Exact blocker for both titles: `NONE`. Their commands are monitor-only checks.

### D19 Private TTS Pass, ASR Gate Fail

- Private Google TTS passed; sync is measured paragraph/stanza, not estimated; all six listening samples scored `9.4` at confidence `0.95`; fatal flags are empty.
- Raw audio-derived ASR/source is `0.6838`, below the global `>=9.7` release gate.
- The recorded `10.0` source value is a static TTS-source provenance audit and cannot substitute for the required audio-derived ASR result.
- The private candidate hash is `d8ccbdda0528ef9b0620638e944b12f5b5ed41d90cdbb0a5a99587fd4a340271`.
- Estimated title total is `$0.4975`; actual provider billing is `NOT_REPORTED`.
- State: `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED_PRIVATE_TTS_PASS`; D19 is not release-ready.
- Publication was not performed. Upload, metadata, endpoint, browser, and packet work remain downstream and must not start until the global ASR gate passes.

The bounded Google `latest_long`/`bn-IN` arm was unsupported, and OpenAI `gpt-4o-transcribe`/`bn` peaked at `6.7606`. Automated ASR arms are exhausted; next action is non-paid normalization repair and human alignment review. No TTS regeneration, upload, metadata mutation, release mutation, or publication is authorized.

### Muchiram Plateau

- Full-book Google QA bottomed at `7.8`, confidence `0.85`, with robotic texture, mechanical cadence, and list-reading rhythm.
- The targeted Achird repair bottomed at `7.4`; the final slower Aoede repair bottomed at `7.8`, confidence `0.85`, with the same fatal-flag family.
- State: `AUTOMATED_TTS_PLATEAU_HUMAN_OR_LICENSED_PATH_REQUIRED`.
- Exact blocker: repeated score/confidence failure plus persistent fatal flags after materially different bounded settings.
- Automated Google retry is not authorized.

Next non-provider handoff command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "from pathlib import Path; from internal.audiobook_lab.scripts.bengali_audiobook_campaign_controller import create_human_narration_packet; print(create_human_narration_packet('muchiram-gurer-jibanchorit', Path('internal/audiobook_lab/sprint1_publication/human_narration_packets/muchiram-gurer-jibanchorit')))"
```

### F5 Cross-Provider Plateau

- Google Aoede and Sarvam Pooja both bottomed at `7.8`, confidence `0.85`, on the punctuation-heavy representative passage.
- Google also recorded robotic texture and mechanical cadence fatal flags.
- State: `CROSS_PROVIDER_TTS_PLATEAU_HUMAN_OR_LICENSED_PATH_REQUIRED`.
- Exact blocker: the same difficult passage failed both bounded provider paths below the Bengali `9.2`/`0.90` gate.
- Further automated Google or Sarvam retry is not authorized.

Next non-provider handoff command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "from pathlib import Path; from internal.audiobook_lab.scripts.bengali_audiobook_campaign_controller import create_human_narration_packet; print(create_human_narration_packet('book-f5d593e1f4', Path('internal/audiobook_lab/sprint1_publication/human_narration_packets/book-f5d593e1f4')))"
```

### Sredni Two-Voice Plateau

- Studio-C scored `8.4`, `9.4`, `7.3`, and `8.4`; dialogue/risk had confidence `0.80` plus `mechanical_cadence_detected` and `robotic_texture_detected`.
- Achird scored `9.4`, `9.4`, `8.5`, and `9.4`; confidence passed and fatal flags were empty, but dialogue/risk remained below the `9.4` all-sample gate.
- State: `TWO_VOICE_AUTOMATED_TTS_PLATEAU_HUMAN_OR_LICENSED_PATH_REQUIRED`.
- Studio-C and Achird must not be repeated for the same text/settings fingerprints.

### Gift Three-Attempt Plateau

- Isolated Studio-C scored `9.5`, `9.4`, `8.5`, and `9.4`.
- Isolated Aoede scored `9.4`, `9.4`, `7.2`, and `9.5`; dialogue/risk carried mechanical and robotic fatal flags.
- Contextual Studio-C scored `9.5`, `9.4`, `8.3`, and `9.5`; the expanded risk passage remained below gate.
- State: `THREE_ATTEMPT_AUTOMATED_TTS_PLATEAU_HUMAN_OR_LICENSED_PATH_REQUIRED`.
- None of the three Google attempts may be repeated.

### Tell-Tale Two-Rate Plateau

- Contextual Studio-C at rate `0.88` scored `9.4`, `8.5`, `9.4`, and `8.8`.
- Slower contextual Studio-C at rate `0.82` scored `9.5`, `8.4`, `9.4`, and `9.6`; slowing worsened the failed middle sample.
- State: `TWO_RATE_CONTEXTUAL_TTS_PLATEAU_HUMAN_OR_LICENSED_PATH_REQUIRED`.
- Neither contextual Studio-C attempt may be repeated.

## Exact Reconciled Chain

| Stage | Prior | Stage estimate/cap | Cumulative | Result |
| --- | ---: | ---: | ---: | --- |
| Sredni Achird TTS | `$8.33828` | `$0.02788` | `$8.36616` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Sredni Achird LQA | `$8.36616` | `$0.20000` | `$8.56616` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| Gift Studio-C isolated TTS | `$8.56616` | `$0.02282` | `$8.58898` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Gift Studio-C isolated LQA | `$8.58898` | `$0.20000` | `$8.78898` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| Gift Aoede isolated TTS | `$8.78898` | `$0.02282` | `$8.81180` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Gift Aoede isolated LQA | `$8.81180` | `$0.20000` | `$9.01180` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| Gift Studio-C contextual TTS | `$9.01180` | `$0.02776` | `$9.03956` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Gift Studio-C contextual LQA | `$9.03956` | `$0.20000` | `$9.23956` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| Tell-Tale Studio-C contextual TTS | `$9.23956` | `$0.02302` | `$9.26258` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Tell-Tale Studio-C contextual LQA | `$9.26258` | `$0.20000` | `$9.46258` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| Tell-Tale Studio-C slow contextual TTS | `$9.46258` | `$0.02302` | `$9.48560` | `AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED` |
| Tell-Tale Studio-C slow contextual LQA | `$9.48560` | `$0.20000` | `$9.68560` | `SUBPROCESS_FAILED_QUALITY_GATE` |
| D19 Google latest_long / bn-IN ASR calibration | `$9.68560` | `$0.03420` | `$9.71980` | `UNSUPPORTED_MODEL_FOR_BN_IN` |
| D19 OpenAI gpt-4o-transcribe / bn ASR calibration | `$9.71980` | `$0.03420` | `$9.75400` | `BELOW_THRESHOLD_BEST_6.7606` |

All six private TTS manifests and all six listening-QA wrappers report the paid lock restored byte-for-byte at SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`. Actual provider billing is `NOT_REPORTED`. Every run remained private, with no upload, release mutation, public audio approval, or publication.

## Serialized Paid-Call Rule

1. Assign exactly one title and one bounded paid stage.
2. Reconcile the latest completed or accepted prior estimate before adding the next estimate.
3. Require all explicit approvals and sprint, title, provider, ASR, and listening-QA caps.
4. Use the existing paid runner and existing lock; restore the lock byte-for-byte.
5. Reject duplicate failed fingerprints and all automated retries for Muchiram, F5, Sredni, Gift, and Tell-Tale plateaued paths.
6. Record provider-call status, estimate checkpoint, actual billing status, and release-mutation status before another paid stage starts.

## Next Serialized Action

D19 exhausted the supported bounded ASR arms without reaching `9.7`. It must not regenerate TTS, repeat listening QA, or retry the recorded fingerprints. Non-paid normalization repair and human alignment review are next; upload/release work remains blocked until audio-derived ASR/source reaches at least `9.7`.

## Final State

- Approved public audiobooks: `book-2b9853ec52`, `a-ghost-story`.
- D19: private TTS/listening/measured-sync passed, but raw ASR/source `0.6838 < 9.7`; `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED_PRIVATE_TTS_PASS`; not release-ready and public audio remains hidden.
- Muchiram: automated TTS plateau; human narration or licensed import required.
- F5: cross-provider automated TTS plateau; human narration or licensed import required.
- Sredni: Studio-C/Achird automated plateau; human narration or licensed import required.
- Gift: three-attempt automated plateau; human narration or licensed import required.
- Tell-Tale: two-rate contextual automated plateau; human narration or licensed import required.
- New publications or public audio approvals at this checkpoint: `0`.
- Paid queue: empty.
- Actual billing: unknown.

Next exact command:

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_parallel_execution_board.json >/dev/null && python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_budget_ledger.json >/dev/null && jq -e '.accounting.cumulative_conservative_estimated_spend_usd == 9.754 and .accounting.actual_spend_usd == null and .accounting.budget_remaining_after_estimated_spend_usd == 165.246' internal/audiobook_lab/sprint1_publication/sprint1_budget_ledger.json >/dev/null && git diff --check
```

## 2026-07-13 Parallel Acceleration Checkpoint

- Coordinator worktree: clean `origin/main` commit `3709321` on `codex/sprint1-acceleration-evidence`.
- Agents: six read-only lanes; paid calls and release mutations remained coordinator-only.
- Runtime caps: owner-supplied values were passed inline because the parent shell did not persist exports.
- Credentials: Sarvam, OpenAI, Google credential file, and Google project were set; `google.auth.default()` resolved successfully.
- Serialized title: `dsires-baby`, the first untouched short English candidate after respecting prior attempt memory.
- Preflight: rights/sanitation/source binding passed; four Studio-C passages; `$0.03616` bounded estimate.
- Execute result: provider DNS unavailable before synthesis; zero synthesis calls, no audio, no listening QA, no release mutation, and zero booked spend.
- Lock: restored byte-for-byte to the authoritative closed hash.
- Release truth: 32 public readers, two approved public audiobooks, 30 audio-hidden titles.
- Next serialized action: retry the same dsires fingerprint from a network-enabled shell; do not advance to full TTS until all representative samples pass.

## D19 Tracked-Artifact Release-Truth Repair

The approved-audio guard found stale D19 `public_book.json` and `approval_evidence.json` fields that contradicted its disabled reader manifest. Both controlled-publication mirrors are now prepared fail-closed: reader access remains live; audio flags, provider, slug, and asset objects are empty; approval is `PUBLIC_AUDIO_RELEASE_NOT_APPROVED`; and packet checksums match. Eleven unique audio URLs were removed from each mirror. Focused backend release-truth tests pass `35/35`. This is a local source/test repair pending commit, PR, merge, and normal deployment; it does not approve or publish D19 audio.
