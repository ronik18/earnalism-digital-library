# Home, Library, Reader/Audiobook 10/10 UX Sprint Evidence

Generated: 2026-07-07T18:20:00Z

## Scope

- Home
- Library
- Reader with approved audiobook controls and settings

## Governor Inputs

Read the persistent UX Governor doctrine, 10/10 page specs, fixed design tokens, scorecard schema, release-gate UX policy, cover policy, and typography policy under `internal/earnalism_intelligence/ux_governor/`.

## Source Findings

- Home source already follows the hybrid editorial hero plus three curated action-card direction.
- Dracula is not the Home main hero; it appears as an English Classics route/tile.
- Bengali Classics are visible and positioned as reader-first/live without unapproved audio promises.
- Library source has search, language filters, availability filters, sort, view modes, status badges, graphical covers, and gated Listen CTAs.
- Reader source had a material release-truth issue: browser `speechSynthesis` fallback and inferred static `/audio/...` URLs were still present.

## Source Changes

- Removed browser speech-synthesis fallback paths from `frontend/src/pages/Reader.jsx`.
- Removed inferred static `/audio/{lang}/{slug}` fallback URLs from `frontend/src/pages/Reader.jsx`.
- Reader audio now requires explicit approved assets or manifest evidence.
- Reader audio copy now says approved audiobook/section-following narration and never claims word-level sync.
- Audiobook speed control is tied to approved audio playback, not browser speech.

## Validation Evidence

- Cover audit: PASS. 164 covers audited, 0 typographic-only public covers.
- Source scan after patch: no `speechSynthesis`, no static `/audio/...` fallback, no `word-level` claim, no fallback speech copy in target source files.
- Required frontend test/build/smoke validation is blocked because `npm ci` and compatibility install attempts stalled during dependency resolution and left `frontend/node_modules` incomplete.
- `craco`/`react-scripts` commands failed after the install stall because `react-scripts` is missing.

## Release-Gate Truth

- No publishing logic was changed.
- No audio was generated.
- No production metadata was mutated.
- No unapproved audio was exposed.
- No word-level sync claim was introduced.

## Status

HOME LIBRARY READER UX PARTIAL.

The high-impact release-truth source fix is complete, but the sprint cannot be marked green until frontend dependencies are restored and the required validation suite passes.
