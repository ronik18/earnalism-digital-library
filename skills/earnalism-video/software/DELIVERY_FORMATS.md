# Video delivery and audio masters

## Default playback delivery

Deliver MP4 with progressive H.264 video, yuv420p chroma, BT.709 SDR colour and AAC-LC stereo at 48 kHz. Preserve the authored frame rate (normally 30 fps) and the separately composed 1920×1080 landscape / 1080×1920 portrait layouts. Put the MP4 moov metadata before media data (+faststart), verify seek/reload/play-to-end and check actual encoded streams and dimensions. Choose quality-based encoding and inspect detailed motion; a file extension alone does not determine quality, compatibility or performance. Use a smaller derivative when actual delivery constraints justify it, retaining a high-quality source master. Do not silently upscale or interpolate source media and call it native higher-resolution footage. Record actual returned clip dimensions even when the provider ignored the requested resolution.

When a caption overlay ends before the film, pass through the underlying picture instead of shortening it or repeating the last caption into the ending. Verify the actual final frame count and complete approved ident; keep a focused regression for this failure.

Keep a clean master with the actual reviewed caption track and a destination-specific burned-caption copy where needed; avoid stacked native and burned captions. Derive all caption timing from the actual unchanged audio. A WAV is not the video soundtrack container for ordinary web playback; the MP4 contains its own AAC audio.

## Audio preservation

Retain PCM WAV narration and the complete mixed soundtrack as audio masters, normally at the existing 48 kHz project rate. A 24-bit PCM export is useful for editing headroom; it cannot add detail missing from a compressed source or earlier lower-bit-depth recording. Preserve original provider files and their hashes. Prefer the existing verified AAC payload for visual-only revisions instead of unnecessary audio re-encoding; verify identical packet payloads across delivered video formats. Report the source and derivation of each WAV honestly. Do not confuse .wav, .mp4 or a successful decode with listening acceptance.

Reset decoded timestamp origin when assembling segments; check actual sample durations, narration plus intentional rests and the full approved ending sound. Do not loosen duration checks to hide a clipped tail. Retain earlier failed exports and invalidate only affected evidence. Technical validation does not supply factual, rights, naturalness or pronunciation approval.

## Reference checked 2026-11-07

YouTube's official [recommended upload encoding settings](https://support.google.com/youtube/answer/1722171?hl=en) supports MP4 fast start, H.264 progressive 4:2:0, 48 kHz AAC and BT.709 SDR. This is platform guidance, not a universal best-codec claim or a requirement to replace an already qualified unchanged soundtrack. Recheck destination requirements at actual delivery.

## Consumer-player verification

Check native captions against the complete logo lockup as well as headings, diagrams and controls; a clean master alone does not prevent a two-line caption from reaching into the watermark. Correct only the delivery sidecar when sufficient, preserving every word and timestamp, and verify the saved selected track in the actual destination player. A stale “captions unavailable” accessibility label can contradict visible English captions and the selected English menu item; record the contradiction and test the rendered track instead of diagnosing missing captions from the label alone.

For looping Reels/Shorts, record the exact post ID, duration and complete played range or observed repeat; `ended=false` alone is not a playback failure. Distinguish paused seeks from continuous coverage, source resolution from the adaptive served rendition, and desktop evidence from native-mobile or signed-out verification. Retain the scope of the checks actually performed.

A local caption rail outside the video is excluded by video-only fullscreen. Use one real caption track in a clean preview, or a fullscreen container that also includes the rail; avoid duplicating native, external and burned captions. Check a long cue while paused and after seeking, caption toggling and fullscreen where the available controls permit it. Record a failed or unavailable fullscreen test explicitly rather than claiming it passed or changing accepted audio.
