# Audiobook Narration QA Rubric

Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

This rubric is an internal human-review framework for future Bengali and English audiobook experiments. It does not approve public audio, does not claim human narration, does not claim WCAG compliance, and does not make any audiobook public. Dracula remains live only as a core reading release. Kshudhita Pashan remains pipeline-only.

## Release Threshold

- Minimum final human-review score: `9.5/10`
- Text fidelity: `PASS` required
- Legal/commercial-use evidence: `PASS` required
- Derivative audiobook rights: `PASS` required
- Accessibility listening review: `PASS` required
- Owner approval: `PASS` required
- Rollback plan: `PASS` required

Any missing or failed required field keeps the audiobook in `HOLD`.

## Scoring Scale

| Score | Meaning |
| --- | --- |
| 10.0 | Release-quality evidence with no known defects after human review. |
| 9.5-9.9 | Candidate may proceed to owner review if all hard gates pass. |
| 9.0-9.4 | Strong internal candidate, but public release remains blocked. |
| 8.0-8.9 | Useful for research only; audible or legal/QA gaps remain. |
| Below 8.0 | Reject or rerun with a different model/provider/source setup. |

## Hard Fail Conditions

- Public audio URL, Listen Now CTA, AudioObject metadata, or audio file appears before approval.
- Source text evidence is missing.
- Model/provider commercial-use license is missing or unclear.
- Derivative audiobook rights are missing or unclear.
- Human-review scorecard is missing.
- Final human-review score is below `9.5/10`.
- Text fidelity fails or cannot be verified.
- Owner approval is missing.
- Rollback plan is missing.
- Draft PR #44 or Draft PR #45 evidence is treated as public release approval.
- The output claims human narration when audio is AI-generated or AI-assisted.
- The output claims "no AI touch" when AI generation or enhancement is used.
- The output claims blind-user testing, WCAG compliance, screen-reader certification, or fully accessible audiobook platform status without evidence.

## Bengali Narration Criteria

| Area | Review Standard | Hard Gate |
| --- | --- | --- |
| Bengali pronunciation accuracy | Names, Sanskritized terms, Perso-Arabic words, English loan words, regional forms, and literary archaisms are pronounced consistently and naturally. | Score required |
| Bengali literary rhythm | Sentence cadence respects classic Bengali prose, long syntactic arcs, and reflective narration without rushing. | Score required |
| Rabindranath-era/classic tone | Historical diction is handled with restraint, not modernized into casual speech unless the source requires it. | Score required |
| Punctuation and sentence flow | Commas, danda, semicolons, dialogue breaks, paragraph changes, poetry line breaks, and chapter headings produce understandable pauses. | Score required |
| Dialogue differentiation | Speaker changes are intelligible without theatrical exaggeration or caricature. | Score required |
| Emotional restraint | Fear, wonder, irony, grief, and suspense are present but not melodramatic. | Score required |
| Text fidelity | No omitted sentences, added lines, hallucinated text, repeated paragraphs, or reordered passages. | PASS required |
| Listener fatigue | A reviewer can listen for a long session without harshness, robotic cadence, or tiring prosody. | Score required |

## English Narration Criteria

| Area | Review Standard | Hard Gate |
| --- | --- | --- |
| English gothic/literary tone | Narration fits classic gothic and literary prose without sounding casual, synthetic, or over-performed. | Score required |
| Dracula-specific mood and pacing | Epistolary headings, dated entries, suspense, dread, and travel descriptions are paced clearly and with restraint. | Score required |
| Pronunciation | Names, places, archaic expressions, and literary phrases are intelligible and consistent. | Score required |
| Dialogue differentiation | Characters are distinguishable without theatrical distortion or stereotype. | Score required |
| Emotional restraint | Suspense and fear are controlled; the narrator does not over-act. | Score required |
| Narrator consistency | Voice, pace, loudness, and pronunciation remain stable across chapters. | Score required |
| Text fidelity | No hallucinated text, omitted passages, added commentary, repeated lines, or chapter-order drift. | PASS required |
| Listener fatigue | Reviewer can listen through a long sample without irritation, harshness, or robotic fatigue. | Score required |

## Technical Audio Criteria

| Area | Required Evidence |
| --- | --- |
| Noise and artifacts | No clipping, metallic artifacts, harsh sibilance, buzzing, dropouts, repeated fragments, or obvious synthesis glitches. |
| Pacing and breath control | Pauses are natural and do not create long silence or breathless rushing. |
| Chapter consistency | Loudness, voice identity, pace, and pronunciation remain stable chapter to chapter. |
| Speed clarity | Samples remain clear at `0.8x`, `1x`, `1.25x`, and `1.5x`. |
| Transcript/sync | Transcript is available when required and sync tolerance is at or below `250 ms`. |
| Rollback readiness | Public metadata, audio routes, static snapshots, and storage links can be disabled quickly. |

## Accessibility Listening Criteria

This is not a public accessibility claim. It is an internal review checklist.

- Blind and non-reading listeners can understand the title, chapter, lock state, and playback state without visual context.
- Chapter navigation, transcript access, and playback speed are understandable non-visually.
- Error and locked states explain what happened and what to do next.
- The audio remains intelligible at common playback speeds.
- No public claim may say blind-user tested until actual blind-user testing evidence exists.

## Required Reviewer Evidence

Each human-review scorecard must include:

- title or work reviewed
- model/provider candidate
- reviewer name or reviewer role
- sample duration
- source text evidence
- derivative-rights status
- legal/commercial-use status
- accessibility listening status
- text fidelity status
- final score
- GO/HOLD decision
- blocking reasons
- owner approval field

## Rollback Criteria

Rollback or hold immediately if:

- any public audio route becomes reachable before approval
- any public page shows Listen Now
- any static snapshot or social preview contains audio metadata
- human-review score falls below `9.5/10`
- text fidelity, derivative rights, model license, owner approval, or rollback plan fails
- a reviewer finds repeated lines, omitted text, hallucinated text, or severe listener fatigue
