> Release policy: [GO_LIVE.md](GO_LIVE.md) governs. Research, variant and growth tasks are optional; one final candidate decision covers primary checks. Older wording does not add approval steps.

# Earnalism Video Studio operating guide

Use the selected project copy of the bundled software. Resolve the active edition instead of using an old version or URL:

```sh
python3 video_studio/review_index.py evidence/current-private-review.json --check-http
python3 video_studio/improvement.py /absolute/verified-candidate
```

The record binds the candidate, delivery manifest and review kit. A local loopback player is private review, not production publication. Historical editions, frozen-audio examples and one-off preparation scripts are replay evidence, not current defaults.

## Start and preserve

Run `scripts/verify.py --project /absolute/project` from the installed skill. It checks the supplied audiobook notebook checksum and project tests. Keep that notebook and every production record unchanged. Use the separate `Earnalism_Video_Narration_Pipeline.ipynb`, independent configuration, caches, logs, retry journal and outputs. Build the fork through `video_studio/build_notebook.py`; safe Run All defaults disable synthesis/export and authorize zero metered units. See [voice production](VOICE_PRODUCTION.md).

Restore pinned Node dependencies with `npm ci` in `video_studio` when necessary; use the existing FFmpeg/ffprobe and reviewed Chrome renderer. Do not silently update libraries, buy compute or introduce a speech provider. Follow `INSPECTION.md` for pinned worker/model provenance and useful original safeguards.

## Production path

Research authoritative sources → write a clear mechanism and misconception → storyboard topic-specific explanatory animation → short original-voice audition when needed → bounded same-provider Colab narration → actual-audio ASR/captions/anchors → independently composed landscape and Shorts → private factual/graphical/listening review → verified delivery → existing website integration only after its gates pass.

Landscape 1920×1080 is primary. Produce separately composed portrait 1080×1920 and captioned portrait, SRT/VTT, transcript, references, thumbnail, YouTube metadata and a dry-narration comparison. About 90 seconds is an editorial aim; never rush, pad or cut reasoning just to hit a clock. Other topics require their own tested model/scenes; do not relabel the Moon renderer.

```sh
python3 video_studio/studio.py import /absolute/narration.zip video_studio/outputs/new-private-edition
python3 video_studio/studio.py render /absolute/new-private-edition
```

Import verifies all member hashes and rejects traversal, symlinks, duplicates and unmanifested files. Render only into a fresh candidate; never overwrite an existing edition.

## Select the smallest correct refinement mode

| Change | Supported route | Required preservation and fresh evidence |
|---|---|---|
| Voice or spoken content | Source-bound edit or bounded stock-Ryan synthesis | Keep original takes/journal; fresh actual-audio ASR, captions, anchors, score timing and both videos; new listening review |
| Visual-only with frozen soundtrack | `python3 video_studio/frozen_edition.py SOURCE NEW`, then `python3 video_studio/studio.py render-frozen NEW` | Verify PCM, captions and copied AAC packets; inspect new frames/playback; fresh artifact-bound AV review |
| Music-only | `remix.py` into a fresh folder | Preserve narration/captions/video streams; rebuild from original score through fresh ducking; new mix/provenance/rights/listening/delivery evidence |
| Combined presentation and music | Fresh candidate preserving narrator/caption hashes; use `render(..., expected_narration_sha256=...)` | New score and images; verify narrator PCM/captions before encoding and all final files afterward |
| Player-only | Fresh review pages/manifest; reuse verified media | Verify media identity, visible motion, caption preference, seeking, reload, return and Replay |

Do not stack processed speech or automated music. Keep rejected attempts and findings. The current exact-emblem watermark, clean picture and END ident are defined in [editorial presentation](EDITORIAL_PRESENTATION.md); use [creative refinement](CREATIVE_REFINEMENT.md), [music direction](MUSIC_DIRECTION.md), [music checks](MUSIC_AUDIBILITY.md) and [learning acceptance](LEARNING_ACCEPTANCE.md) for their respective work.

## Private delivery and release

Serve with `review_server.py OUTPUT_DIRECTORY --port FREE_PORT`, bound to 127.0.0.1. Verify actual HTTP 206 ranges and disabled directory listing. Use MP4 faststart with WebM fallback. The visible player hides download links, but that is not authentication, DRM or capture prevention. Preserve captions, sources, AI disclosure, fullscreen, Replay and recovery. Test actual moving pictures in the owner's narrow panel; decode and advancing time alone do not prove visible playback.

`studio.verify_download(URL, SHA256, NEW_DESTINATION)` must retrieve, hash and fully decode each delivery. Do not invent links or call an unexecuted transfer successful. Use [strict quality](STRICT_QUALITY.md) for mandatory claim/frame/playback coverage and [disclosures](DISCLOSURES.md) for external-delivery copy.

All real release candidates need fresh artifact-bound factual, rights/model, voice, AV, technical, delivery and applicable learning/device acceptance. Tests cannot supply human approvals. Fixtures never publish. GO LIVE does not override failed gates, missing listening feedback or user-only authentication. Inspect and reuse the real website/router/storage/access contracts; no new CMS, dashboard, payments or bulk framework. YouTube remains manual upload-ready delivery. Report local rendering, Colab narration, verified downloads and actual website publication readiness separately.

## Audience planning and format packaging

Before narration, follow [audience and distribution](AUDIENCE_AND_DISTRIBUTION.md). `prepare` creates a draft audience plan and packaging record. The creator fills ordinary editorial choices autonomously and runs `audience_plan.py generation FOLDER`; incomplete non-fixture plans stop `make_job` and Colab execution before model setup, including resumes. Engineering fixtures remain unpublishable.

Before finalizing a new delivery manifest, complete selected titles/reasons and actual cover/readback references. Render emits private `youtube-landscape.json` and `youtube-shorts.json` matched to those selections, and a pending publication handoff. `audience_plan.py package FOLDER` verifies assets/bindings; it does not establish click appeal or human graphic approval. Packaging changes after rendering require a fresh bound candidate.

After internal qualification and separately authorized manual upload, `audience_plan.py handoff-check FOLDER --target youtube` validates current platform evidence; use `--target website` or `both` for the existing storage/watch route. Keep handoff and production journal outside the media manifest. Current policy/route observations use an internal seven-day freshness window. No command uploads, purchases, schedules or approves publication.
