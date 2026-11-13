# Supplied English/Bengali audiobook → private visual production

Use this route when the input is an existing audio/audiobook. It overrides the
ordinary English/~90-second/new-B explainer defaults: retain the supplied language,
narrator, complete selected recording, score, rests and duration. Never silently
translate, condense, synthesize a new voice or change speed/gain to fit pictures.
Select an excerpt only when the brief calls for one, recording its original sample
range and retaining the full source. Reuse source-bound rights and actual listening
acceptance within their scope. This route adds no upload/publication authority.

## What is implemented and what remains editorial

`audiobook_visuals` is an offline source-bound compiler/renderer for supplied audio,
exact timed cues and an editor-written storyboard. It accepts English and Bengali,
measures actual media clocks and glyph bounds, and assembles independent landscape
and portrait **technical storyboard previews**. It can place retained stills or
motion which actually spans a scene. It is not automatic speech recognition, book
understanding, a character model, artwork generation or a completed cinematic film.
Do not promote its card treatment as the owner's requested lively human animation.

Codex remains the coordinator: read the eligible source, identify character and
setting continuity, split by actual narrative beats, commission/source the artwork,
write action/feeling directions, inspect raw motion and assemble the approved shots.
For a long book, process chapters incrementally and reuse accepted bound assets;
never load the whole book into one generative-video request. A first chapter cannot
qualify unreviewed later chapters or every future book.

## Minimal production sequence

1. Bind the original audio, eligible source/rights, exact transcript and scope. Probe
   actual duration/channels/sample rate. Preserve the source and any existing score.
2. Use actual source-bound phrase/paragraph cue evidence. Represent rests explicitly;
   do not infer word timestamps from character offsets or divide duration by words.
   Unresolved timing may render immediately as a visibly labelled **private draft**;
   it remains unresolved for a captioned release. A whole-unit technical preview can
   use `caption_mode: off`, with captions `NOT_APPLICABLE` and no sync claim.
3. Write a semantic shot plan with exact source quotations, acting subject, action,
   emotional change, continuity, composition and required asset. Separate what is
   narrated, what is visibly performed and what is merely proposed. Use complete
   purposeful action rather than moving every element or stretching one short clip.
4. Prepare independent wide/portrait assets. Bind their hashes, source/rights and
   limitations. The baseline fits artwork whole; do not force arbitrary crops,
   loop short motion or hide missing coverage with repeated final frames. Use the
   existing rich production renderer when that is the appropriate finished treatment.
5. Compile and render privately. Inspect both layouts at phone size, including all
   face/eye/hand edges, action extrema, captions, full-logo halo and transitions.
   Reuse genuine listening for identical audio while checking each visual timeline.
6. Keep one manifest-bound final decision and the existing factual/rights/quality/
   actual delivery checks. Technical decode/hash success is not hearing or AV approval.

## Offline interface

In the existing Studio, with Python 3.11, FFmpeg/ffprobe, Node and Pillow with RAQM:

```sh
python3 -m video_studio.audiobook_visuals init ORIGINAL.wav NEW_PLAN.json \
  --title 'Actual book — selected passage' --language bn \
  --cues SOURCE_CUES.json --font /absolute/licensed-bengali-font.ttf \
  --logo /absolute/approved-transparent-full-logo.png \
  --end-landscape /absolute/approved-landscape-END.mp4 \
  --end-portrait /absolute/approved-portrait-END.mp4
python3 -m video_studio.audiobook_visuals compile NEW_PLAN.json --output COMPILED.json
python3 -m video_studio.audiobook_visuals render NEW_PLAN.json --output NEW_PRIVATE_REVIEW
python3 -m video_studio.audiobook_visuals check NEW_PRIVATE_REVIEW
```

Fill `init`'s semantic and asset placeholders before compiling. Existing candidates
are never overwritten. See `software/audiobook_visuals/README.md` in the portable
source package, or `video_studio/audiobook_visuals/README.md` in Studio, for the cue
and scene schema. From a source-only repository checkout, change to `skills/earnalism-video` and use
`python3 -m software.audiobook_visuals`.
The source archive contains no approved media or fonts; provision existing qualified
private assets, never fabricate them to make a clean checkout render.

