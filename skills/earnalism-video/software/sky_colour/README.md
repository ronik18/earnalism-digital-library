# Sky-colour animation adapter

Original clear-air explanatory vectors for episode06. This is not a relabelled Moon, thermal or condensation mechanism. `model.mjs` computes the fixed observer’s ray intersection with a fixed concentric atmosphere shell on every frame. The low-Sun path is longer without passing through Earth or changing shell thickness. The prediction stage uses only a white path-following comparison highlight, not coloured transmission decisions or simulated photon speed; coloured redistribution is revealed in the following explanatory beat. Packet wavelengths/colours remain assigned through redirection; shorter wavelengths are redirected more often in the explicitly illustrative packet scheme, while other colours also scatter. Violet is represented and not falsely declared absent. No packet counts or arbitrary transmission numbers are shown as measured data.

Sun glyphs representing the upstream source remain white. The warm Sun in the opening/closing environmental vignette is its appearance through a longer atmospheric path, not an emitted-Sun colour change. The sunset field retains blue overhead. The blue-sky scene uses a clearly labelled conceptual receiver, with an incoming route redirected from an off-Sun air patch; the direct route is faint/unhighlighted. No person is shown staring at the Sun. Keep the solar safety and fuller schematic limitations in the existing player/metadata context, not a new persistent video footer.

## Contract

Props match the current six-scene studio pattern:

```
{duration, scenes:[{id,scene,start,end,marks}], captions:[{start,end,text}], outro:true, burnCaptions:false}
```

`duration` is the actual body audio duration. `start/end` and every mark must come from verified actual-audio alignment. Six scene kinds, in order:

| scene | required relative marks | spoken anchors |
|---|---|---|
| question | question, light | “Same Sun, so what changed”; “what happens to its light” |
| scattering | mixed, redirect, shorter, red; optional scatter | “mixture of visible colours”; first cause “scatter some of that light”; “they redirect it”; “Shorter wavelengths”; “than red” |
| sky_path | away, toward, direct | “away from the Sun”; “scatter toward you” in the accepted delivery; “coming straight from the Sun” |
| prediction | lower, longer, predict | “lower the Sun”; “a longer stretch of atmosphere”; “What do you think” |
| sunset_path | scatter, warm, identity, mixture | “More blue light”; “more orange or red”; “Blue light has not turned red”; “mixture reaching us” |
| callback | variation, sky, direct, callback | “clouds and particles”; “blue sky is scattered sunlight”; “a red sunset Sun”; “Same Sun. Different paths” |

`assertTimeline` rejects absent/out-of-range marks or reordered/discontinuous scenes. The renderer contains no inferred narration timings. `bodyFrameCount(duration,30)` pads only to the next frame; the unchanged approved nonverbal end ident adds90frames. `BrandWatermark` reuses the unchanged exact emblem. No soundtrack is encoded here.

Compositions: `SkyColourLandscape` (1920×1080 clean), `SkyColourShorts` (1080×1920 burned captions), `SkyColourCleanShorts` (1080×1920 clean), `CoverLandscape`, `CoverShorts`. Each arrangement has a dedicated diagram, support and caption region. The independently composed portrait layout never crops the landscape explanation.

```
node video_studio/sky_colour/test_model.mjs
node video_studio/sky_colour/test_render_startup.mjs
node video_studio/sky_colour/test_sync_anchor.mjs
python3 -m unittest video_studio.sky_colour.test_production video_studio.sky_colour.test_delivery_revision -q
python3 -m unittest video_studio.sky_colour.test_sync_anchor video_studio.condensation.test_audio_review -q
node video_studio/sky_colour/render-batch.mjs FRESH_ASSEMBLED_ROOT
node video_studio/sky_colour/render.mjs ACTUAL_PROPS OUTPUT.mp4 SkyColourLandscape
node video_studio/sky_colour/render.mjs ACTUAL_PROPS OUTPUT.png SkyColourShorts FRAME[,FRAME...]
```

Set `SKY_COLOUR_FRAME_RANGE='[FIRST,LAST]'` only for a clearly labelled engineering/repair range. Render outputs refuse overwrite. A silent render establishes no narration integration. Combine actual sound through the parent’s strict mux/manifest workflow, preserving its common encoded audio for all formats.

## Checks and scope

Tests sweep shell/ray intersections and the complete high→low trajectory, fixed observer/shell, off-Sun receiving angle, wavelength/colour identity, non-blue scattering, remaining blue, exact renderer label backplates and their movement clearances, and caption-region separation. These engineering checks do not certify final narrow-player label reading, narration sync, listening, rights, native platform caption layout or publication acceptance. Inspect current encoded scenes with real captions before claiming those results.

Current illustrative geometry omits density gradients, atmospheric refraction, ozone absorption, multiple scattering and cloud/aerosol microphysics. “Atmosphere exaggerated” marks the model introduction. It is not a quantitative photometric, spectrum or air-mass simulation. Do not transfer its dimensions or symbolic packet choices into a universal scientific default.

