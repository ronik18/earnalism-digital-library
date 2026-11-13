# Content-aware audiobook background score

`scripts/audiobook_score.py` prepares an optional, offline instrumental score for
an exact narration candidate. It produces a contextual director packet, plans
music against measured narration timing, and renders a reproducible mix from
supplied instrumental stems. It does not make inference/provider calls or
generate recorded music. Missing suitable stems produce composition briefs and
explicit unresolved silence.

This is source preparation. It does not change existing books, upload assets,
activate audio, deploy the application, or publish an audiobook. Keep generated
audio, private text, director packets and evidence outside git.

## Why emotion and sentence type are separate

A question can be joyful, grieving, suspicious, rhetorical or playful. A serious
statement can follow laughter without becoming sad. The director considers the
complete supplied narrative context and annotates emotion separately from the
speech act. The planner consumes those contextual annotations; it does not claim
that keywords, punctuation, an acoustic measurement, or an uncalibrated model
confidence number prove emotional accuracy.

The generated director packet instructs the approved agent/model workflow to:

- Read the complete supplied text, retain scene and speaker context, and avoid
  scoring a quoted character's emotion as the narrator's own emotion.
- Distinguish an emotional state from a mention of that state. Negation,
  remembered events, hypotheticals, irony, and sarcastic laughter need context.
- Separate speech acts from emotion. Do not turn every question mark into
  suspense or every exclamation into joy.
- Place each decision at a supplied cue anchor. Do not invent timestamps,
  rewrite narration, add cues, or estimate timing from reading speed.
- Explain the contextual rationale and provenance. Resolve a deliberate
  override explicitly with its reason; do not conceal it as a model decision.
- Abstain when context does not resolve an interpretation. Silence and an
  unresolved item are valid outcomes. A confidence value is an estimate of the
  interpretation, never listening acceptance, a calibrated probability, or a
  release approval.

Use only the already approved agent/model workflow to return the requested JSON
direction. This command does not grant inference authority, provider budget or
permission to send private manuscripts to another service.

## Run the offline pipeline

Prepare the candidate, measured timing, instrumental catalog and existing rights
evidence in a local JSON input. Then run from the canonical checkout:

```sh
python3 scripts/audiobook_score.py prepare-director \
  --input /tmp/audiobook-score/candidate.json \
  --output /tmp/audiobook-score/director-packet.json
```

Use the complete packet in the approved workflow. Its `direction_template`
contains the exact response schema, candidate hashes and one annotation per cue.
For a local working copy, extract that generated template:

```sh
python3 - <<'PY'
import json
from pathlib import Path

packet = json.loads(Path('/tmp/audiobook-score/director-packet.json').read_text())
with Path('/tmp/audiobook-score/direction.json').open('x', encoding='utf-8') as out:
    json.dump(packet['direction_template'], out, ensure_ascii=False, indent=2)
    out.write('\n')
PY
```

Return the contextual interpretation in that direction file. Replace the
`REQUIRED` provenance values and every `REPLACE` rationale; preserve all
candidate hashes and cue IDs. An unchanged template is deliberately rejected.

```sh
python3 scripts/audiobook_score.py plan \
  --input /tmp/audiobook-score/candidate.json \
  --direction /tmp/audiobook-score/direction.json \
  --output /tmp/audiobook-score/plan.json

python3 scripts/audiobook_score.py render \
  --input /tmp/audiobook-score/candidate.json \
  --direction /tmp/audiobook-score/direction.json \
  --plan /tmp/audiobook-score/plan.json \
  --output-dir /tmp/audiobook-score/render
```

