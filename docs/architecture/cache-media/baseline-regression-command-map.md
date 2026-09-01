# Baseline regression command map

The cleanup command reproduced three failures on both `090afdd4b84eecc5ca40b7576ce54000305df837` and untouched PR head `d13a01e440da7c695af1a9b89378c390d583cd4c`. The legacy routing command reproduced the same 13 failures on both authorities. The JSON companion is the machine-readable command and count record.

The runtime catalog source is `data/controlled_publications`; `backend/data/controlled_publications` is a packaged duplicate, not the first selected local runtime root. `book-2b9853ec52` is present only as an excluded historical packet and is unavailable to runtime loading. `nishkriti` is runtime-valid and audio-disabled; its observed mismatch was in the duplicate packaged historical checksum manifest.

The normal regression and PR regression scripts are recorded in the JSON map. Neither historic failing suite is selected by the normal regression script, so their authority is adjudicated by the current protected-audio tests and final green targeted reports.
