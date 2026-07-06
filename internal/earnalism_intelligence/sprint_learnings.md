# Sprint Learnings

- Bengali reused local audio repeatedly failed manuscript match; do not rerun stale audio blindly.
- Bengali reader-only publication is a valid customer-facing outcome when content, rights, covers, and reader pass.
- OpenAI Bengali TTS has not met premium literary listening expectations; Sarvam remains promising but unproven for full release.
- Objective gates remain strict even with tiered listening and paragraph/stanza sync policy.
- Customer-facing book covers must never fall back to plain typography panels. Use approved graphical covers first and lightweight graphical runtime fallback only when source art is missing.
- Deterministic HTML text is safer than generated image text for covers because it avoids misspellings, supports Bengali/English typography, and prevents heavy raster churn.
- Homepage performance in the CRA shell is still constrained by client-render LCP; hero asset/font/background optimizations improved local Lighthouse from 66 to 90 but did not restore the requested >=94 guardrail.

## Achievement-Aware Cost Governor - 2026-07-06T18:44:02.494690+00:00

- Added `achievement_ledger.json` to prevent rerunning achieved goals when source hashes are unchanged.
- Latest Bengali integration evidence supersedes older prompt state: all 31 route-live Bengali titles are reader-only approved/audio-hidden; the six former rights blockers are rights `PASS` and audiobook endpoints are hidden/non-200.
- Current graphical-cover and calm-type pass is visually safe and cover-complete, but current evidence-based UX index is 9.66 with Lighthouse performance 90/LCP 3.6s, so a new GREEN claim is not justified without a targeted performance fix.
- Sarvam/Bengali audiobook work remains deferred behind explicit paid/provider approval and higher-priority merge/performance blockers.

## Performance Rescue - 2026-07-07

- Do not trust an old GREEN UX score after cover/type source changes; rerun the specific active Lighthouse route only when performance is the blocker.
- The LCP regression was not caused by paid/generated covers. The solvable causes were the mobile hero image candidate, automatic first-visit tour timing, early idle prefetch/settings work, and an oversized header logo asset.
- Eager-loading Home into the main bundle was tested and rejected because it worsened Lighthouse; delaying noncritical work restored performance with less risk.
- Final local production-equivalent evidence: Lighthouse performance 96, LCP 2.7s, accessibility 100, SEO 100, cover audit 164/0 typography-only, visual smoke PASS, audio safety PASS.
