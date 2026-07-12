# Failed Provider Attempt Summary: গিন্নি

- Release classification: `ASR_SOURCE_MISMATCH_HUMAN_NARRATION_REQUIRED`
- Quality summary: fresh Sarvam full TTS passed generation, but raw ASR/source, first/last boundaries, listening minimum, confidence, and fatal-flag gates failed.
- Exact blocker: `RAW_ASR_SOURCE_1.3504_BELOW_9.7; FIRST_LAST_FAILED; LISTENING_MINIMUM_8.0_CONFIDENCE_0.85_FATAL_LIST_READING_RHYTHM`
- Failed structured attempts found: `3`

- `full_book_qa`: Google Aoede historical candidate -> listening/sync PASS but raw ASR FAIL; minimum/representative score `9.4`; fatal flags: `none recorded`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_qa.json`
- `full_book_qa`: `provider identity not recorded` -> `FULL_RELEASE_QA_BLOCKED`; minimum/representative score `8.0`; fatal flags: `none recorded`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_full_qa.json`
- `full_book_qa`: Sarvam `bulbul:v3` / `pooja` -> `FULL_RELEASE_QA_BLOCKED`; raw ASR/source `1.3504`, first/last failed, minimum score `8.0`, confidence `0.85`; fatal flags: `list_reading_rhythm_detected`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2g_full_qa.json`

Do not reuse failed audio or repeat an attempt fingerprint listed above.
A representative pass alone is not permission to publish; the received full candidate must pass every release gate.
