# READINESS_DASHBOARD

Run timestamp: 2026-07-03T06:42:13+0000
Pipeline command: scripts/audiobook_production_pipeline.py --manifest internal/audiobook_lab/generated_candidate_restoration/restoration_manifest_20260702.json --title-limit 2
Total source titles in manifest scope: 2
Total unique titles: 152
Duplicates removed: 25
Skipped titles: 0
Titles completed: 2
Completed release-qualified: 0
Blocked by content sanitation: 2
Blocked by audio quality: 2
Titles using OpenAI TTS: 0
Titles using fallback audio: 0
Titles with auto-estimated sync: 2
Estimated retry count: 2
Estimated total API cost: $0.0000

## Title Gate Summary
| Slug | Language | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Gate 6 | Cover | Overall Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bn-027 | ben | GATE_0_WARN_MISSING_COVER | GATE_1_PASS | GATE_2_FAIL | GATE_3_AUTO_ESTIMATED | GATE_4_FAIL | - |  | MISSING | BLOCKED |
| bn-031 | ben | GATE_0_WARN_MISSING_COVER | GATE_1_PASS | GATE_2_FAIL | GATE_3_AUTO_ESTIMATED | GATE_4_FAIL | - |  | MISSING | BLOCKED |

## Ready for Human Sign-Off
- Count: 0

## Needs Manual Attention
- **bn-027**: TTS generation failed on chapter 1 paragraph 1: OpenAI API call failed: Error code: 400 - {'error': {'message': "[{'type': 'string_too_long', 'loc': ('body', 'input'), 'msg': 'String should have at most 4096 characters', 'ctx': {'max_length': 4096}}]", 'type': 'invalid_request_error', 'param': None, 'code': None}}, Gate 3 continuing after Gate 2 outcome for fallback sync estimation, Missing reader_manifest.json in data/controlled_publications, Enhanced MP3 missing, Gate 5 blocked: requires Gates 0-4 pass, Gate 6 blocked: QA sheet not generated
  - Fix instruction: Re-run Gate 2 and ensure enhanced MP3 is produced.
  - Fix instruction: Regenerate reader_manifest.json in controlled_publications/{slug}/ and rerun.
  - Fix instruction: Review gate failure details and rerun after remediation.
- **bn-031**: TTS generation failed on chapter 1 paragraph 1: OpenAI API call failed: Error code: 400 - {'error': {'message': "[{'type': 'string_too_long', 'loc': ('body', 'input'), 'msg': 'String should have at most 4096 characters', 'ctx': {'max_length': 4096}}]", 'type': 'invalid_request_error', 'param': None, 'code': None}}, Gate 3 continuing after Gate 2 outcome for fallback sync estimation, Missing reader_manifest.json in data/controlled_publications, Enhanced MP3 missing, Gate 5 blocked: requires Gates 0-4 pass, Gate 6 blocked: QA sheet not generated
  - Fix instruction: Re-run Gate 2 and ensure enhanced MP3 is produced.
  - Fix instruction: Regenerate reader_manifest.json in controlled_publications/{slug}/ and rerun.
  - Fix instruction: Review gate failure details and rerun after remediation.

## Missing Covers
- bn-027
  - Fix instruction: populate `coverAssets` in `content/books/bn-027/book.json`
- bn-031
  - Fix instruction: populate `coverAssets` in `content/books/bn-031/book.json`

## Sample Inspection (begin/middle/end)
- **bn-027** (ben) | Words: 0 | Duration: 0.00s | TTS: failed | Sync: auto-estimated | Warnings: Missing optional language metadata in content/books/bn-027/book.json
  - Render sample: -
  - Text sample: -
  - Highlights: data/controlled_publications/bn-027/highlight_sync.json
- **bn-031** (ben) | Words: 0 | Duration: 0.00s | TTS: failed | Sync: auto-estimated | Warnings: Missing optional language metadata in content/books/bn-031/book.json
  - Render sample: -
  - Text sample: -
  - Highlights: data/controlled_publications/bn-031/highlight_sync.json

## Git Diff Summary
- content/books/bn-031/book.json
- data/controlled_publications/bn-027/highlight_sync.json
- data/controlled_publications/bn-031/highlight_sync.json
- internal/audiobook_lab/release_gate/READINESS_DASHBOARD.md
- internal/audiobook_lab/release_gate/approved_for_live.json
- internal/audiobook_lab/release_gate/release_gate_status.json
- internal/audiobook_lab/release_gate/sync_manifests/a-jury-of-her-peers/a-jury-of-her-peers_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/a-mystery-of-heroism/a-mystery-of-heroism_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/a-retrieved-reformation/a-retrieved-reformation_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/alices-adventures-in-wonderland/alices-adventures-in-wonderland_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/berenice/berenice_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bharat-at-the-crossroads/bharat-at-the-crossroads_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-027/bn-027_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-031/bn-031_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-035/bn-035_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-036/bn-036_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-041/bn-041_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-059/bn-059_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-060/bn-060_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/bn-066/bn-066_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-0986aeb7e3/book-0986aeb7e3_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-0deb35c750/book-0deb35c750_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-0fbdaa730e/book-0fbdaa730e_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-1090573dff/book-1090573dff_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-2b9853ec52/book-2b9853ec52_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-2ddbed8293/book-2ddbed8293_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-2e468c4990/book-2e468c4990_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-4968248842/book-4968248842_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-4b944e64fa/book-4b944e64fa_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-5461971092/book-5461971092_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-5704b31005/book-5704b31005_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-5aedda79fe/book-5aedda79fe_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-63afd5e9be/book-63afd5e9be_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-754da4eab8/book-754da4eab8_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-827fdc7aee/book-827fdc7aee_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-88ded9b47c/book-88ded9b47c_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-95624627d5/book-95624627d5_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-9a7f771921/book-9a7f771921_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-a23625bf36/book-a23625bf36_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-a4a369483f/book-a4a369483f_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-a74c1a1451/book-a74c1a1451_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-ac5a71075e/book-ac5a71075e_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-b9d47814a8/book-b9d47814a8_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-bfc51280b3/book-bfc51280b3_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-c307a57868/book-c307a57868_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-c7f3ce526c/book-c7f3ce526c_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-c85323409f/book-c85323409f_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-d19e96859f/book-d19e96859f_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-d2fe532e1c/book-d2fe532e1c_fallback.json
- internal/audiobook_lab/release_gate/sync_manifests/book-edfcf810c5/book-edfcf810c5_fallback.json

## Exact Command
`scripts/audiobook_production_pipeline.py --manifest internal/audiobook_lab/generated_candidate_restoration/restoration_manifest_20260702.json --title-limit 2`
