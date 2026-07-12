# QA And Release Checklist

- [ ] Received-audio format, duration, and checksum preflight PASS.
- [ ] Source/rights/provenance and performance or license chain PASS.
- [ ] ASR/manuscript score is `>= 9.7`.
- [ ] First and last words match the source-bound sanitized manuscript.
- [ ] No missing, duplicated, reordered, substituted, or unrelated content.
- [ ] Representative and full-book listening score is `>= 9.4` with confidence `>= 0.9`.
- [ ] No robotic texture, mechanical cadence, list-reading rhythm, choppy joins, fallback TTS, or placeholder audio.
- [ ] Measured `paragraph_or_section` sync PASS; `auto_estimated_sync=false`.
- [ ] Upload and checksum validation PASS.
- [ ] Metadata approval PASS and blocker list is empty.
- [ ] Audiobook endpoint returns `200/206` and range requests work.
- [ ] Browser/player gate PASS on supported desktop and mobile routes.
- [ ] Owner release approval is recorded before Listen controls, AudioObject metadata, or public audio exposure.
