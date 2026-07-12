# Failed Provider Attempt Summary: মুচিরাম গুড়ের জীবনচরিত

- Release classification: `INCOMPLETE_FAIL_CLOSED`
- Quality summary: `0.039/10 ASR-source; representative timed out`
- Exact blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Failed structured attempts found: `3`

- `representative_audition`: `google/google-cloud-texttospeech/bn-IN-Chirp3-HD-Aoede` -> `BLOCKED`; minimum/representative score `7.8`; fatal flags: `list_reading_rhythm_detected, mechanical_cadence_detected, robotic_texture_detected`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_aoede_slow_repair_audition/bengali_representative_audition_report.json`
- `full_book_qa`: `provider identity not recorded` -> `FULL_RELEASE_QA_BLOCKED`; minimum/representative score `7.8`; fatal flags: `list_reading_rhythm_detected, mechanical_cadence_detected, robotic_texture_detected`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_full_qa.json`
- `representative_audition`: `google/google-cloud-texttospeech/bn-IN-Chirp3-HD-Achird` -> `BLOCKED`; minimum/representative score `7.4`; fatal flags: `list_reading_rhythm_detected, mechanical_cadence_detected, robotic_texture_detected`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_targeted_repair_audition/bengali_representative_audition_report.json`

## Representative Passes That Are Not Release Approval

- `representative_audition`: `google/google-cloud-texttospeech/bn-IN-Chirp3-HD-Aoede` -> `PASS`; minimum/representative score `9.3`; fatal flags: `none recorded`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_chirp_audition/bengali_representative_audition_report.json`

Do not reuse failed audio or repeat an attempt fingerprint listed above.
A representative pass alone is not permission to publish; the received full candidate must pass every release gate.
