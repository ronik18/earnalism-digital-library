# Rainbow adapter

Explains the familiar primary rainbow as an observer-relative direction of light, not an object with a fixed ground endpoint. The geometry uses Snell refraction at entry/exit and **one partial internal reflection** in an illustrative spherical water drop. Red is outside violet; about 42° is measured from the antisolar viewing direction at the eye. The moving observer selects different stationary droplets. Full-circle visibility requires an unobstructed view with sunlit drops below, staged from actual spoken anchors.

The exit inset is an **eight-times spatial magnification of the same computed rays**. It does not enlarge the refraction angle or change refractive indices to manufacture dispersion. Visible-light indices are illustrative; this is geometric optics, not a wave-optics or intensity simulation. Original sources/rights remain in the episode research package. Primary checks use [NOAA/NWS](https://www.weather.gov/fgz/Rainbow) and the [AMS analysis](https://journals.ametsoc.org/doi/10.1175/BAMS-D-20-0101.1), checked 4 November 2026.

`index.tsx` registers `RainbowLandscape`, captioned `RainbowShorts`, clean `RainbowCleanShorts`, and independently composed `CoverLandscape`/`CoverShorts`. Props are actual body `duration`, seven ordered `scenes` with local actual-word `marks`, timed `captions`, and `outro:true`. `model.mjs` exports the exact scene/mark contract and rejects missing marks, scene gaps and reordered timings. Do not estimate narration anchors.

Operate from the selected Earnalism project, retaining its accepted B baseline and original notebook. With the researched inputs already prepared in `SOURCE_ROOT`, build the disabled notebook using `python3 -m video_studio.rainbow.pipeline build SOURCE_ROOT`. A current owner compute allowance and verified export are required before importing real speech with `python3 -m video_studio.rainbow.assemble import SOURCE_ROOT --archive VERIFIED_ZIP`. Assemble actual words into a **fresh** candidate with `python3 -m video_studio.rainbow.assemble assemble SOURCE_ROOT --output FRESH_CANDIDATE`, then run `pipeline score FRESH_CANDIDATE` through the same module. An unexpected ASR difference stops assembly; the retained literal notation resolution applies only to its exact original archive.

After rendering below, run `python3 -m video_studio.rainbow.pipeline mux FRESH_CANDIDATE FORMAT` for `landscape`, `shorts` and `clean-shorts`; prepare the current music-screen/listening evidence, then `python3 -m video_studio.rainbow.package_preview FRESH_CANDIDATE`. Finally run `python3 video_studio/studio.py check FRESH_CANDIDATE`. This qualifies private integration; listening and the single final release decision remain explicit. The retained Python regression fixtures live in the project production source, not in installed private media. Execute them in project package context: `python3 -m unittest video_studio.rainbow.test_pipeline video_studio.rainbow.test_delivery_resolution`.

Run focused regressions from the project root:

```sh
node video_studio/rainbow/test_model.mjs
node video_studio/rainbow/test_ui_safe_area.mjs
```

These executed checks cover Snell entry/exit, reflection type/order, primary colour order, optical ray bounds, cone angle, fixed-drop selection during approach and sideways movement, actual spatial magnification, conditional circle reveal, contiguous timing, caption-region/label geometry and the complete safe watermark. They do not grant factual, listening, native-platform clearance or publication approval. Authoring stills in `authoring-stills/` use fixture marks and are not synchronized-narration evidence.

For a new assembled candidate, after actual encoded/still review:

```sh
EARNALISM_REMOTION_RUNTIME=/private/tmp/earnalism-rainbow-render-runtime-2026-11-04 \
  node video_studio/rainbow/render-batch.mjs /absolute/path/to/fresh-candidate
```

Use an available exact-lockfile runtime; the dated path above identifies the tested local installation, not a universal default. Default execution may block Chrome launch; request the existing scoped local execution permission rather than weakening browser security. The batch compiles once, uses one explicitly closed headless Chrome, preserves a partial batch instead of overwriting, and records source/prop hashes. It renders three **silent animations** and two covers. Portraits use the tested pinned FFmpeg ident append. `pipeline.py` separately mixes/muxes the current accepted B audio, derives captions and qualifies audiovisual outputs. Never count a silent render as narration integration.

Keep drafts private, original notebooks and accepted voice/audio protected, exact approved emblem and three-second ending unchanged. Use the existing consolidated final decision and publication lane. No upload, spending or model-review permission is implied by this adapter.

## Explicitly selected performance variants

For the owner-selected private rainbow storytelling rebuild only, `assemble.py` accepts an exact source-bound `accepted-voice-direction.json` plus `owner-voice-decision.json`. It validates the accepted audition WAV/metadata, unchanged pinned B model/controls/worker, and the actual source settings before reusing remaining strict checks. It does not change universal narration defaults or supply listening approval. Keep the original baseline and earlier takes.

If the existing cached local turbo aligner is used, retain its actual model/revision and bind each WAV/alignment hash with `create_story_asr_binding`; never relabel recognition as the original large-v3 model. `create_story_display_resolution` permits only the documented exact script-position spelling/number notation differences and preserves raw words/timestamps. A semantic difference still stops assembly. Run `python3 -m unittest video_studio.rainbow.test_storytelling_recipe` for the scoped regressions.

The opening names the rainbow endpoint explicitly in both compositions, retaining the researched question rather than reverting to an ambiguous pronoun. Safe bounds apply at the normal layout font size. An owner-selected short audition remains separate from full-recording and final-candidate acceptance.
