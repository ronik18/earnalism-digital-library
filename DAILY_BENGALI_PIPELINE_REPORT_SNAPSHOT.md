# Daily Bengali Pipeline Report Snapshot

This is a committed sample snapshot from the 2026-06-20 IST owner audit. Recurring daily reports should be generated locally with `npm run owner:daily-growth-audit`, which writes dated artifacts under `output/daily/YYYY-MM-DD/`.

Date: 2026-06-20 IST

Bengali pipeline score: 9.0 / 10

Recommendation: GO for draft/pipeline work only; HOLD for public Bengali Gothic publishing/audio.

## Kshudhita Pashan Status

Current `main` production surface:

- Kshudhita Pashan / The Hungry Stones is not exposed on homepage static HTML.
- Kshudhita Pashan is not exposed on library static HTML.
- Kshudhita Pashan is not in the public sitemap.
- No Start Reading CTA was found for Kshudhita Pashan on current main.
- No Listen Now CTA was found for Kshudhita Pashan on current main.

Pipeline work may continue only as draft/source/rights/audio-readiness artifacts.

## Audio Safety

- No Bengali Gothic audio was enabled today.
- No audiobook provider call was made.
- No audio upload occurred.
- Full audiobook claims remain blocked until provider output, transcript comparison, waveform/timestamps, sync QA, and human listening review pass.

## Top Wins

- No accidental Kshudhita public launch was detected.
- Dracula remains the only controlled approval artifact.
- Bengali Gothic work can continue safely in reports/drafts.

## Top Risks

- If the Bengali Gothic candidate PR is merged later, it must remain pipeline-only until explicitly approved.
- Any future audio preview must stay metadata-only until QA gates pass.
- Bengali source text must not be committed in full unless explicitly approved.

## Exact Fixes Needed

- Keep Kshudhita out of reader routes until final rights/source/text QA approval.
- Keep pronunciation guide and audio QA checklist as draft artifacts.
- Add an explicit canary after any Bengali pipeline PR merge to verify no Start Reading or Listen Now CTA appears.

Rollback needed today: No.