Default delivery canvases are 1920×1080 and 1080×1920 at 30 fps. Smaller previews are
explicitly labelled, not called final HD. The canonical transparent full lockup,
blur/halo, destination-safe anchor and actual occupied-box checks are shared with
existing renderers. Captions wrap at readable reference sizes; overflow requires
resegmentation rather than shrinking to illegible text. Bengali needs real font
coverage and RAQM shaping. Bind an appropriately licensed external font; do not
bundle a proprietary system font. A readable glyph test does not establish correct
pronunciation, narration fidelity or measured timing.

Original audio bytes remain retained. Compatible AAC is copied; other sources use
one declared complete AAC delivery derivative shared across both formats, without
new score, speed/level edits or silent source replacement. When sample rate/channel
layout must match the END, explicitly record the conversion and review its result;
a downmix is not unchanged source PCM or a proven unchanged perceptual balance.
Record codec/alignment padding precisely. Bind the approved three-second END separately; preserve its own
sound and exclude body-score bleed. If a frame-rate delivery derivative is needed,
record its original and derivative hashes and actual comparison rather than claiming
source-pixel or MP4 byte identity after re-encoding. No new creative approval is
invented for ordinary private encoding; actual final quality checks still apply.

## Warm visual generation queue

The separate `wan22.batch` schema accepts arbitrary safe scene IDs and immutable
source-image/model/revision/profile/seed/prompt bindings. It reuses one loaded
pipeline for sequential shots, checkpointing each attempt and completed output.
Planning, asset preparation and already completed-shot assembly can run in parallel.
Do not run multiple inference processes on the same GPU; the shared worker/batch
lock prevents that collision. Additional GPUs need provider-supported capacity and
specific remaining compute authority, not a blanket assumption of unlimited scaling.

The generic disabled notebook builder is `wan22.build_batch_colab`. Build locally
from an already bound batch job and sources. Verify the exact source pack before
setup; supply actual owner/free-runtime authority and the original allocation clock.
The notebook supervises one warm process, exports completed clips and retains the
original deadline timer requesting runtime unassign; verify actual provider release. Run All with defaults performs no install/download/model
work. Do not copy an exhausted single-shot allowance into a new queue.

`wan22.batch` CLI actions are `validate`, `preflight`, `begin`, `setup`, `run`,
`status`, `export`, `unpack` and `import`; consult `--help`. Setup/run are inert without
`--execute`. A resumed process skips only cryptographically verified completed shots;
failed or interrupted starts stay in history and are not rerolled automatically.
The original deadline, explicit attempt/output/CU ceilings and export reserve remain
fixed through reloads and delays. The queue itself does not enforce provider billing
or shutdown: retain the supervising runtime guard and actual release verification.

The pinned 5B route does not enforce `last_image`/`end_image` conditioning. Reject
those inputs rather than claiming a target final pose. Offline control-plane/media regressions pass; the real warm-GPU implementation
remains **UNQUALIFIED pending a newly authorized real benchmark**. No measured cost/throughput or universal face/action stability follows
from injected test backends. Existing reviewed single-shot evidence remains scoped
to its exact source/output. Do not train on supplied audiobooks or send them to a new
service without applicable authority and rights.

## Quality and efficiency that carry forward

- Review faces/eyes and hands throughout motion at delivery size, including every
  frame around a suspected break. Resolution/sharpening/prompt promises do not fix
  identity drift. A stable face alone does not prove a completed action or emotion.
- Ask for one readable action and a legible emotional progression. Score performed
  action, timing and anatomy separately; report partial adherence truthfully. Reuse a
  clean source-bound interval only if it serves the narrative without a hidden freeze.
- Reuse a warm model, source-bound assets and accepted audio. Parallelize independent
  planning/assembly rather than regenerating voices or loading multiple models on
  the same constrained GPU. Durable transfer is part of completion, not a toast.
- Keep book text, recordings, private analytics, accounts, fonts, notebooks, generated
  media and runtime receipts outside the reusable Git skill package. Track source,
  generic templates, focused tests and a compact material changelog only.

Official implementation sources checked 14 November 2026:
[Wan2.2](https://github.com/Wan-Video/Wan2.2) and the pinned
[Diffusers 0.36.0 Wan pipeline](https://huggingface.co/docs/diffusers/v0.36.0/en/api/pipelines/wan).
These document the model/API, not this project's cinematic quality or throughput.
