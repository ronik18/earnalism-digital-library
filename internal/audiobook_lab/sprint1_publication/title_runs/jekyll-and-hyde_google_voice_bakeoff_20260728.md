# Jekyll and Hyde Google voice bake-off

## Result

`en-GB-Chirp3-HD-Charon` at rate `0.94` is the selected private representative candidate.

| Voice | Objective result | Listening result | Decision |
| --- | --- | --- | --- |
| `en-GB-Studio-C` at `0.88` | Four normalized passages at 10.0 / 1.0 | 9.4, 8.4, 8.4, 9.4 | Closed; do not repeat |
| `en-GB-Chirp3-HD-Charon` at `0.94` | Four normalized passages at 10.0 / 1.0 | 9.4, 9.4, 9.4, 9.4 | Representative pass |

The Charon middle passage had one source-blind ASR spelling variance:
canonical `neighbouring`, transcript `neighboring`. Raw score and coverage
remain recorded at 9.8438 and 0.9844. The adapter applies only that explicit
standalone British/American orthography pair; no broad spelling, stemming,
name, or content normalization is allowed.

All four selected samples have valid audio-derived word timestamps, confidence
0.95, no fatal flags, and no listening dimension below 9.2.

## Release truth

This is not a full audiobook and is not release-ready. The title remains
reader-live and audio-hidden. Full-title generation cannot start until the
private graphical front/back candidates are reviewed and promoted to canonical
cover truth.

No audio was uploaded, no release gate changed, and no public endpoint or
browser release claim was made.

## Next exact command

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/title_runs/jekyll-and-hyde_google_voice_bakeoff_20260728.json >/dev/null
```
