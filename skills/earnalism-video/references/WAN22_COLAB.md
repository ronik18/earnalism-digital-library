# Wan2.2 Colab motion adapter

Use when natural illustration/character motion is needed and the selected hosted provider is unavailable, or the owner chooses self-hosted Wan. The control plane is locally tested and the demonstrated Diwali portrait and landscape jobs have completed on an L4. Successful inference/import does **not** qualify every pixel, new scene, profile or production replacement; review actual clips and delivery composites. Preserve selected narration, original notebooks, earlier candidate media and their manifests.

## Build and open

The initial pilot is deliberately scoped to two Diwali scenes: homecoming and sweets. It uses the existing portrait art, not new narration or a talking avatar. Do not relabel this job as another episode; give a future episode its own isolated job/root/input hashes and relevant prompts.

```sh
python3 -m video_studio.wan22.build_colab output/wan22/diwali-pilot-v1 --art video_studio/diwali_v8/public/art
python3 -m unittest video_studio.wan22.test_workflow -v
```

The builder outputs a disabled Colab notebook, a separate ZIP of the two source images plus job, and hashes. No model is downloaded or executed by building. Upload these exact artifacts privately to Drive/Colab only with scoped payload/destination authority; do not make public links or mount all Drive. Update existing known file IDs instead of repeatedly creating copies. Verify MIME/name/size and permission metadata after upload.

## Verified Colab transfer and bootstrap lessons

The 7 November pilot used an L4 with23034MiB VRAM and Python3.13.16. The output-frame `files.upload()` picker did not raise a usable chooser; Files → Upload to session storage worked. Prefer the sidebar and let the upload cell verify `/content/wan22-inputs.zip` against the exact archive hash. Do not mount Drive or weaken extension permissions to work around this picker. An existing wrong-hash file is a hold, not permission to overwrite it.

The standard-library `venv` failed in Colab `ensurepip`; the pinned `virtualenv==20.35.4` bootstrap repaired the isolated environment while inheriting the current PyTorch. Python3.13 also failed the sentencepiece0.2.0 source build; sentencepiece0.2.1 installed as a compatible wheel. Validate the pipeline imports before downloading weights. These are verified setup lessons, not evidence of successful motion generation. Keep the original allocation deadline through setup repairs. A control archive was durably recovered and hash/import verified before inference; notebook download initiation alone did not yield a local file. Use the supported hashed transfer recovery when needed.

## Measured L4 result and budget forecasting

The 7 November bounded pilot completed dependency setup and model loading, but produced **no completed clip**. In its first 704×1280/121-frame/50-step attempt, the visible log reached2/50 steps at31.09s/step, estimating24:52 remaining. The original session had about11minutes left, so the attempt was deliberately interrupted and recorded `FAILED_NO_AUTOMATIC_RETRY`; the second scene was not started. Colab subsequently showed0 active sessions and0 CU/hour. This is an early-step observation, not a completed-run benchmark or a motion-quality result. Do not advertise two standard clips as a proven30-minute L4 workflow.

The initial worker forecast used two steps, a15percent margin,45seconds for decode and a separate120-second export reserve. The optimized retry exposed a warm-up bias in that estimator; the corrected rule below supersedes it. If it cannot fit, it fails the existing attempt without retry or deadline reset. The original callback ran live in the optimized retry; the corrected callback subsequently completed the selective sweets recovery below. A future reduced-resolution/shorter/accelerated route needs its own prepared job, validated model/pipeline compatibility and scoped compute authority; do not silently reduce this job or borrow unused allowance after shutdown.

The final full audit ZIP was created but not durably imported: automatic downloads stalled, and a direct data-URL recovery link was rejected by browser URL policy. Do not work around such a rejection using another browser surface or encoded archive extraction. Preserve visible observations separately and report the missing raw archive honestly. Only the earlier small control ZIP was durably hash/import verified. An export/download click is not delivery evidence.

## Optimized bounded retry profile

