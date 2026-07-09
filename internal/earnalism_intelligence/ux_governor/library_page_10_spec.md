# Library Page 10/10 Spec

## Intent

The Library must feel like a premium catalog, not a warehouse grid. It should help readers discover by language, availability, genre, mood, and reading intent.

## Required Controls

- Search.
- Language filters: All, Bengali, English.
- Availability filters: Reader Ready, Audio Hidden, Audiobook Approved, In Preparation.
- Shelf, grid, and compact views where supported.
- Sort options that prioritize reader value without hiding release truth.

## Required Card States

- Reader Ready.
- Audio Hidden.
- Audiobook Approved.
- In Preparation.

## Book Card Requirements

- Graphical cover.
- Title, author, language, and truthful availability badges.
- Read CTA when reader route is live.
- Listen CTA only when approved audio evidence exists.
- Calm hover and focus states.
- No title or cover crop.

## Empty, Loading, and Error States

- Use premium skeletons or calm unavailable states.
- Do not show raw API errors.
- Do not leak internal metadata.
- Bengali reader-only titles must feel complete, not missing or broken.

## Release-Gate Requirements

- No stale audio exposure.
- No audio CTA from metadata alone.
- No inferred approval from audio URL presence alone.