The Python commands use the standard library. Rendering additionally requires
local `ffmpeg` and `ffprobe` executables and accessible local audio files.
The renderer detects file-backed filtergraph support, using the legacy
`-filter_complex_script` option when available and `-/filter_complex` otherwise.
Local media rendering was tested with FFmpeg 9.0.2; older-option selection has a
focused compatibility test, rather than a claim of local FFmpeg 6.1 execution.
Keep the same FFmpeg build when comparing
repeated renders; reproducible planning does not promise byte-identical audio
across different codec/filter versions.
All `--output` paths must be new files. Rendering requires a new output directory
and replans from the supplied input/direction before comparing the entire
supplied plan. For a new interpretation, change the input/direction and create a
new plan. For a feedback-driven arrangement correction, retain that baseline and
use the explicit editorial edit below.

## Reuse the skill and improve from feedback

Use `$earnalism-audiobook-score` in this checkout. Its entry point is
[the repository skill](../.agents/skills/earnalism-audiobook-score/SKILL.md).
Each invocation reads its retained lessons and the current title's feedback,
preserves positively reviewed passages, and records the exact before/after
candidate and observed result in the existing intelligence journals. New
evidence improves the next run's choices; an unchanged run need not invent a
new lesson. This is retained editorial learning, not model-weight training.

For a placement revision, write a separate local `edits.json`:

```json
{
  "schema": "earnalism.audiobook_score.edit.v1",
  "base_plan_sha256": "<SHA-256 of the exact baseline plan.json file bytes>",
  "feedback": "Actual timestamped feedback and the intended fix/preserve scope",
  "placements": []
}
```

Replace `placements` with the **complete revised list** of placement objects
from the baseline, each with `asset_id`, `start_ms`, `end_ms`,
`source_offset_ms`, `fade_in_ms`, `fade_out_ms`, `gain_db` and `anchor_cue_id`.
An empty list deliberately removes all music. Keep measured cue IDs; an overlap
may begin before an anchor to make a musical prelap explicit. Use only suitable
assets with current candidate-bound rights. The renderer checks offsets,
finite capacity, gains, fades and timeline bounds as for ordinary renders.

```sh
python3 scripts/audiobook_score.py render \
  --input /tmp/audiobook-score/candidate.json \
  --direction /tmp/audiobook-score/direction.json \
  --plan /tmp/audiobook-score/plan.json \
  --edits /tmp/audiobook-score/edits.json \
  --output-dir /tmp/audiobook-score/revision-1
```

The command first checks the regenerated baseline, then applies the hash-bound
edit to freshly validated source assets. It retains feedback and edit hashes,
labels original cue decisions as `baseline_decisions`, and saves
`effective-plan.json` beside the WAVs/report. Baseline review items remain
baseline findings, not automatically resolved by a placement override. The new
audio remains a private candidate with listening status unperformed.

Inspect the full score's music-off spans before delivery. Serious narration and
questions do not automatically need silence. Use a restrained appropriate bed
or bridge for continuity when suitable music is cleared; retain intentional
breathing space and genuine unresolved gaps explicitly. Check the actual music
stem for unexpected dropout and compare the edited passages plus any protected
regions. A nonzero waveform proves signal, not audibility or emotional fit.

Record user comments against the exact reviewed audio hash and time range.
Update [retained lessons](../.agents/skills/earnalism-audiobook-score/references/learning.md)
only when the observation supports a reusable improvement, keeping title-specific
choices scoped to that title. Resume the loop with each use and new feedback;
finish when the requested edit and applicable checks are complete.

## JSON shapes

The following compact shapes include every required key. Replace digest
placeholders with actual lowercase 64-character SHA-256 values, paths with
retained local files, and example timing/rights with accepted evidence for the
actual candidate. They are explanatory examples, not ready-made acceptance
receipts. Paths resolve against the candidate JSON's directory, including paths
inside file-reference objects. Unknown keys and duplicate JSON keys are rejected.

`candidate.json`:

