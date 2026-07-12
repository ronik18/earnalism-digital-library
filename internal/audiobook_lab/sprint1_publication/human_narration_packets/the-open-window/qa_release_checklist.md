# QA And Release-Gate Checklist

- [ ] Received-audio format/checksum preflight PASS.
- [ ] ASR/source score >= 9.7.
- [ ] First and last words match.
- [ ] No missing, duplicated, reordered, or unrelated content.
- [ ] Every listening sample >= 9.4 with confidence >= 0.90.
- [ ] No robotic texture, mechanical cadence, list reading, choppy joins, or fallback TTS.
- [ ] Measured section-following sync; no word-level or estimated-sync claim.
- [ ] Manifest and checksum validation PASS.
- [ ] Audio endpoint and range request PASS.
- [ ] Frontend release-state and production route validation PASS.
- [ ] Owner release approval recorded before Listen or AudioObject exposure.
