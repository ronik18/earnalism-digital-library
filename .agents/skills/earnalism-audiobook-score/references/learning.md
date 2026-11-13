# Retained scoring learning

Read this on every invocation, then read the current title's retained feedback.
These are scoped observations and editorial preferences, not listening scores or
universal musical rules. Record new evidence in the existing title/decision
journals before promoting a reusable lesson here. Do not add another learning
controller or copy private media into the skill.

## Continuity through serious passages

**Evidence:** The Selfish Giant owner listening feedback, 13 November 2026,
recorded under `selfish_giant_owner_continuity_fix_20261113` in
[title history](../../../../internal/earnalism_intelligence/title_decision_history.json).

The owner reported that music disappeared suddenly around 0:36, returned around
1:24 and dropped out elsewhere. The v3 plan contained a 44.487-second music-off
span beginning at 0:36.450 and several other long gaps. Successful rendering had
therefore preserved an arrangement problem.

**Reusable lesson:** Serious narration and questions do not automatically call
for silence. Inspect the musical arc and planned gaps as an arrangement; use
restrained neutral or reflective continuity where suitable. Keep purposeful
silence and scene breathing space when they serve the work. Do not generalize
this feedback into continuous music under every sentence.

## Preserve what the owner liked

In that same feedback, the owner said 4:33 seemed perfect and 8:04–8:13 looked
good. This feedback belongs to the v3 candidate:

`775f4fbabf551e2f41ba966532830597b3e54e4e0dedb59ed5cfb96a0dcacfc6`

The v4 continuity repair filled six earlier gaps with finite reflective passages
and scene fades while retaining those liked cues and the original narration
clock. Its candidate hash is:

`c2b40e3b618036cc64b310b3cfe72a43adb3c105d972371f3434f117e9400442`

**Status at this entry:** v4 was technically checked; owner listening remained
pending. Earlier praise does not approve the whole v3 recording or the new v4
mix. Technical comparison windows in the title history do not broaden the scope
of owner acceptance. Consult later title feedback before reusing this status.

**Reusable lesson:** Treat positive feedback as a preserve decision tied to the
reviewed candidate and time scope. A broader repair should retain that musical
material and context unless the owner asks to change it.

### Open Window and Sredni Vashtar: retained KEEP decisions

**Evidence:** On 14 November 2026 the owner said “Keep all of them” for the listed passages of these exact private v1 mixes. The full record is `open_window_sredni_owner_keep_feedback_20261114` in title history.

| Title | Reviewed MP3 SHA-256 | KEEP ranges |
| --- | --- | --- |
| The Open Window | `5ac7314b165b0716e9e63e1ea1c0ee9956b83b4a59b00d941bd499f373629167` | 1:45–1:55; 3:53–4:48; 6:34–6:40; 7:02–8:11 |
| Sredni Vashtar | `3fcbc364b60760f06885586c260bc3a6f36ee10715faa90b0e9b8ee882e18c8e` | 2:01–2:33; 4:48–4:52; 5:22–5:38; 8:21–8:40; 9:09–9:29; 9:44–10:38 |

For later revisions, apply the existing preserve-owner-liked-passages rule to these ranges and their musical context. Preserve narration and private access. The feedback specifies KEEP decisions; full-title listening coverage, final-private selection, publication approval and numerical scores were not supplied. The 6:34–6:40 checklist wording remains a KEEP action without inventing a separate heard finding. These are title-specific examples, not settings to copy to unrelated books.

## Source-aware fades and credits

The same pilot exposed music-file preroll: a fade could finish before the first
actual note. Measured source entry offsets and fades over sounding material
corrected that timing without moving narration cues. Finite excerpts and their
remaining source capacity mattered when extending the arrangement.

**Reusable lesson:** Check actual musical entries, source capacity and the
resulting fades. Preserve cleared-source provenance and attribution, including
the actual excerpting, level, fade and ducking changes. The pilot's two cleared
Kevin MacLeod tracks, Heartwarming and Heartbreaking, are case assets rather
than a required catalog for future books. Do not copy this title's fade lengths,
gains or source offsets as universal defaults.

## Automated music review did not provide sign-off

The retained alternative-review record
`selfish_giant_alternative_musical_review_20261113` documents music-presence,
boundary and grounding failures across automated reviewers. Some responses
transcribed speech correctly or recognized short controls yet misreported music
in the actual longer mix or focused excerpt. These findings were rejected and
did not establish a full musical review.

**Reusable lesson:** Reuse the documented failure rather than repeat the same
review settings or rotate prompts to obtain a favorable answer. Ground musical
claims in actual reviewed audio and their demonstrated scope. Prefer a simple
local repair from concrete listening feedback; keep unassessed musical fit
explicit. No new paid review loop follows from using this skill.

## Distinguish a release hold from absent timing measurements

**Evidence:** Bicharak private scoring on13 November2026, `bicharak_fresh_private_emotion_score_20261113` in title history. A later retained file already contained40 current-master acoustic paragraph measurements. Exact PCM clock mapping supported the unchanged takes; the repaired take used its own current evidence. Four saved word anchors refined the score without new inference.

**Reusable lesson:** Inspect the actual measurements and source/audio clock before treating an unqualified release status as missing timing. Qualify reuse for the requested production purpose and retain raw uncertainty and the separate full-release status. Never transfer an older clock across a changed take. Observed agreement between methods is not a calibrated error bound.

## Review sounding envelopes and verify the cause

**Evidence:** Bicharak v2-to-v3 review, `bicharak_private_score_refinement_20261113` in title history. Nonzero source-outro tails still produced multi-second low-level troughs; using sounding mid-sections removed those troughs. Removing the final source restart did not remove the first-second piano rise, so the initial causal attribution was corrected.

**Reusable lesson:** Inspect actual outgoing/incoming envelopes and source positions; lower placement gain or nonzero samples alone do not establish a smooth or softer transition. Use before/after evidence to test the proposed cause. Retain natural musical dynamics when no defect is established, and keep full listening judgments distinct from contextual and signal checks.

The full Open Window/Sredni review (`open_window_sredni_full_context_signal_review_20261114`) also corrected a3.01dB reference mismatch from comparing mono narration RMS with stereo music. For balance checks, use the renderer’s actual narration channel mapping, resampling and gain, state window/activity definitions, and inspect voice onsets, pauses and tails before diagnosing masking from a short level ratio. No heard defect or automatic repair followed from those diagnostic transients.

## Preserve the master during an isolated level correction

**Evidence:** Owner-requested Bicharak v3-to-v4 piano softening, `bicharak_owner_piano_softening_20261113` in title history. A calibrated retained instrumental stem supported a smooth local music delta; independent checks confirmed unchanged PCM outside the correction and the requested reduction. The owner subsequently confirmed, “The piano rise at 18:36 sounds good now,” and selected the unchanged v4 as the final private version (`bicharak_final_private_v4_20261113`). This is an owner-accepted example of a focused music-only repair with the narration and surrounding score preserved; its6dB reduction and3.4-second envelope remain specific to that performance.

**Reusable lesson:** When feedback concerns one musical rise and the surrounding mix should remain intact, prefer a local instrumental gain edit over whole-file remastering when the retained stems support it. Bind the exact source hashes and compare unchanged material. Choose depth and envelope for the actual note and feedback; this case does not prescribe universal settings. Re-encoded MP3 identity differs from preservation of the lossless master.
