# READINESS_DASHBOARD

Run timestamp: 2026-07-03T06:43:17+0000
Pipeline command: scripts/audiobook_production_pipeline.py --manifest internal/audiobook_lab/generated_candidate_restoration/restoration_manifest_20260702.json --title-limit 2
Total source titles in manifest scope: 2
Total unique titles: 152
Duplicates removed: 25
Skipped titles: 0
Titles completed: 2
Completed release-qualified: 0
Blocked by content sanitation: 0
Blocked by audio quality: 2
Titles using OpenAI TTS: 0
Titles using fallback audio: 2
Titles with auto-estimated sync: 2
Estimated retry count: 0
Estimated total API cost: $0.0000

## Title Gate Summary
| Slug | Language | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Gate 6 | Cover | Overall Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bn-027 | ben | GATE_0_WARN_MISSING_COVER | GATE_1_PASS | GATE_2_PASS_FALLBACK | GATE_3_AUTO_ESTIMATED | GATE_4_FAIL | - |  | MISSING | MANUAL_REQUIRED |
| bn-031 | ben | GATE_0_WARN_MISSING_COVER | GATE_1_PASS | GATE_2_PASS_FALLBACK | GATE_3_AUTO_ESTIMATED | GATE_4_FAIL | - |  | MISSING | MANUAL_REQUIRED |

## Ready for Human Sign-Off
- Count: 0

## Needs Manual Attention
- **bn-027**: Fallback audio used (non-premium TTS not generated), Missing reader_manifest.json in data/controlled_publications, Gate 5 blocked: requires Gates 0-4 pass, Gate 6 blocked: QA sheet not generated
  - Fix instruction: Action: manual intervention required before next run (add source MP3 or OPENAI_API_KEY).
  - Fix instruction: Regenerate reader_manifest.json in controlled_publications/{slug}/ and rerun.
  - Fix instruction: Review gate failure details and rerun after remediation.
- **bn-031**: Fallback audio used (non-premium TTS not generated), Missing reader_manifest.json in data/controlled_publications, Gate 5 blocked: requires Gates 0-4 pass, Gate 6 blocked: QA sheet not generated
  - Fix instruction: Action: manual intervention required before next run (add source MP3 or OPENAI_API_KEY).
  - Fix instruction: Regenerate reader_manifest.json in controlled_publications/{slug}/ and rerun.
  - Fix instruction: Review gate failure details and rerun after remediation.

## Missing Covers
- bn-027
  - Fix instruction: populate `coverAssets` in `content/books/bn-027/book.json`
- bn-031
  - Fix instruction: populate `coverAssets` in `content/books/bn-031/book.json`

## Sample Inspection (begin/middle/end)
- **bn-027** (ben) | Words: 0 | Duration: 2125.92s | TTS: fallback | Sync: auto-estimated | Warnings: Missing optional language metadata in content/books/bn-027/book.json
  - Render sample: - | internal/audiobook_lab/enhanced_candidates/bn-027/bn-027_enhanced.mp3
  - Text sample: -
  - Highlights: data/controlled_publications/bn-027/highlight_sync.json
- **bn-031** (ben) | Words: 0 | Duration: 1740.02s | TTS: fallback | Sync: auto-estimated | Warnings: Missing optional language metadata in content/books/bn-031/book.json
  - Render sample: - | internal/audiobook_lab/enhanced_candidates/bn-031/bn-031_enhanced.mp3
  - Text sample: -
  - Highlights: data/controlled_publications/bn-031/highlight_sync.json

## Git Diff Summary
- data/controlled_publications/bn-027/highlight_sync.json
- data/controlled_publications/bn-031/highlight_sync.json
- internal/audiobook_lab/release_gate/READINESS_DASHBOARD.md
- internal/audiobook_lab/release_gate/release_gate_status.json

## Exact Command
`scripts/audiobook_production_pipeline.py --manifest internal/audiobook_lab/generated_candidate_restoration/restoration_manifest_20260702.json --title-limit 2`
