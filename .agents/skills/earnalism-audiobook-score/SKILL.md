---
name: earnalism-audiobook-score
description: Plan, mix and refine emotional instrumental backgrounds for existing audiobook narration, using measured timings, cleared music and retained owner feedback. Use for audiobook scoring and musical continuity edits.
---

# Earnalism audiobook score

For a cinematic book edition, use the repository's
[`earnalism-book-audiovisual`](../earnalism-book-audiovisual/SKILL.md) coordination
with the exact scored master. Preserve story-specific silence and review scope;
an audiobook music licence or accepted dry narration does not establish AV rights
or acceptance of a new final soundtrack.

Prepare the requested scored audiobook or narrow musical repair with the existing
narration and measured clock. Keep the result private unless the current task
separately authorizes the supported publication workflow. Explicit invocation:
`$earnalism-audiobook-score`.

## Resume and direct the music

On every invocation, read [retained learning](references/learning.md), the current
title checkpoint and relevant title feedback in
`internal/earnalism_intelligence/title_decision_history.json`. Read applicable
AGENTS.md and the relevant provider-memory entry before considering an external
review. Current owner instructions take precedence over retained preferences.

Read the complete supplied story and use the exact narration, measured cues and
cleared instrumentals. Follow the [scoring guide](../../../docs/audiobook_background_score.md)
for candidate preparation, direction, planning and rendering; it contains the
complete schemas and commands. Keep private text, audio and generated evidence
outside git.

Direct scenes in context. Separate emotion, narrative tone and speech act: a
question need not create suspense, and seriousness need not create sadness or
music-off. Prefer continuity through ordinary dialogue and scene changes when
the musical material supports it. Inspect the planned music-off spans and bridge
unintended dropouts with suitable restrained music. Purposeful silence remains
valid; do not fill it merely to achieve continuous coverage. Missing suitable
music stays an explicit unresolved choice rather than a fabricated asset.

## Refine the exact candidate

Turn actual feedback into concrete fix and preserve decisions. Retain the
owner-liked passages and their musical context; adjust only what the correction
requires. Preserve narration wording and timing. Choose source excerpts, levels
and fades for the actual scene and material rather than applying a universal
fade duration or silence threshold. Retain the music's source and modification
credits.

Use the existing offline pipeline. For a placement correction to a retained
baseline, use `render --edits` as documented in the guide instead of silently
rewriting the baseline plan. The edit binds the raw baseline plan SHA-256,
records the actual feedback rationale and supplies the complete placement list.
The renderer first regenerates and checks the baseline, validates placements
against the supplied cleared assets and saves `effective-plan.json` with the
render. Read the guide for the full edit schema.

Check the resulting duration, levels, source capacity and changed transitions
with the existing local tools. Compare preserved material where relevant. These
measurements establish the edit's technical properties; they do not establish
heard emotional fit. Share the complete private result with a concise account of
the repair, preserved passages and actual review status.

Do not make repeated AI review calls to chase a music-fit verdict. Reuse relevant
evidence and provider learning. Correct speech recognition, a music-presence
label or a successful control does not prove perception of musical transitions
in the actual mix. Routine continuity repairs need no new provider call. Any
requested external review remains within its existing transfer, attempt and
spending authority; an inconclusive response remains inconclusive.

## Retain useful learning

At the end of each use, record the exact input candidate hash, actual feedback
and source, title/time scope, fix and preserve decisions, resulting candidate
hash, applied change and actual verification/listening status in the existing
title history and decision journal. Carry material learning into the other
AGENTS-required learning/campaign records by reference to that same entry;
preserve their unrelated authority and counters.

Update [retained learning](references/learning.md) only with an evidenced reusable
lesson or explicit preference, retaining its source and scope. Keep individual
title facts in title history. When there is no new supported lesson, record
`no-new-learning` in the run entry rather than accumulating duplicate rules.
Future invocations must read and apply the retained lessons. This improves
instructions and editorial choices; it does not train model weights, guarantee
perfect scoring or turn an applied fix into listening acceptance.