The renderer loads the bundler through its public CommonJS entry point. Early CLI validation precedes renderer dependency loading; a bounded startup regression tests invalid/partial attempts without starting Chrome. Actual still/render runs separately verify dependency and browser operation. Stage messages distinguish dependency startup, bundling, composition selection and rendering. No package downgrade, cache deletion or unrelated process termination is required.

For a new complete set, `render-batch.mjs` builds once and reuses one explicitly closed rendering browser for the three actual-props formats. Its lock rejects an existing/partial attempt before compiling. `render-batch.json` records source/props hashes, frame counts and animation hashes. These remain silent engineering outputs until the unchanged narration/common soundtrack is muxed and verified.

The optional first-scatter anchor is declared as a unique spoken phrase in the fresh scene inputs, then derived from actual aligned words; it must lie between the mixed-light introduction and redirection restatement. Old timelines retain their prior onset. Essential-label tests account for the nested SVG scale at this episode's intended narrow player; the numerical font/player sizes are not universal defaults. The fresh score master uses measured constant gain rather than an adaptive loudness curve after its authored rests. Read the exact provenance and retain raw music flags with authored context; none of these checks grants listening or publication acceptance.


## Opening and packaging refinement

The opening uses its actual spoken question anchor to reveal the shared white source, then its actual light anchor for travel cues. Both environmental appearances are visible on frame zero; later explanatory physics and the callback retain their own tested scenes. The two cover compositions use dedicated small-readable comparison layouts, not still frames. Keep the sunset artwork clipped to its rounded card and use the padded uppercase panel-label layout rather than the smaller scientific-label estimate. `test_opening_cover.mjs` protects these relationships; inspect actual encoded output and small cover/profile crops as well.

Fresh packaging writes distinct accurate landscape/Shorts titles and Instagram copy while retaining exact speech captions, sources, plain disclosure and both brand hashtags. `test_growth_copy.py` protects the caption strategy and pending private-delivery settings. These changes are packaging hypotheses, not demonstrated retention, follow or revenue gains.


## Organic portrait interface reservations

The portrait body reflows the heading, mechanism, support and full-size speech captions inside the configurable `src/social-safe-area.mjs` review profile. The exact emblem has an explicit inner placement and the unchanged silent ident asset is reframed into the same content area. Landscape and cover compositions retain their separate layouts. The reserved bands are a conservative Earnalism design profile derived from observed organic mobile overlays, not official Instagram/YouTube dimensions or a guarantee for every crop/device. Inspect all heading states, the longest actual cue, moving-label extremes and ending with a labeled simulated mask, then verify the actual consumer surface during authorized delivery.

Run `node video_studio/sky_colour/test_ui_safe_area.mjs`. For a portrait-only visual repair, `render-batch.mjs FRESH_ROOT --portrait-only` renders the two portrait masters and can retain an already hash-verified unchanged landscape; final packaging still requires all three completed technical records. The batch records the shared safe-area/watermark dependencies as well as topic source hashes and explicitly closes its browser. No audio is rendered or changed by this mode.

The observed local `OffthreadVideo` proxy request timed out on the pinned three-second portrait ident. The authoritative batch now renders portrait body frames with `outro:false`, then `append_ident.py` uses FFmpeg to reframe the exact pinned ident, append exactly90 visual frames and copy H264 body packets. Full audio is still muxed from the protected common AAC afterward. A real silent FFmpeg fixture checks frame count/duration, no competing audio and refusal to overwrite; it does not establish narration integration. Keep a proxy failure scoped to its observed extraction stage rather than attributing every slow import or bundle to it. The interactive Remotion component retains its standard ident preview; use the qualified batch for portrait delivery.

If the existing dependency tree cannot be read reliably, preserve it. A separate `npm ci --ignore-scripts --no-audit --no-fund` installation from the exact project package.json/package-lock can be selected with `EARNALISM_REMOTION_RUNTIME`. `src/render-runtime.mjs` rejects any of the five actual package versions that differ from the authoritative pins, uses public package exports and sets the matching bundler root. Do not upgrade libraries, delete caches/project files, or weaken a timeout/release gate to make a stalled import look successful. Record the isolated path/lock digest; recreate it from the same lock if an ephemeral directory is gone. `src/test_render_runtime.mjs` checks mismatched-runtime rejection; actual still/render runs verify the real dependency/browser path.

Final portrait-ident finishing removes only the empty outer decorative border, scales the pinned lockup into the reserved central area and extends background edge pixels. Keep the complete moving emblem, lettering and paired hop. Inspect beginning/middle/end pixels; a smaller portrait video pasted over a flat canvas can create an unwanted inset box even when its bounds pass. Reuse exact body frames for an ending-only correction rather than rerendering the lesson.
