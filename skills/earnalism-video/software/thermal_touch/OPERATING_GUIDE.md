# Thermal touch — private episode adapter

Use the selected Studio project, with its existing Remotion dependencies, approved
brand assets and hash-bound accepted B job. This is a subject-specific adapter,
not a replacement for the general production workflow or permission to spend.

1. Keep research, units and the baseline job under a fresh episode production
   directory. `build_colab.py PRODUCTION_ROOT` creates a separate disabled notebook;
   connect/run only within the current authorized compute scope. Preserve the
   original notebook, persistent retries and every returned take.
2. Verify the downloaded archive and its manifest, safely import original WAVs,
   `.wav.json` provenance and alignment records under `imported/`. Then run
   `assemble.py PRODUCTION_ROOT`. Every recognized-word difference or missing
   actual phrase anchor blocks assembly; an existing assembly requires a fresh
   explicit output directory. No new timing is inferred from the script.
3. Review actual phrase/caption timing and rendered checks, then `finish.py score
   ASSEMBLED_ROOT` creates the new score and one common soundtrack. Render silent
   animations with `render.mjs` into `{landscape,shorts,clean-shorts}/animation.mp4`,
   using the corresponding actual props and `ThermalLandscape`, `ThermalShorts`,
   `ThermalCleanShorts`. Run `finish.py mux ASSEMBLED_ROOT FORMAT` for each.
4. Review the complete scored/dry audio and both visual compositions. Test real
   playback, native/burned captions, seeking and replay. Keep acceptance pending
   until evidenced; use the existing single exact-candidate release decision.

The physics test model assumes ideal semi-infinite perfect contact. It is not a
measured skin-temperature curve. Rendered energy marks are qualitative; keep
equal *starting* temperatures distinct from post-contact temperatures, and stage
the warmer-object condition before reversing every heat arrow. Never recommend
testing hot surfaces by touch.

`engineering-v1` contains explicitly estimated layout fixtures and proof frames.
They cannot qualify narration, final synchronization, captions or publication.

Validation: `python3 -m unittest discover -s video_studio/thermal_touch -t .`
and `node video_studio/thermal_touch/test_layout.mjs`. Tests do not supply listening
or owner approval. All output writers refuse overwriting existing candidates.
