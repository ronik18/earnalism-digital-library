# Audio to private technical storyboard review

This offline adapter preserves a selected complete audiobook recording and
assembles supplied, source-bound illustrations or motion into independent
landscape and portrait review videos. It does **not** infer a book's meaning,
align speech, generate artwork, download/train a model, synthesize narration,
approve quality, upload or publish. The current visual treatment is an honest
illustrated technical storyboard preview, not finished animation or evidence of
cinematic 3D quality. Do not route it as ordinary premium production merely because
technical checks complete. Rich production art/motion and actual storytelling
acceptance remain separate production work.

Use existing FFmpeg/ffprobe and Python 3.11 with Pillow/RAQM. Fonts remain external
hash-bound files; proprietary system TTC fonts are not copied or distributed.
Both Latin and Bengali text use RAQM. Used-character missing-glyph checks help
identify an unsuitable font but do not certify typography or spoken accuracy.

## Commands

From the Studio project directory:

```sh
/opt/homebrew/bin/python3.11 -m video_studio.audiobook_visuals init \
  /absolute/original-audio.wav /absolute/new-plan.json \
  --title 'Book title — selected complete passage' --language bn \
  --cues /absolute/source-cues.json \
  --font /System/Library/Fonts/KohinoorBangla.ttc \
  --logo /absolute/explicit-transparent-full-logo.png \
  --end-landscape /absolute/approved-landscape-END.mp4 \
  --end-portrait /absolute/approved-portrait-END.mp4

/opt/homebrew/bin/python3.11 -m video_studio.audiobook_visuals compile \
  /absolute/new-plan.json --output /absolute/new-compiled.json

/opt/homebrew/bin/python3.11 -m video_studio.audiobook_visuals render \
  /absolute/new-plan.json --output /absolute/new-private-review

/opt/homebrew/bin/python3.11 -m video_studio.audiobook_visuals check \
  /absolute/new-private-review
```

`init` probes the actual recording and binds file hashes. Fill its storyboard and
asset placeholders before compiling. Existing plans, compilations and candidates
are never overwritten. Compilation is deterministic from the bound inputs.

## Exact source cues and semantic storyboard

The cue JSON has `timing_status`, `timing_method` and `cues`. Each cue contains an
ID, `kind` (`narration` or `silence`), integer `start_ms`/`end_ms`, and exact `text`.
Use empty text only for explicit silence cues. Cover from zero through the rounded
actual recording duration, including all leading/internal/final rests. Gaps,
overlaps, reordering and omissions are rejected; the recording is never cut to
fit cues. Scene `cue_ids` must cover every cue once, in order; `source_quote` must
be the exact selected cue texts joined by a newline. The compiler never paraphrases.

`source_reviewed` records supplied timing provenance; it is not a software claim
that speech was independently heard. Keep heuristic, estimated or unresolved
alignment as `estimated` or `unverified`, with an honest method. Such drafts may
render immediately: they carry a visible **PRIVATE DRAFT / TIMING UNVERIFIED**
label and `check` reports `HELD_TIMING_UNVERIFIED` for final release. No additional
creative approval is required to make a private draft.

For a measured whole-unit preview without word/phrase alignment, use the exact
whole source transcript in a full-duration narration cue and set
`caption_mode: "off"`. Record that only the whole-unit boundary is measured.
Caption checks then report `NOT_APPLICABLE`; no subtitle sync claim is made.

Each scene needs an editor-written `visual` and honest `semantic_review`
(`reviewed` or `pending`). Each format asset needs:

```json
{
  "path": "/absolute/supplied-artwork.png",
  "sha256": "actual SHA256",
  "kind": "still",
  "composition": "independently_composed",
  "rights": "Actual source/permission or licence evidence",
  "content_note": "What this exact scene shows and its limitations"
}
```