For the owner's fresh5CU/30-minute retry, use `--profile l4-balanced-v2`. It creates `diwali-wan22-pilot-v2` in a separate runtime root, retaining prior failed-attempt provenance. It keeps the exact model revision, input hashes, seeds, guidance5,121frames/24fps and two-start/11second limits, but uses512×896 and24steps. This is a performance/quality tradeoff to review in actual playback, not a qualified production default. The standard-v1 job remains unchanged and importable. Shape and step settings are profile-bound; never relabel an existing attempt or silently alter its job.

Use only the PyTorch backend (`USE_TF=0`, `USE_FLAX=0`) in isolated subprocesses; these supported Transformers flags avoid unrelated backend initialization. Export ZIPs use standard DEFLATE to reduce log-transfer size. Neither change grants model/voice/provider authority.

The retry's normal `files.download()` control transfer was durably verified after completing Chrome's native Save dialog. If the Colab cell finishes but no local file appears, inspect the native browser dialog before declaring a transfer failure. Complete only the task's expected filename; preserve existing files and unrelated windows. Await input-upload completion and verify the exact source hash before setup; returning from a file chooser does not establish transfer completion. A Playwright download-event timeout alone does not prove download failure. Verify local bytes/hash after saving. This supported route does not require data URLs, permission changes or broad Drive access.

