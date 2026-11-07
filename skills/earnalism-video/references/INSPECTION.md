> Release policy: [GO_LIVE.md](GO_LIVE.md) governs. Research, variant and growth tasks are optional; one final candidate decision covers primary checks. Older wording does not add approval steps.

# Supplied notebook inspection

Inspected JSON cell sources rather than inferring from the name. Original supplied notebook: 454720 bytes, SHA256 62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4.

Actual narration: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice, stock Ryan. Model commit 0c0e3051f131929182e2c023b9537f8b1c68adfe; Qwen code commit 022e286b98fbec7e1e916cb940cdf532cd9f488e. Original environment: managed Python 3.12, torch/torchaudio 2.8.0 CU126, eager attention default, GPU cuda:0. Separate CPU faster-whisper 1.2.1 large-v3 ASR. Optional ACE-Step music exists but is not needed for this video.

Useful safeguards preserved verbatim in vendor/qwen_worker.py: pinned snapshot identity, generation configuration validation, native-English stock speakers only, numerical generation probe, finite waveform/clipping/RMS/duration/rate checks, process lock, fsynced attempt journal, maximum three attempts across resumes, per-effective-settings cache keys, audio/metadata hashes, STOP flag and pending human listening state. This worker does not implement publication.

The source notebook additionally contains historical private-ASR probes, Unit24 repair, Drive persistence probes, book catalogue/review/release machinery and optional music. Those cells are neither copied as executable notebook stages nor executed. The video embeds only the required worker, its policy/layout/core imports and the original runtime setup module. The runtime module contains unrelated functions but the video invokes only setup_qwen, pip_env and its video-scoped snapshot override. It never invokes prepare_source_repository or audiobook release functions.

Separate folders: /content/earnalism-video/software, /content/earnalism-video/venvs, /content/earnalism-video/hf-cache; optional /content/drive/MyDrive/Earnalism_Video_Studio/outputs. Local outputs under video_studio/outputs; scene configuration under video_studio/config. Original snapshot cache path is overridden at the adapter boundary without modifying the vendor source. No output targets existing audiobook folders.
