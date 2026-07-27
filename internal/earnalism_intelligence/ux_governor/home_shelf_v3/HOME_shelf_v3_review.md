# Home Editorial Shelf Runway V3 Review

## Executive result

The V3 implementation replaces the sparse fixed-height collage with an explicit editorial runway that follows the hero’s dark-to-parchment visual handoff. The browser build was checked at all seven requested viewport sizes. Layout hard checks pass: no horizontal overflow, no orphaned rendered card, no unsupported empty grid cell, no duplicate within a visible shelf, and paired row bottoms align to 0px in the measured build.

This review does **not** claim a 10/10 launch score. The current catalog truth prevents two requested visual elements from appearing safely: every Short Masterpieces candidate fails current graphical-cover truth, and the approved-audiobook records currently have placeholder or canonical-mismatch cover evidence. The implementation omits both rather than rendering misleading covers or internal audio status.

## Layout and density

Desktop (`>=1280px`) uses the requested 12-column runway:

```text
"bengali bengali bengali bengali bengali bengali bengali gothic gothic gothic gothic gothic"
"love love love love adventure adventure adventure adventure adventure adventure adventure adventure"
```

At 900–1279px the layout becomes two columns; at 984px the browser confirms the Bengali feature spans both columns, Gothic/Love are paired, and Adventure spans the lower row because Short is truthfully omitted. At 600px and below the layout becomes a single compact column, with no unsupported Short row.

The feature, duo, and spotlight modes keep the card anatomy tied to real title count. Bengali uses three covers, Gothic uses a compact one-book Spotlight, Love uses two covers, and Adventure uses three covers. The one-book Spotlight no longer leaves a narrow cover island inside a wide empty panel.

## Exact shelf selections

- Bengali Life & Legacy: `book-f5d593e1f4`, `book-edfcf810c5`, `bn-066`.
- Gothic & the Uncanny: `dracula`.
- Love, Society & Human Nature: `radharani`, `pride-and-prejudice`.
- Adventure, Nature & Wonder: `the-time-machine`, `the-call-of-the-wild`, `the-secret-garden`.
- Short Masterpieces: omitted because no candidate passes cover truth.
- Selected Listening: omitted because current approved-audiobook visual packages do not pass cover truth.

The allocator reserves hero-selected visuals before shelf selection and avoids cross-shelf duplication when a canonical alternative exists. It does not use audiobook approval as a literary-shelf eligibility requirement.

## Visual evidence

Full-page captures are stored for `1536x864`, `1440x900`, `1180x900`, `984x1364`, `768x1024`, `430x932`, and `390x844`. Focused review captures are stored at:

- `screenshots/HOME_shelf_v3_1536x864_focused.png`
- `screenshots/HOME_shelf_v3_430x932_focused.png`

The focused desktop capture shows the continuous transition, compact intro, balanced first row, and corrected Gothic Spotlight. The focused mobile capture shows the one-column runway, readable chip rhythm, intact cover links, and no Short placeholder row.

## Accessibility and performance

The shelf remains semantic: section heading, shelf headings, cover lists, descriptive cover labels, keyboard-visible focus, reduced-motion support, and minimum mobile target sizing. Images keep explicit dimensions, responsive `sizes`, lazy loading, and no public fallback cover. The production build completed successfully with a 116.21 kB gzip main JS bundle and 30.63 kB gzip main CSS bundle.

## Remaining backlog

1. Repair or replace the canonical graphical covers for the Short Masterpieces candidates through the approved cover workflow.
2. Repair approved-audiobook cover packages and rerun cover truth before showing Selected Listening.
3. Re-run the scorecard after those assets pass; only then can the visual result be reconsidered for the requested 9.8+ claim threshold.
