# READINESS_DASHBOARD

Run ID: 20260703T182202Z
Run started: 2026-07-03T18:22:02+0000
Run completed: 2026-07-03T18:23:13+0000
Run timestamp: 2026-07-03T18:23:13+0000
Pipeline command: scripts/audiobook_production_pipeline.py --only-slugs frankenstein --title-limit 1
Environment flags present: OPENAI_API_KEY=False, OPEN_AI_API_KEY=False, CLOUDINARY_URL=False, EARNALISM_API_URL=False, EARNALISM_ADMIN_TOKEN=False, ADMIN_EMAIL=False, ADMIN_PASSWORD=False
Total source titles in manifest scope: 1
Total unique titles: 1
Duplicates removed: 0
Skipped titles: 0
Titles completed: 1
Completed release-qualified: 0
Blocked titles: 1
Titles using OpenAI TTS: 1
Titles with fallback audio: 0
Titles with auto-estimated sync: 0
Estimated total API cost: $0.0000
Estimated retry count: 0
Failed titles: 1
Release-ready condition: NO

## Release readiness (GO LIVE READY: NO)
- Total titles must be: 152 | Current: 1
- Covers with URL: 1
- Content artifacts passing: 0

## Ready for Human Sign-Off
- Count: 0
- CSV artifact: /Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/audiobook_lab/release_gate/title_release_readiness.csv

## Top Blocker Categories

- content sanitation: 1
  - frankenstein

## Title Gate Summary
| Slug | Language | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Gate 6 | Cover | Overall Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frankenstein | en | GATE_0_FAIL | GATE_1_PASS | GATE_2_PASS | GATE_3_PASS | GATE_4_FAIL | - |  | OK | BLOCKED |

## Needs Manual Attention / Blocked Queue
- **frankenstein**: Forbidden boilerplate in chapter content (content/books/frankenstein/chapters/008-chapter-4.json), BLOCKER: runtime/log traceback text in content/books/frankenstein/chapters/008-chapter-4.json, BLOCKER: suspicious token in content/books/frankenstein/chapters/008-chapter-4.json: \bTraceback\b|\bException\b|\bJSONDecodeError\b, Forbidden boilerplate in chapter content (content/books/frankenstein/chapters/010-chapter-6.json), BLOCKER: runtime/log traceback text in content/books/frankenstein/chapters/010-chapter-6.json, BLOCKER: suspicious token in content/books/frankenstein/chapters/010-chapter-6.json: \bTraceback\b|\bException\b|\bJSONDecodeError\b, Forbidden boilerplate in chapter content (content/books/frankenstein/raw/source.txt), BLOCKER: runtime/log traceback text in content/books/frankenstein/raw/source.txt, BLOCKER: repeated standalone page/chapter markers detected in content/books/frankenstein/raw/source.txt (48), BLOCKER: suspicious token in content/books/frankenstein/raw/source.txt: \bTraceback\b|\bException\b|\bJSONDecodeError\b, Reader manifest chapter count mismatch for frankenstein: manifest=28, text=29, Reader manifest chapter identifiers mismatch for frankenstein, Cannot load enhanced MP3: Unable to process >4GB files, Gate 5 blocked: requires Gates 0-4 pass, Gate 6 blocked: QA sheet not generated, CONTENT_BLOCKER: Gate 0 failed, AUDIO_BLOCKER: Gate 4 failed, QA_BLOCKER: Gate 5 not generated, LEGAL_BLOCKER: Gate 6 not generated

## Ready-Match Blocker Queue (sorted by blocker type + language)
### Content Sanitation (1)
- en — frankenstein

## Sample Inspection (begin/middle/end)
- **frankenstein** | Frankenstein | Mary Shelley | Lang: en | Words: 40 | Duration: 32950.71s | WPM: 0.0 | TTS: OPENAI_TTS | Sync: real | Fallback Audio: False | Auto Sync: False
  - Render sample: content/books/frankenstein/chapters/001-letter-1.json | internal/audiobook_lab/enhanced_candidates/frankenstein/frankenstein_enhanced.mp3
  - Reader: data/controlled_publications/frankenstein/reader_manifest.json; EPUB: None; PDF: None
  - Covers: https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566127/earnalism/covers/front/cover_3f8a6bb7-258b-4473-b14e-c68d2df58b29.png | https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566151/earnalism/covers/back/back_cover_3f8a6bb7-258b-4473-b14e-c68d2df58b29.png
  - Text sample: {   "bookSlug": "frankenstein",   "chapterNumber": 1,   "id": "chapter-001",   "title": "Letter 1",   "language": "en",   "content": "_To Mrs. Saville, England._\n\nSt. Petersburgh, Dec. 11th, 17—.\n\nYou will rejoice to hear that no disaster has accompanied the commencement of an enterprise which you have regarded wit
  - Warnings: Cover URLs resolved for frankenstein: mapping:front + mapping:back, Missing coverAssets in content/books/frankenstein/book.json, Cover URLs assigned: front=https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566127/earnalism/covers/front/cover_3f8a6bb7-258b-4473-b14e-c68d2df58b29.png, back=https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779566151/earnalism/covers/back/back_cover_3f8a6bb7-258b-4473-b14e-c68d2df58b29.png, possible markdown/annotation artifact in content/books/frankenstein/raw/source.txt, repeated chapter header-like lines in content/books/frankenstein/raw/source.txt (36), excessive spacing/markdown artifacts in content/books/frankenstein/raw/source.txt
  - Highlights: data/controlled_publications/frankenstein/highlight_sync.json

## Git Diff Summary
- frontend/public/assets/books/sultanas-dream/front-cover.svg
- frontend/src/components/ShelfTwoSlideshow.jsx
- frontend/src/index.css
- frontend/src/lib/controlledLaunch.js
- frontend/src/pages/Home.jsx

## Exact Command
`scripts/audiobook_production_pipeline.py --only-slugs frankenstein --title-limit 1`

## Retry and blocker counts
- Auto retries total: 0
- OpenAI-related blockers: 0
- Manual required queue: 0
- Manual required slugs: -
- Sample inspections: 1 (3 beginning / 3 middle / 3 end)
