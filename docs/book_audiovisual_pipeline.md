# Cinematic book production

This adapter coordinates the existing four skills and the existing
`produce_release.py` release governor. It supports Bengali and English discovery,
private local composition and candidate-bound AV checks. It does not synthesize
unqualified voices, train weights, buy compute or publish video by itself.

## One production path

| Stage | Existing capability | Exit evidence |
| --- | --- | --- |
| Edition and rights | `earnalism-book-production`, existing manifest/admin workflow | Complete sanitized edition, intended audiovisual use/territory, covers and applicable rights |
| Voice and narration | `earnalism-audiobook-go-live`, qualified retained masters before auditions | Exact narrator/model/voice provenance, full fidelity/completeness, real listening |
| Dramatic score | `earnalism-audiobook-score`, `scripts/audiobook_score.py` | Contextual direction, cleared source capacity, measured clock, exact mix and heard fit |
| Storyboard and composition | `earnalism-video`, `scripts/book_av_render.py` | Story-specific art/motion, independently supplied compositions, exact branding/END, measured captions |
| Qualification and release | `scripts/produce_release.py`, `scripts/release_acceptance.py` | Complete exact-candidate evidence and one destination-bound final decision; actual destination acceptance before LIVE |
| Feedback | Existing title/campaign history and skill lessons | Actual source/time scope, protected passages, narrow repair and affected rechecks |

Start from the repository root:

```bash
python3 scripts/book_audiovisual.py plan --title "The Open Window"
python3 scripts/book_av_render.py --job /PRIVATE/job.json --validate-only
python3 scripts/book_audiovisual.py render --job /PRIVATE/job.json --output-dir /PRIVATE/new-candidate
python3 scripts/book_audiovisual.py check --manifest /PRIVATE/release.json
```

The title planner resolves retained candidates and emits an action packet. A title
match is a locator, not acceptance. Unknown/ambiguous editions remain explicit;
inspect the complete text and actual checkpoint. Import only through the existing
API, in draft unless release authority actually applies. Keep manuscript, raw
audio, generated artwork, job files and review evidence outside git/public assets.

## Voice and visual direction

Read the full book and choose a stable narrative identity before scene expression.
An accepted master is the cheapest first option. New voice selection compares
qualified language/accent, proper-name clarity, long sentences, dialogue and
full-length fatigue against the content. Do not infer qualification from a display
name, model licence or a single pleasing sample. The English roster cannot route
Bengali to an unsupported model. A failed or unknown attempt stays consumed until
the existing ledger reconciles it; changed filenames do not reset allowances.

The compositor consumes completed source-bound storyboard assets. Scene anchors
and captions must come from measured audio evidence. It can animate camera motion
over an illustration or use supplied reviewed motion clips; these are different
creative capabilities. It does not invent character animation or factual review
from decoding. Supply a separate composition for each selected aspect ratio and
retain the approved logo and three-second END asset with its own sound. The
literary score may contain deliberate silence; use story-specific direction.

### Local composition contract

The `earnalism.book_av_render.v1` job contains these fields (file references are
`{path, sha256}`; resolve paths relative to the job):

- `title`, `territory`, `fixture_mode: false`.
- `manuscript` reference plus `language: en|bn`; `narration` and `scored_audio`
  references plus the same `duration_ms`; `timing` reference to the existing
  `earnalism.audiobook_score.timing.v1` measured source/narration-bound clock.
- `assets`: unique IDs, `kind: image|video`, file reference and `rights` reference.
  Each `earnalism.book_av_visual_rights.v1` receipt binds the actual asset hash,
  `scope: commercial_audiovisual`, actual territories, `approval_status: APPROVED`,
  `commercial_use`, `distribution` and `derivative_use` all true, and nonempty
  rights-holder, licence, attribution and approval references.
- `scenes`: ordered `{id, cue_id, start_ms, end_ms}` covering the body once. A new
  scene begins at its measured cue anchor; it does not estimate a new boundary.
- `branding`: approved transparent PNG reference plus `approval_ref`.
- `outputs`: one or both independently authored `landscape`/`portrait` records,
  native even `width`/`height`, `fps` of 24/25/30/60, a `watermark` box and halo,
  the complete scene layouts, and an approved native-size `end_clip` reference
  with `duration_ms: 3000` and `approval_ref`.
  Optional `canvas_color: "#RRGGBB"` sets the full composition background; use
  actual contrast review with the unchanged transparent brand lockup rather than
  adding a backing rectangle to the logo.
- Each output scene layout specifies `scene_id`, `asset_id`, contained artwork
  `box: [x,y,width,height]`, `zoom_start`, `zoom_end` and `source_offset_ms`.
  The compositor reserves the complete logo halo outside artwork; this simple
  composition contract does not certify arbitrary subject silhouettes.
- `captions`: boolean. Only measured, short, readable cues produce
  SRT/VTT sidecars. Coarse source paragraphs are rejected rather than split into
  estimated word cues. Burned-in captions are not implemented by this adapter;
  qualify the actual sidecar consumer at delivery. Captionless rendering is
  available for private preparation; the current production route requires the
  measured sidecars and their final delivery review.

Subtitle display collapses whitespace within the exact source cue; source text,
offsets and raw acoustic evidence remain unchanged. This does not estimate words
or invent cue boundaries.

The supported compositor uses hard scene cuts, gentle centered illustration
camera motion or finite supplied motion clips without looping. It adds no
generated acting. It builds one 48kHz stereo 24-bit PCM soundtrack from the source
score followed by the END sound, preserving every decoded score sample and
recording its difference from the integer-millisecond timing clock (at most 1ms),
encodes AAC once and verifies the actual AAC payload in every final composition.
The END audio follows its original exact frame presentation timestamps, retaining
decoded samples at their positions and silence in any original timestamp gaps.
Concatenating raw decoder buffers alone can remove those gaps. The END picture
is transcoded at its native canvas to the selected frame rate;
this is content lineage, not byte-identical source-video preservation. All media
and partial failures remain in a new private directory; existing outputs are
never overwritten.

