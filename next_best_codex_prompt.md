# Next Best Codex Prompt

Continue the Bengali audiobook pilot only if the owner explicitly approves a second repaired full-pilot generation.

Current truth:
- Pilot `book-2b9853ec52` generated with Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- TTS generation passed, duration ~330.06 seconds.
- ASR/manuscript gate failed: score `7.0199 < 9.7`, first/last boundary checks failed, and no word/segment timestamps were returned.
- Upload, metadata, browser, and public audio exposure were not run.
- Source has been patched so future TTS-only Bengali preparation strips source/frontmatter lines before generation.

If owner approves a repaired second pilot despite the one-pilot guard, run the same guarded Railway command after confirming the TTS-prep hash changed and no stale audio cache is reused. Otherwise, keep Bengali audio hidden and continue PR/ship work.
