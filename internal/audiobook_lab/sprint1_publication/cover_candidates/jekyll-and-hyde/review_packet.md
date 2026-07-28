# Jekyll and Hyde private cover candidate

## Decision

This pair is a private, text-free graphical candidate for **The Strange Case of Dr. Jekyll and Mr. Hyde** by Robert Louis Stevenson. It is not canonical and has not been uploaded or exposed publicly.

The front uses a gaslit Victorian street, a private laboratory window, a neglected door, and a divided cast shadow. The back continues the same setting with a quiet central field suitable for deterministic reader-facing typography.

## Technical checks

- Both files are original 1024 x 1536 RGB PNG artwork in a 2:3 ratio.
- Both files are below the current 4 MiB admin-upload limit.
- No title, author, logo, source mark, watermark, barcode, or generated lettering is embedded.
- No audio, reader, release-gate, or public catalog state changed.

## Required review

Owner review must confirm the visual direction and visual-rights statement before upload. The current production admin route also needs a controlled-publication fallback because `jekyll-and-hyde` is not present in Mongo and therefore cannot currently receive a private cover candidate.

After an authenticated private upload, canonical promotion remains a separate hash-bound catalog change covering both controlled-publication copies and their checksum manifests.

## Generation prompts

Front: premium painterly engraved Victorian London cover art with a gaslit street, private laboratory, weathered door, dignified gentleman, and a human shadow expressing divided identity; dark bottle-green, charcoal, oxblood, amber, and antique-gold palette; text-free.

Back: matching gaslit London street and laboratory-door companion art with a sealed envelope, restrained glassware, and broad quiet central negative space; text-free.

## Next exact command

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/cover_candidates/jekyll-and-hyde/candidate_manifest.json >/dev/null
```
