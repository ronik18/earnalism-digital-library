# Earnalism three-second brand sting

Private review ident, 1920×1080, 60 fps, 180 frames. Uses the exact unchanged 2400×720 production header PNG retrieved from https://theearnalism.com/assets/brand/earnalism-brand-lockup.png on 27 October 2026 (IST). The full wordmark, tagline and venture line remain inside the asset; no retyping or recolouring. Reference screenshot: evidence/production-header-brand.png.

Visual: burgundy hardback, gold rules, perspective cover opening and ivory leaves reveal the production lockup on warm paper. No third-party footage or fonts. Sound: deterministic original synthesized paper foley and a sparse warm harmonic resolve; no speech provider, samples, stock track or paid generation. Source and recording hashes are retained in sound-provenance.json. Owner review remains pending; nothing is published.

From video_studio, run `python brand_sting/sound.py` only when restoring missing sound (refuses overwrite), then `node brand_sting/render.mjs`. Rendering refuses an existing MP4. Version outputs instead of overwriting. FFmpeg master audio normalisation uses -20 LUFS, -2 dBTP and an explicit three-second trim. Export VP9/Opus preview for the in-app browser and H.264/AAC MP4 for delivery. Final full decode and hash-verified local HTTP download are recorded in technical.json and delivery-check.json.