```json
{
  "schema": "earnalism.audiobook_score.input.v1",
  "manuscript": {"path": "manuscript.txt", "sha256": "<manuscript SHA-256>", "language": "en"},
  "narration": {"path": "narration.wav", "sha256": "<narration SHA-256>", "duration_ms": 4000},
  "timing": {"path": "timing.json", "sha256": "<timing file SHA-256>"},
  "territory": "IN",
  "assets": [{
    "id": "warm-family-a",
    "path": "warm.wav", "sha256": "<instrumental file SHA-256>", "duration_ms": 60000,
    "moods": ["amusement", "joy"], "energy": 0.25,
    "transition_group": "compatible-family-a",
    "rights": {"path": "warm-rights.json", "sha256": "<rights file SHA-256>"}
  }],
  "fixture_mode": false,
  "policy": {}
}
```

`assets` may be empty; planning then reports any requested music as unresolved
and produces composition briefs instead of fabricating assets. `fixture_mode`
and `policy` are optional. Policy keys/defaults are defined by `DEFAULT_POLICY`
in the script; omitted keys retain those defaults. The confidence threshold is
an interpretation-selection rule, not the release policy's confidence floor.

`timing.json`, for the exact UTF-8 manuscript `She smiled. Why?`:

```json
{
  "schema": "earnalism.audiobook_score.timing.v1",
  "manuscript_sha256": "<manuscript SHA-256>",
  "narration_sha256": "<narration SHA-256>",
  "duration_ms": 4000,
  "method": "measured_word_alignment",
  "provenance": {"tool": "<actual timing tool>", "version": "<actual version>", "boundary_validation": "accepted"},
  "cues": [
    {"id": "c1", "start_ms": 0, "end_ms": 2000, "text_start": 0, "text_end": 11, "text": "She smiled."},
    {"id": "c2", "start_ms": 2200, "end_ms": 3500, "text_start": 12, "text_end": 16, "text": "Why?"}
  ]
}
```

Offsets are zero-based Python Unicode character indices, with an exclusive
`text_end`; they are neither UTF-8 byte offsets nor JavaScript UTF-16 offsets.
Cue times use integer milliseconds and must not overlap. Cues must cover all
nonwhitespace manuscript content exactly once, in order; whitespace gaps and
measured pauses are allowed. Production `method` is `measured_word_alignment`
or `human_verified_audio`, with `boundary_validation: "accepted"`. Fixture mode
requires both values to be `synthetic_fixture` instead.

Cue granularity bounds the musical timing: the director cannot create a new
anchor inside a supplied cue. Supply measured phrase/word boundaries at the
needed narrative turns. A paragraph-wide cue cannot establish the exact timing
of a mid-paragraph change from laughter to seriousness.

`warm-rights.json`:

```json
{
  "schema": "earnalism.audiobook_music_rights.v1",
  "asset_sha256": "<instrumental file SHA-256>",
  "rights_holder": "<actual rights holder>", "license_id": "<actual license>",
  "scope": "commercial_audiobook", "territories": ["IN"],
  "commercial_use": true, "distribution": true, "derivative_mixing": true,
  "instrumental": true, "approval_status": "APPROVED",
  "approved_by": "<actual authorized reviewer>", "approval_ref": "<retained approval reference>"
}
```

Use the generated direction template rather than rebuilding the response
schema manually. Its provenance requires `method` (`contextual_model` or
`editor`), `agent_or_model`, `assessment_basis` (`text_only` or `text_and_audio`)
and `version`. Each annotation requires `cue_id`, `emotion`, `narrative_tone`,
`speech_act`, `intensity`, `confidence`, `uncertain`, `score`, `transition`,
`context_cue_ids` and `rationale`. Intensity/confidence range from 0 to 1;
`uncertain` is boolean. Context must include the current cue and only known cue
IDs. Use editor provenance and a concrete rationale for a deliberate editorial
override; do not invent an `override` field.

