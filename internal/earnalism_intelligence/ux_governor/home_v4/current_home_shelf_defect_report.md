# Current Home Shelf Defect Report

Status: repaired in code; production visual canary pending.

## Root causes

- The previous Home mounted an inline legacy hero and `HomeShelfArchitecture`; it did not mount the release-safe `PremiumHero`, so the required Hero → Listening Rooms → Collage order was not guaranteed.
- Broken cover states came from raw image paths and the reader sanitation path that converted failed/empty inline images into a customer-visible `Image unavailable` alt string. The shared cover component also treated a generated graphical resolver fallback as a real image when `allowGraphicalFallback={false}`.
- Love-card overlap came from content-driven implicit rows, negative cover-stage spacing, and transformed cover items sharing flow with chips and CTA. The repair gives meta, title, description, chips, covers, and CTA explicit zones and bounds the cover stage.

## Repair

- Home now fetches `/api/home/curated` once and mounts `PremiumHero`, `PremiumListeningRail`, then `CuratedShelfCollage`.
- `BookCoverImage` tries ordered canonical candidates and calls permanent-failure callbacks only after all candidates fail. Shelf and rail components promote same-shelf reserve books into the failed slot.
- Failed inline reader images are omitted instead of creating a broken-image marker or customer-facing placeholder text.
- The Love card is a bounded flow grid; cover stage, chips, and CTA cannot share an implicit row.

Production browser measurements remain required before any 10/10 claim.