## Evidence and authority

An optional `audiovisual` object in the existing release manifest binds the text,
dry narration, final scored soundtrack, timing, storyboard, score plan and every
output. AV evidence binds those exact candidate inputs and named destinations.
Read `scripts/release_acceptance.py` for the executable schema; malformed, missing
or stale required evidence is blocking. A release manifest without `audiovisual`
keeps its existing audiobook/Reader behavior.

An AV technical receipt includes the actual compositor report reference. The
governor independently validates its source job, complete delivered-file decode,
PCM source/END lineage, AAC payload and selected caption sidecars. Evidence is
excluded from the stable candidate digest to avoid circular receipt hashes;
selected source files, outputs, captions and destinations remain bound. A human
or automatic review receipt must identify its actual provenance and complete
scope. The explicit owner `GO_LIVE` action is never generated by this checker.

Produce the technical receipt from real rendered files through:

```bash
python3 scripts/book_audiovisual.py measure --manifest /PRIVATE/release.json --render-report /PRIVATE/candidate/render-report.json --output /PRIVATE/new-technical-receipt.json
```

This performs measurements only and grants no editorial or publication acceptance.

Rights evidence must cover the selected audiovisual adaptation, synchronization
and distribution, including literary/translation, voice/model, music and image
permissions and territory. This is an applicability check, not legal certainty.
The actual reviewer and supporting documents establish clearance.

Full final listening/visual review remains distinct from technical checks. Bengali
overall and every required dimension must be >=8.9, confidence >=0.90 and fatal
flags absent, with ASR/manuscript >=9.7 and the rest of the source/delivery gates.
No audio-only timing exemption clears caption-dependent production. No fixture or
short audition can clear a full edition. Preserve current title holds and public
Bengali Reader-only/audio-hidden state.

The Bengali review's nested `dimensions` uses the established rubric:
`naturalness`, `pronunciation`, `emotional_expression`, `punctuation_pause`,
`pacing`, `continuity`, `anti_robotic_texture`, `anti_choppy_join` and
`listener_enjoyment`. Each required and any additionally supplied dimension must
meet 8.9; overall must meet 8.9 and confidence 0.90. Preserve the original review
and its actual provenance rather than inventing scores during schema conversion.
The full review also records the actual verified caption consumer and destinations
in `caption_delivery`; local sidecar creation alone cannot establish saved,
synchronized captions on a platform.

For private browser review, reuse the installed video skill's
`software/review_server.py`, bound only to loopback. It supports media byte ranges;
the basic Python file server failed actual chapter seeking in the tested native
player. Verify captions, seeking, ending and replay on the real served file.
These are technical consumer checks, not complete listening/AV acceptance.

The current audiobook promotion adapter does not publish AV. Even complete local
AV qualification must stop before an unsupported destination operation. Prepare
the exact reviewed package and its supported manual/platform handoff, then verify
the actual destination before reporting LIVE. The one owner final decision binds
the exact candidate and selected destinations; local tests never create it.

## Feedback and evidence reuse

| Changed input | Recheck | Reuse when exact and applicable |
| --- | --- | --- |
| Manuscript/words/narration | Fidelity, first/last/order, timing, affected score/captions/scenes, listening | Unchanged unrelated art/licence evidence |
| Music or mix | Mix continuity, levels, transitions, final soundtrack listening and AV synchronization | Exact dry narration fidelity and unchanged source |
| Pictures/motion/layout | Affected composition, pixels, branding/captions and complete final visual review | Verified identical soundtrack listening |
| Encoding/output bytes | Exact delivered streams, full decode, duration, transport and sound identity | Perceptual evidence only with proven applicable unchanged content |
| Use/territory/licence | Rights applicability and affected final decision | Unchanged technical results |

Record actual feedback and its source against the exact candidate, with a
timestamp/frame scope, concrete defect, passages to preserve and observable finish
line. Apply the smallest repair and keep previous versions. Automated speech
recognition, music detection and successful controls do not establish perception
of the actual score's emotional transitions. Use the retained failed-provider
memory rather than repeatedly seeking a favourable review.

The optional private feedback command accepts JSON with `candidate_sha256`,
`source: human|automatic`, `source_ref`, `scope`, `area`, `finding`, `fix` and
`preserve`. `area` is `narration`, `score`, `visual`, `captions`, `rights` or `technical`.
It creates a new feedback record with affected evidence requirements; it does
not change an accepted candidate or claim that a proposed repair was applied:

```bash
python3 scripts/book_audiovisual.py feedback --input /PRIVATE/actual-feedback.json --output /PRIVATE/new-feedback-record.json
```

At handoff update existing title history, decision ledger, sprint learning and
relevant campaign state by reference to the same material result. Preserve
unrelated counters, scopes and holds. An evidenced reusable lesson can update the
relevant skill and focused regression; title-specific choices stay in title
history. Repeated synthetic rehearsals are not audience feedback or weight
training. Optional growth studies are advisory, and no background automation is
created by this pipeline.

## Readiness terminology

- **Software validated locally:** affected tests and real fixture rendering ran.
- **Private candidate prepared:** actual complete media exists with known scope.
- **Qualified pending decision:** all applicable primary evidence is genuine and
  bound; the one final decision remains outstanding.
- **Production GO LIVE / LIVE:** actual approved destination path is supported,
  release gates pass and customer-visible delivery is verified.

Never collapse these states into a flattering production-ready label. The first
retained candidate is a pilot, and a successful pilot is required before scaling.