| Annotation field | Allowed values |
| --- | --- |
| `emotion` | `joy`, `amusement`, `sadness`, `anger`, `fear`, `calm`, `neutral`, `unknown` |
| `narrative_tone` | `serious`, `playful`, `reflective`, `tense`, `neutral` |
| `speech_act` | `statement`, `question`, `exclamation`, `command`, `narration`, `unknown` |
| `score` | `music`, `silence` |
| `transition` | `auto`, `gentle`, `strong` |

Asset mood tags are `joy`, `amusement`, `sadness`, `serious`, `tension`, `calm`,
`reflective` or `neutral`. Anger/fear map to tension; a serious tone can restrain
joyful/amused/neutral/calm emotion, while a reflective neutral passage maps to
reflective music. Speech-act labels retain context for the director and briefs;
they do not independently force a track change or a question stinger.

Assets may specify `entry_offset_ms` and `entry_fade_ms`. The offset skips
measured music preroll without moving the narration anchor; it is an absolute
file offset for a nonloop asset, or relative to an approved loop interval.
All usable-capacity checks subtract it. A retained file with 1.38 seconds of
leading silence must not finish its entire fade before its first sounding note.
Keep a small measured preroll and use an entry fade over the actual music.
An explicit entry fade is bounded by the passage length; an actual compatible
overlap still determines both crossfade envelopes. Incoming music can enter
gently while the outgoing incompatible mood ends promptly at the narrative turn.

Optional approved loops add this shape to an asset:

```json
"loop": {"start_ms": 1000, "end_ms": 9000, "evidence": {"path": "warm-loop.json", "sha256": "<loop proof SHA-256>"}}
```

The referenced loop proof requires `schema: "earnalism.audiobook_music_loop.v1"`,
the exact `asset_sha256`, matching `start_ms`/`end_ms`, `seam_verified: true`, and
a nonempty `provenance` string. Loops are never inferred from a short file.

## Candidate and evidence contract

Production timing must come from the actual narration audio and retain its
measurement provenance. Bind the manuscript, narration, direction and planned
music to their exact checksums. An audio-derived cue is not automatically a
content-fidelity pass; wrong words, missing content and bad alignments remain
defects. Estimated reading speed and a text-only frame grid cannot substitute
for measured production anchors.

Synthetic tests must explicitly select `fixture_mode: true`. Their timing and
audio are fixtures, never production synchronization or release evidence.
Changing narration or the source text invalidates the corresponding direction
and plan; regenerate against the new exact candidate.

Instrumental stems need current file checksums and retained commercial-use and
mix/distribution rights evidence. An evidence digest establishes file identity,
not the legal sufficiency of a license. The underlying rights decision must
already cover the intended use. A mood tag or a composition brief is not a
music asset or a rights clearance.

## Transitions and voice priority

The planner retains compatible music across ordinary sentence changes. Dwell
limits reduce distracting rapid changes; a supported hard narrative turn can
override dwell. Ambiguous or low-confidence direction produces explicit
unresolved silence rather than a guessed emotional score.
Dwell is evaluated at supplied cue anchors, not by introducing an estimated
mid-cue change when a timer expires. Use `transition: "strong"` with its actual
contextual rationale for an important turn that must bypass dwell.

Transitions use narration anchors and absolute placements so crossfades do not
progressively shorten the audiobook. Same-family stems offer the best basis
for continuity: prepare them with compatible harmony, tempo, texture and entry
points. Compatibility labels are supplied catalog metadata, not automatic
musicological verification. A smooth amplitude fade alone cannot establish
harmonic or narrative appropriateness.

Transitions have finite duration. The new emotional texture begins at the
planned anchor and develops through its fade; the tool cannot promise an
instantaneous complete musical change and a long smooth overlap at once.
Brief passages constrain fade lengths. Sparse or silent scoring is preferable
to forcing a new track under every phrase. Do not move an important narrative
turn arbitrarily later merely to wait for a musical bar.

