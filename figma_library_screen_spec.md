# Earnalism Library Screen Spec

## Frame
- Desktop: `1440 x 1400`
- Tablet: `820 x 1180`
- Mobile: `390 x 844`

## Structure
1. Compact editorial library hero.
2. Recognition-first catalog controls.
3. Live reader-ready shelf.
4. Rights-safe pipeline shelf.
5. Reading paths and audiobook proof shelf.

## Controls
- Search: title, author, language, status.
- Language: All, Bengali, English.
- Availability: All, Reader Ready, Approved Audiobook, Audio Hidden, In Preparation.
- Sort: Recently approved, Title, Author, Short reads.
- View: Shelf, Grid, Compact.

## Card Requirements
- Graphical cover.
- Title, author, language.
- Status badges.
- `Read` visible when reader route is approved.
- `Listen` visible only when `canExposeAudiobookControls` is true.
- Bengali reader-only copy: `Reader edition live · audio intentionally hidden`.
