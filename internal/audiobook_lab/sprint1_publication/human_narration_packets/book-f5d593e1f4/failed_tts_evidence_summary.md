# Failed Provider Attempt Summary: রামকানাইয়ের নির্বুদ্ধিতা

- Release classification: `INCOMPLETE_FAIL_CLOSED`
- Quality summary: `9.4/10 representative only; full-book source gate failed`
- Exact blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Failed structured attempts found: `2`

- `representative_audition`: `google/google-cloud-texttospeech/bn-IN-Chirp3-HD-Aoede` -> `BLOCKED`; minimum/representative score `7.8`; fatal flags: `mechanical_cadence_detected, robotic_texture_detected`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-f5d593e1f4_google_audition/bengali_representative_audition_report.json`
- `representative_audition`: `sarvam/bulbul:v3/pooja` -> `BLOCKED`; minimum/representative score `7.8`; fatal flags: `none recorded`; evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-f5d593e1f4_sarvam_audition/bengali_representative_audition_report.json`

Do not reuse failed audio or repeat an attempt fingerprint listed above.
A representative pass alone is not permission to publish; the received full candidate must pass every release gate.