Rendering produces `music_stem.wav` (the ducked instrumental), `final_mix.wav`
and `report.json`, plus the exact `effective-plan.json`. WAV outputs use automatic
RF64 when needed for recordings larger than the RIFF 4 GiB limit. It retains the original dry narration through its unchanged,
checksum-bound reference in the report rather than making another copy.
Narration drives music ducking, preserving the voice as the primary signal.
The renderer first measures the dry voice and applies constant gain within its
peak headroom before splitting the audible and sidechain paths. Excessive gain
or an unsuitable voice crest factor fails instead of letting a quiet voice sit
below normalized music. The original dry file remains unchanged. The final mix
is normalized and measured against the configured loudness/true peak targets.
Output measurements establish technical properties within their actual scope;
they do not establish emotional suitability or substitute for applicable
content checks.

A plan reports `PRIVATE_PLAN` or `PRIVATE_PLAN_WITH_UNRESOLVED_CUES`, absolute
`placements`, cue-level `decisions`, `review_items`, candidate/asset bindings and
`release_approved: false`. The report uses `PRIVATE_RENDERED` and also retains
`release_approved: false`. The final mix may contain intentionally silent or
unresolved music passages; a successful render is not a declaration that every
requested mood has a completed score.

Rendering is bounded to 256 referenced assets and 4,096 placements per plan,
with a duration-based timeout capped at 30 minutes for each media command.
An oversized plan must be prepared as appropriately bound chapter candidates;
the command does not silently truncate music or narration to fit. The current
capacity is a processing limit, not acceptance of an incomplete full-title
release package.

Inputs must be physical local audio containers (WAV, MP3, FLAC, MOV/M4A, Ogg,
AAC or Matroska). Media commands restrict protocols to local files and pipes
and reject playlists, so a checksum-bound local input cannot fetch a remote
stream as an unrecorded dependency.

## Acceptance stays with the existing title workflow

The plan and render are draft artifacts. They do not manufacture listening
scores, human approval, rights approval or release PASS. Their findings can
inform the existing candidate's music evidence and remediation work.

For an explicitly selected `automated-editorial-2026-11-11` job, follow
[`automated_audiobook_editorial_policy.md`](automated_audiobook_editorial_policy.md).
This feature adds no numerical human listening/confidence floor and no routine
human approval wait. Jobs using other policies retain those policies' existing
contracts. A draft status or an unresolved semantic item is not a new universal
human-review requirement.

Recording, voice/model and music rights, source/content fidelity, complete
candidate binding, upload/checksum, protected access, accounting, explicit title
holds and other applicable gates remain effective. Measured scoring cues are
internal production inputs: this feature does not re-enable read-along,
narration-linked highlighting or text-linked navigation. No live title's
reader-only/audio-hidden state changes as a consequence of local planning.

Hand the resulting master and its plan/report to the existing package/release
workflow as a new exact candidate. Historical title-specific scored adoptions
in `internal/audiobook_lab/scripts/native_scored_package.py` and
`open_window_scored_retained.py` bind older masters; their acceptance cannot be
transferred to a newly mixed file. This helper supplies scoring artifacts, not
a second publisher or an automatic music-rights release receipt.

## Reference basis

- [W3C EmotionML](https://www.w3.org/TR/emotionml/) describes separate emotion
  representations, confidence and media references. The local JSON contract is
  an application format; it does not claim EmotionML conformance.
- [FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html) documents
  fades, mixing, sidechain compression and loudness measurement/normalization.
  Inspect the retained local command and measurements for the filters actually
  used by a render.

## Private music-review limitation observed

For the Selfish Giant v3 pilot, Gemini passed blinded speech/music controls but misreported real music exits in longer material and in a focused excerpt. Correctly transcribed speech and a coarse `some` music flag do not establish musical-boundary perception. These responses were rejected, further calls stopped, and no listening score or release approval was fabricated. The private refined candidate retains the verified rendering/timing corrections; full musical sign-off needs a human listen-through. Keep future work simple and do not repeat these failed review settings.
