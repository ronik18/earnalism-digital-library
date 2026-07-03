# READINESS_DASHBOARD

Run timestamp: 2026-07-03T06:35:56+0000
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
- **bn-031** (ben) | Words: 0 | Duration: 0.00s | TTS: failed | Sync: auto-estimated | Warnings: Filled missing metadata 'title' in content/books/bn-031/book.json from manifest, Filled missing metadata 'author' in content/books/bn-031/book.json from manifest, Missing optional language metadata in content/books/bn-031/book.json
  - Render sample: -
  - Text sample: -
  - Highlights: data/controlled_publications/bn-031/highlight_sync.json

## Git Diff Summary
- scripts/audiobook_production_pipeline.py

## Exact Command
`scripts/audiobook_production_pipeline.py --manifest internal/audiobook_lab/generated_candidate_restoration/restoration_manifest_20260702.json --title-limit 2`