References: [pinned pipeline input and denoising contract](https://github.com/huggingface/diffusers/blob/v0.36.0/src/diffusers/pipelines/wan/pipeline_wan_i2v.py), [pinned Transformers backend flags](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/utils/import_utils.py). The512×896 shape satisfies the pinned pipeline's16-pixel divisibility requirement; lowering steps is an engineering choice, not a claim of equal quality.

## Optimized retry outcome and corrected forecasting

The optimized retry generated one real homecoming MP4:512×896,121frames at24fps,5.041667seconds,H.264/yuv420p, silent. Its end-to-end generation took476.34seconds; visible steady denoising was about11.3–11.5seconds/step. The full final archive, member hashes, job/model/source bindings and full decode were locally verified, including the failed second attempt's logs. Sampled homecoming frames retained the painted palette and three principal figures while showing a welcome gesture. Full perceptual playback acceptance remains separate from technical completion.

The sweets attempt was stopped by the original forecast after two callbacks: it reported37.34seconds/step and990seconds projected, because prompt/first-step warm-up was incorrectly multiplied by the remaining steps. The attempt remains failed and reserved; no automatic reroll or history reset. The fresh allocation was disconnected within about22.5minutes; Colab showed0 active sessions and0CU/hour. These observations qualify one generated technical pilot, not two finished clips or production quality.

The corrected forecast starts measuring at the first completed step and averages the last three **inter-step intervals**, waiting for at least two intervals. Warm-up still consumes the absolute session deadline but is not repeated in the rate estimate. Retain15percent timing headroom, an initial180-second decode allowance and the separate120-second export reserve. The larger decode allowance is conservative for this pilot, not a universal Wan guarantee. Regression checks cover both long warm-up with feasible steady steps and genuinely infeasible steady inference. This corrected rule subsequently completed the authorized sweets-only live run described below; the attempt cap and original deadline still govern.

File previews can cache an older log: do not infer current completion from a stale open preview alone. Prefer the actual notebook attempt result or a live terminal read. Confirm actual file bytes after a normal download before repeatedly requesting it; a save can complete asynchronously without another dialog. Preserve duplicate downloads rather than deleting them without need.

## Selective recovery and integration

When the owner authorizes a fresh retry of sweets while retaining completed homecoming, build a new run/root using `--run-id`, `--scene sweets` and `--prior-evidence PATH`. The evidence must retain the prior archive/clip hashes and failed-attempt status. The generated job has one scene, one start and at most6seconds reserved output; the homecoming cell is inert and directs reuse. The input archive contains only the selected source image and job. This is a new explicitly authorized recovery, not an automatic retry or a reset of the prior journal.

The input cell now requires a completed Files-sidebar upload at `/content/wan22-inputs.zip` before hash verification. Do not automatically fall back to an output-frame picker when that path has not appeared; a second picker obscures which file is being checked. A missing or partial upload remains a setup hold, and generation must not start until the exact source binding passes.

For production integration, preserve raw clips and normalize a derivative to30fps/H.264/yuv420p/BT709 with an explicit frame count. The current121-frame24fps source is5.041667seconds; its151-frame30fps working derivative is5.033333seconds. Record this trim rather than describing both as exactly5seconds. Freeze the actual last frame for any remaining narrated interval instead of looping the action or returning abruptly to its original pose. Compose portrait and landscape separately; a landscape crop must retain the story's faces, hands and contact, with captions and complete branding outside the action. Source resolution remains512×896 even when delivery is1080p.

The bundled `wan22/splice.py` accepts silent30fps replacement intervals, validates dimensions/counts/non-overlap and preserves the assembled total frame count. It re-encodes video; it does not claim unchanged encoded video bytes. Remux the exact existing AAC soundtrack separately and verify its packet hash plus unchanged PCM WAV masters. Render/review changed boundaries and watch each full assembled format, including the ending. A source clip or segment technical pass does not qualify the full movie or confer publication authority.

## Verified selective sweets recovery

A separately owner-authorized v3 job used only the retained family illustration, seed702 and the same512×896/121frame/24step profile. The corrected inter-step guard ran through all24steps and completed the raw5.041667-second sweets MP4 in495.04seconds. The archive, source binding and full decode were verified locally. Raw playback reached5.04seconds; reviewed frames retain four family identities, a supported plate and the girl's reach for a sweet. This supports use in the private edit, not a claim of perfect anatomy or publication acceptance.

The L4 was released after16.22minutes including setup and export; actual Colab UI showed0 active sessions and0CU/hour. No purchase or upgrade. Retain both v2 journals and the v3 journal. Do not regenerate homecoming when recovering sweets. These two completed clips establish this bounded profile's usefulness for the demonstrated scenes, not universal runtime/quality guarantees for other images or GPUs.

## Verified Diwali integration lessons

The private v9 edit places homecoming at frames412..706 and sweets at1961..2146 inclusive in each30fps format. It retains the remaining v8 scenes and ending, and delivers2489frames per movie. All three assembled H.264/AAC exports passed full decode, duration, fast-start and stream checks. AAC packet hashes are identical to v8 in each format; PCM WAV masters, word timings and captions are byte-identical. Preserve this evidence when video-only edits leave narration unchanged.

For family interaction in landscape, an independently composed crop retains all four faces and the shared plate; the same painted scene supplies a soft background extension. Inspect hands/contact and caption clearance in the actual output, not only the portrait source. Preserve the generated action's true end frame through a restrained hold, rather than looping a reach or snapping a character back. This is a delivery technique, not added natural action or restored source detail. Full playback and primary listening/pronunciation acceptance remain separate checks.

## Model and execution contract

- Official weights: `Wan-AI/Wan2.2-TI2V-5B-Diffusers`, revision `b8fff7315c768468a5333511427288870b2e9635`; Apache2.0 model metadata. Preserve source/licence notices.
- Explicit `WanImageToVideoPipeline`, with `expand_timesteps=True`, VAE float32, transformer bfloat16, CPU offloading and VAE tiling. The model's default metadata names `WanPipeline`; blindly using the auto text-to-video class can lose the image-conditioning route. The pinned Diffusers0.36.0 source supports the image argument and 5B timestep expansion.
- Pinned Python dependencies in `wan22/worker.py`; isolated venv inherits compatible Colab PyTorch>=2.4 and records actual dependency versions. Use PyTorch SDPA, avoiding FlashAttention compilation. No prompt-extension API, TTS, billing API or provider purchase.
- Each of two scenes:704×1280,121frames at24fps (~5.04s),50steps and fixed seed. Reserve at most11output seconds and two starts. Actual generated duration is frame-count/fps; do not call121/24 exactly5seconds. These pilot limits do not reset historical provider usage or confer new paid authority.
- Conservative standard-route preflight: one bf16 CUDA GPU with23000MiB or more VRAM (nominal24GB class),28GiB host RAM and55GiB free disk. Reject smaller/T4 allocations before installation/download. These are adapter gates, not measured universal Wan hardware minima. Lower-memory quantized variants need separate preparation and validation.

## Compute and resume

Default controls are all disabled, with zero metered allowance. Confirm the actual Colab allocation and rate before starting. A disconnected account's zero usage rate is **not proof that its prospective GPU is free**. A general request to use Colab, a Pro subscription or remaining compute-unit balance is not a scoped paid allowance.

The worker supports confirmed free mode or a separately authorized bounded pilot of at most5 existing CU and1800seconds, with twice the observed-rate headroom. In metered mode record the actual allocation start, including startup; inspect balance/rate after setup and each clip, and stop on insufficient headroom. Never increase the owner limit, buy units or upgrade. A wall-clock watchdog is a safeguard, not a provider-enforced CU cap or automatic live billing monitor.

Install the runtime-unassign timer before hardware checks/setup. Preserve the job hash, original deadline and attempt journal. A started/failed scene cannot be silently restarted or overwritten; inspect its partial export first. Reusing clips or reopening a notebook does not reset caps. The local-ledger guarantee applies within the retained run directory; an erased Colab disk cannot reconstruct history. Re-import preserved journals and source evidence before any explicitly authorized recovery; never represent a fresh disk as an untouched first attempt.

The guard covers setup/downloads, inference and transfer. Failures retain logs and partial exports. Do not extend a guard to compensate for a slow download. Do not leave the sole media copy on an ephemeral runtime. For an observed download problem, prove complete supported transfer with a small control before metered inference, and use the existing `colab_transfer.py` hashed-chunk recovery if needed. After durable verified import, disconnect only this notebook, verify no active runtime/usage, and restore saved controls todisabled/zero. A kernel restart is not shutdown.

## Import, review and assemble

```sh
python3 -m video_studio.wan22.import_clips /absolute/path/wan22-export.zip output/wan22/diwali-pilot-v1/imported --sha256 ARCHIVE_SHA_FROM_COLAB --job output/wan22/diwali-pilot-v1/job.json
```

The importer checks archive/member hashes, paths, job/model/source bindings, attempt budget and current media streams/frame count/full decode. It preserves raw clips, logs, failures and provenance and refuses destination overwrite. Invalid/unbound clips remain rejected in the receipt. Successful import is technical evidence only: `motion_accepted` remainsfalse and publication is unapproved.

Review real movement for identity drift, hands/plate contact, coherent action, sacred-story portrayal, painted-style consistency and intended portrait/landscape crop. Do not equate pans, still images, interpolated frames or a completed inference job with natural animation. Reject artifacts instead of hiding them with fast cuts or calling the model qualified. No automatic reroll.

After a clip is accepted for the edit, derive a silent H.264/yuv420p/BT709 working copy at the production frame rate, record original dimensions/fps and any trim/crop, and integrate in a **new** candidate through the existing renderer. Preserve the accepted narration, AAC soundtrack, timing and PCM WAV masters. Check the entire assembled ending, synchronization, both formats and canonical private/release gate. Keep one consolidated final decision; this adapter grants no publication authority.

## Primary references

- https://github.com/Wan-Video/Wan2.2
- https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers
- https://github.com/huggingface/diffusers/blob/v0.36.0/src/diffusers/pipelines/wan/pipeline_wan_i2v.py
- https://github.com/huggingface/diffusers/issues/13258

## Measured native-landscape pilot

The separately owner-authorized `l4-landscape-v1` job used a source-bound wide family illustration,896×512,121frames/24fps,24steps, guidance5 and one sweets start. It completed in477.75seconds on the observed L4; the runtime was released after14.74minutes including setup/export/import confirmation. The complete archive and source/job/model bindings passed local import and full decode. No purchase or upgrade. This one observation is not a guarantee for another scene/GPU or equal quality at another resolution.

Full raw playback reached5.04seconds. The four principal faces and initial plate support were retained, but the enlarged delivery composite exposed late tray-underside geometry drift. The raw clip is **not accepted wholesale**. The edit uses the first80 normalized30fps frames wide, then a sustained512×288 reaction crop at source(192,20) for frames80..150, excluding the unstable object region while preserving the video time cursor. A35-frame source-start establishment precedes the151-frame action. Record accepted/rejected regions and the actual crop; do not label the entire raw clip clean, call a still additional natural action, or conceal defects behind rapid cuts. If the remaining regions do not form a truthful coherent edit, reject the replacement and preserve the prior candidate. Reaction detail remains soft when enlarged; delivery resolution is not generated detail.

Author the source illustration for the intended aspect ratio before generation. Reuse an already-reviewed portrait export when a landscape-specific improvement does not change it; verify exact bytes and reuse its existing playback evidence. Review the changed landscape movie completely, including the preserved ending, and verify unchanged AAC/PCM narration. A pleasing raw thumbnail or successful inference is insufficient for contact/anatomy acceptance at delivery size.

When other account sessions are active, record account aggregate usage separately from this pilot's observed rate and stop only this notebook. The demonstrated run began with another session at1.15CU/hour; the aggregate rose to3.09, then fell to1.94 when that other session ended without agent action. At pilot shutdown the UI showed0 active sessions and0CU/hour. Account balance fell0.44CU over the period, including the initially concurrent session; this is not a pilot-only invoice. Restore the saved notebook to disabled/zero controls after durable import and shutdown, while retaining the consumed attempt journal.


## Bind revised action sources before a new pilot

For a newly authorized refinement, pass `--scene-spec scene-spec.json` with known scene IDs mapped to required `image` (a local basename) and `prompt`, with optional `frame_profile`. A distinct `--run-id` and retained `--prior-evidence` are required. The builder hashes the actual new artwork, puts only bound inputs into the ZIP and embeds that exact job into the disabled notebook. This prevents a revised greeting illustration from silently inheriting an older head-nod prompt. Runtime/attempt caps, reviewed profiles, model revision and inert defaults remain unchanged. Tests cover new source/prompt binding, archive import, disabled controls and unsafe/relabelled inputs. A prepared prompt does not prove the action was generated successfully.


## V12 action-specific result and honest selection

The fresh two-start Diwali pilot completed two896×512/121-frame24fps clips at24steps: homecoming484.71seconds and family response499.95seconds. Both archives passed source/job/model binding and full decode. The original allocation deadline remained fixed; shutdown was observed before a local receipt taken24.79minutes after allocation request. Colab showed0 active sessions and0CU/hour; displayed balance363.06→362.42CU is an account observation, not a provider invoice. Saved notebook controls were restored toFalse/zero and read back.

The generated homecoming failed the intended namaste action and was rejected despite technical completion. Its replacement is explicitly a quieter illustration. The family source starts with the girl already supporting the flat tray; the returned response retained visible supporting hands and a stable platter in raw review. It depicts a response after support, not a handover. The edit uses151normalized30fps frames and a35-frame hold on the actual final frame, avoiding an unrelated illustrated ending. The portrait crop must keep complete hands clear of captions and exclude cut-off background faces; its effective source detail is lower than the native-wide clip. These are scene-specific observations, not a universal motion-quality qualification or authority to repeat either attempt.


## Aspect-specific sources within one bounded pilot

Use a native portrait illustration for portrait human action when a wide crop loses faces, supporting hands or effective detail. A scene may select a known `frame_profile` with the same steps, guidance, frame count and fps as the job profile; only reviewed dimensions may differ. The mixed job still has one original deadline, one attempt journal and the same total start/output/compute cap. Unknown profiles, arbitrary shapes and inference-contract changes fail validation. This is framing support, not evidence that either generated action is acceptable.

For a held namaste, describe joined palms as an invariant and animate one small head bow; avoid asking the model to construct or change a difficult hand gesture. For an already supported tray, animate a small response without a handover. Reject incorrect contact or gestures after real playback. Preserve previously accepted landscape footage when only a portrait replacement is qualified.

Wait for the complete Files-sidebar transfer before verifying the ZIP. A visible filename can precede complete bytes; a hash mismatch must stop setup/inference until the original bound ZIP matches. Keep the original allocation deadline through transfer delays.


## V13 measured held-gesture refinement

A held-namaste896×512 source produced a483.58second technical attempt. Raw5.04second playback retained joined palms, wrists and forearms during Rama's bow toward a child. It did not return upright by the end; selection is a bow-only landscape action followed by a context cut, not a completed bow-and-return. Portrait retains its independently composed illustration. These are scene-specific editorial observations; technical completion alone grants no acceptance.

Transfer/startup delays count against the original allocation. Before the second scene, measured-headroom checking stopped at597.77seconds versus600required; no second attempt was started, and the guard was not weakened. A two-start allowance is a maximum, not a promise to consume both. Export/import was verified, this GPU was released, UI showed0active sessions/0CU-hour, and saved flags were restored toFalse/zero. The account balance observation362.35→361.82includes an initially concurrent session and is not a pilot-only invoice. Native portrait family artwork remains prepared, not generated.


## Private notebook recovery for output-widget failure

A successful control transfer does not guarantee the final download. In v14, Colab reported an output-JavaScript loading error; reload retained the same session, but output-widget and session-file downloads still failed. No browser security/policy rejection was reported. Do not weaken cookie/security settings, bypass a policy rejection, or extend the original timer.

For this specific UI failure, an approved existing private notebook can preserve a small archive in source as a last resort: use the running kernel's `get_ipython().set_next_input(...)` to insert exactly two inert string assignments, `EARNALISM_PRIVATE_RECOVERY_SHA256` and `EARNALISM_PRIVATE_RECOVERY_BASE64`. Save through Colab, verify the Drive save, fetch the complete raw notebook with the Drive connector, then run:

```sh
python3 video_studio/colab_transfer.py recover-notebook /absolute/path/recovered.ipynb /absolute/path/archive.zip
```

The helper accepts one unambiguous two-string recovery cell, rejects executable/nonliteral/duplicate or hash-mismatched data, caps notebook/archive sizes and refuses overwrite. It never executes notebook code; normal `wan22.import_clips` job/model/member/media checks still follow. This route requires authority for the private notebook destination and generated data; it grants no new sharing or authentication access. The demonstrated2.32MB archive produced a3.15MB notebook and stalled its editor. Preserve the fetched original, restore the disabled cloud notebook, close only the stalled agent view, and verify shutdown in a fresh view. Prefer normal downloads; do not make large embedded source cells a routine default.

The v14 homecoming and native portrait family attempts completed in479.08s and490.90s respectively, with two starts and no generation retry. The original1800second guard remained fixed through recovery. Later UI readback showed0active sessions/0CU-hour, balance361.66→360.69, and disabled/zero saved controls. The balance movement is an account observation, not a provider invoice or exact shutdown timestamp. The selected homecoming edit uses121prior bow frames,54early return frames and12endpoint-hold frames at30fps, then context; late clipped-head footage is excluded. Native512×896 family footage uses151normalized30fpsframes plus15first-frame and20last-frame holds. Source resolution, selected intervals and full playback must remain explicit.


## Experimental single-shot detail pilot

`landscape-detail-pilot-v1` is explicit opt-in preparation, not a qualified L4/default quality profile. It binds one homecoming start only, 1280×704, 121 frames at 24 fps, 24 steps and guidance 5. A distinct run, explicit homecoming selection and retained prior evidence are required. It cannot be hidden in a mixed job or expanded to a second scene. The guard reserves 360 seconds for decode in addition to its existing export reserve and preserves the original 1800-second deadline. Require 1200 seconds of pre-start headroom and prove durable transfer before inference. Slow steps, memory failure or a missing completed action stop the pilot without a reroll or silent profile downgrade.

Official Wan guidance documents 1280×704 TI2V-5B generation on 24 GB-class hardware, but its example uses 50 steps and does not qualify this 24-step L4 experiment. Resolution alone does not prove sharper faces: retain a large enough subject while reserving the complete swept head/hand region. The first v15 full-body framing was rejected locally because extra empty space shrank the faces; a medium source was selected instead. Qualify actual motion completion, headroom, identity stability, source detail and the final delivery crop before selecting a replacement.

For local finishing of retained footage, compare the exact same motion at matched display size. Lanczos resampling and restrained luma sharpening can change edge contrast; they do not create missing detail, fix identity drift or add natural movement. Inspect both stills and playback for halos, shimmer and texture mismatch before adopting the finish. Preserve the original clips and audio.

Source checked for this preparation: https://github.com/Wan-Video/Wan2.2#run-text-image-to-video-generation . Runtime and visual qualification remain pending.
