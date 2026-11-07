# Wan2.2 Colab motion adapter

Use when natural illustration/character motion is needed and the selected hosted provider is unavailable, or the owner chooses self-hosted Wan. This is a prepared, locally tested adapter; it is **not GPU-inference-qualified or an accepted replacement** until actual clips are generated and reviewed. Preserve selected narration, original notebooks, earlier candidate media and their manifests.

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

The worker now forecasts completion after two measured steps, retaining a15percent timing margin,45seconds for decode and the separate120-second export reserve. If it cannot fit, it fails the existing attempt without retry or deadline reset. This safeguard is locally tested; its callback has not yet been exercised in a new live inference. A future reduced-resolution/shorter/accelerated route needs its own prepared job, validated model/pipeline compatibility and scoped compute authority; do not silently reduce this job or borrow unused allowance after shutdown.

The final full audit ZIP was created but not durably imported: automatic downloads stalled, and a direct data-URL recovery link was rejected by browser URL policy. Do not work around such a rejection using another browser surface or encoded archive extraction. Preserve visible observations separately and report the missing raw archive honestly. Only the earlier small control ZIP was durably hash/import verified. An export/download click is not delivery evidence.

## Optimized bounded retry profile

For the owner's fresh5CU/30-minute retry, use `--profile l4-balanced-v2`. It creates `diwali-wan22-pilot-v2` in a separate runtime root, retaining prior failed-attempt provenance. It keeps the exact model revision, input hashes, seeds, guidance5,121frames/24fps and two-start/11second limits, but uses512×896 and24steps. This is a performance/quality tradeoff to review in actual playback, not a qualified production default. The standard-v1 job remains unchanged and importable. Shape and step settings are profile-bound; never relabel an existing attempt or silently alter its job.

Use only the PyTorch backend (`USE_TF=0`, `USE_FLAX=0`) in isolated subprocesses; these supported Transformers flags avoid unrelated backend initialization. Export ZIPs use standard DEFLATE to reduce log-transfer size. Neither change grants model/voice/provider authority.

The retry's normal `files.download()` control transfer was durably verified after completing Chrome's native Save dialog. If the Colab cell finishes but no local file appears, inspect the native browser dialog before declaring a transfer failure. Complete only the task's expected filename; preserve existing files and unrelated windows. A Playwright download-event timeout alone does not prove download failure. Verify local bytes/hash after saving. This supported route does not require data URLs, permission changes or broad Drive access.

References: [pinned pipeline input and denoising contract](https://github.com/huggingface/diffusers/blob/v0.36.0/src/diffusers/pipelines/wan/pipeline_wan_i2v.py), [pinned Transformers backend flags](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/utils/import_utils.py). The512×896 shape satisfies the pinned pipeline's16-pixel divisibility requirement; lowering steps is an engineering choice, not a claim of equal quality.

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