Supply different independently composed source assets for the two formats.
Assets are fitted whole into separate picture regions, never arbitrarily cropped.
Still holds are labelled as illustrated treatment. Motion must actually cover its
scene using decoded video timestamps/span, not a longer audio/container duration.
Overlays disable repeat-last-frame; no loop, respeed or hidden freeze is allowed. Motion-frame rate
may be sampled to the declared delivery frame grid without changing story time.
Semantic, character/action and anatomical fidelity still require actual review.

## Branding, captions and preserved sound

Bind the real transparent 10:3 full Earnalism lockup and each approved three-second
END explicitly. Production logo SHA must match the canonical `watermarkAsset`
export; an arbitrary transparent image with the same shape/tag is rejected.
No guessed icon, invented END or replacement tagline is generated.

Default canvases are 1920×1080 and 1080×1920 at 30fps. Smaller canvases require
explicit `preview_only: true`, and remain labelled/held as smaller previews.
Each END must match its output dimensions and share exact AAC audio payload.
Matching frame rates use the original video. Exact integer-rate normalization
(such as approved 60fps END to 30fps body) selects every second source frame and
creates a separately recorded standard High-profile yuv420p H264 derivative
(CRF 18, no B-frames, two-second GOP), with AAC copied. The receipt reports
different MP4 bytes, actual profile, source-selected-frame PSNR comparison metrics
and unchanged audio payload. Source decoded-pixel identity is not claimed.
Final exact END frame checks compare against the recorded normalized reference.
Source masters stay intact.
This normalization does not establish native platform compatibility.

A small read-only Node bridge reuses project `branding.mjs` and
`social-safe-area.mjs` for canonical placement, ratio, opacity, blur/halo and
protected-region checks. The baseline separates picture and captions, measures
actual RAQM-shaped glyphs and raster logo pixels, and refuses overflow. Fitting
never shrinks below the existing 1080p caption reference (43px portrait / 36px
landscape, proportionally scaled); correct cue segmentation instead. Conservative
review margins are not certification of every native UI or phone. Inspect the
actual final picture at phone size. No additional video heading is typeset;
source artwork remains entirely within its own picture region.

The selected full original recording is retained unchanged and hash checked.
Compatible AAC is packet-copied. Otherwise one explicitly recorded AAC derivative
preserves the complete source, with no speed/level edits and only a documented
trailing subframe alignment pad. It is shared identically across both formats.
That derivative may resample or apply FFmpeg's default channel mapping to match
the bound END. Actual source/output formats, sample-rate and channel conversion
are reported; downmixed/resampled AAC is not preserved PCM. Channel conversion
still needs perceptual review, even when all packet/hash checks complete.
Original intentional rests remain intact; no new score or narration is created.
The bound END audio packet payload is preserved. Complete decoded ending frames
are compared with each bound original or its explicitly recorded normalization
reference after assembly. AAC derivative status is
reported instead of claiming byte-identical source audio.

## Receipts and limits

The new review folder includes `compiled.json`, the copied source plan, original
audio, shared AAC, SRT/VTT, measured layout receipts, both MP4s, a private HTML
player, manifest and `technical-receipt.json`. The check performs actual full
decodes, exact hashes, frame counts, identical shared AAC payload and decoded END
frame comparisons. It does not produce an artistic, semantic or listening PASS.
No publication is authorized; use the existing one-decision release workflow
after full listening/AV, factual/semantic, art and actual delivery review.

Focused offline tests (tiny synthetic fixtures, not real production evidence):

```sh
/opt/homebrew/bin/python3.11 -m unittest video_studio.audiobook_visuals.test_pipeline -v
```

Tests select an existing Mac Arial/Kohinoor Bangla font or Linux DejaVu Sans/Noto
Sans Bengali font. Override paths with `EARNALISM_TEST_EN_FONT` and
`EARNALISM_TEST_BN_FONT`. Linux CI provisions `fonts-dejavu-core` and
`fonts-noto-core`, FFmpeg and a Pillow build with RAQM before the test command.
Missing prerequisites are explicit errors, not an all-skipped green run. The
tests never download fonts or copy proprietary system fonts into the repository.
