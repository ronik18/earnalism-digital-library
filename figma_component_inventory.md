# Earnalism Figma Component Inventory

## Core Shell
- `AppHeader`: compact logo, Library, Bengali Classics, English Classics, Reader, About, and Enter Library CTA.
- `HeroEditorial`: calm editorial headline, subtitle, trust line, Start Reading, Browse Library, and graphical literary composition.
- `CuratedActionCard`: graphical cover tile, eyebrow, title, copy, gated CTA state.

## Catalog
- `BookCoverTile`: graphical cover image or deterministic graphical fallback with fixed aspect ratio.
- `BookCard`: cover, title, author, language/status badges, Read CTA, gated Listen CTA.
- `BookShelf`: editorial shelf header, optional status note, responsive card grid.
- `FilterRail`: search, language chips, availability chips, sort, and view mode controls.
- `StatusBadge`: Reader Ready, Audio Hidden, Audiobook Approved, In Review.

## Reader And Audio
- `ReaderShell`: ivory/sepia/night reading surface, centered measure, progress footer.
- `ReaderToolbar`: back, title, position, bookmark, contents, settings.
- `ReaderSettingsPanel`: font size, line height, margin width, theme, font mode, focus mode, reduced motion, highlight intensity.
- `AudiobookMiniPlayer`: rendered only when release-gate evidence exists.
- `ParagraphSyncHighlight`: section-following narration; never word-sync claims for paragraph/stanza releases.
- `PremiumUnavailableState`: calm audio unavailable copy for reader-only titles.
- `LoadingSkeleton`: premium paper skeletons for catalog/reader loading.
