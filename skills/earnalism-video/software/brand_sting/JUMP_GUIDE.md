# Red L and caret jump studies

Three private 3-second/60-fps samples. The exact production PNG is composited into a stationary rest layer and original-artwork glyph layers. Mask bounds in original 2400×720 coordinates: x707, y40, width181, height350. No mark was retyped, recoloured or redrawn. Independent L/caret clipping separates at y290. Final position/scale is unchanged.

Paired Hop: both marks arrive as a group, with a small rebound. Staggered Landing: L lands before caret. Arcing Jump: the group follows an arc with slight tilt. All motion uses eased interpolation; the full rest of the logo is visible from the outset. Original synthesized upward gesture and soft landing tones are timed in jump_sound.py, with no stock audio or paid services.

Sources: glyph-jump.tsx, jump_sound.py, render_jumps.mjs, finish_jumps.py. Output: outputs/glyph-jump-options-v2. Earlier studies and the original book introductions remain untouched. Render and finish scripts refuse overwrites. Preserve the original production PNG and protected notebook checksums.

Verification: 180 frames, 1920×1080, 60 fps, three-second MP4; full decode, audible unclipped AAC, VP9/Opus browser preview, actual local HTTP retrieval and byte-hash check. Final still comparison against an unmasked production logo reference allows at most two RGB levels out of 255 for masked alpha compositing rounding. No logo geometry or content changes. Owner creative/listening approval remains pending; nothing is published.
