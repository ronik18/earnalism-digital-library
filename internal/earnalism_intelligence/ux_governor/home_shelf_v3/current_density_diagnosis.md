# Home Shelf V3 Density Diagnosis

## Baseline diagnosis

The previous shelf implementation used a two-row 12-column grid with fixed `21rem` rows. The Bengali tile occupied both rows, so its outer box was approximately `44rem` including the grid gap while the supporting tiles retained the same tall card anatomy. That combination created a large vertical stage for short copy and made the visual weight depend on empty grid space rather than on the covers.

The supporting cards also shared the same content-driven anatomy regardless of book count. Gothic and Love each had one valid cover, but were rendered as full shelf cards instead of a spotlight/duo variant. Adventure had three covers and consequently looked materially denser. Short Masterpieces had no cover-audit-valid title, so it could not render a truthful card; the fallback area made the lower row read as an unresolved composition even when CSS technically collapsed the grid.

The curation code was already reader-first, but the first viewport allocator did not reserve hero visuals before selecting shelf candidates. That could produce avoidable cross-surface repetition. Approved-audiobook status was not used to qualify literary shelf membership, which is correct and remains unchanged.

## V3 correction

V3 replaces the fixed tall-card impression with explicit editorial areas, compact bounded rows, and adaptive modes:

- `shelf-feature` for three or more valid canonical books;
- `duo-shelf` for two valid canonical books;
- `spotlight` for one valid canonical book;
- hidden shelf for zero valid books.

The Bengali feature and Gothic spotlight share the first row, while Love and Adventure share the second row. When Short Masterpieces has no valid visual asset, Adventure intentionally spans the remaining lower row instead of leaving an unsupported grid cell or a fake card. On mobile, that omitted shelf is removed from the one-column area map as well.

## Measured result

Browser geometry was captured against the production build at 1536x864, 1440x900, 1180x900, 984x1364, 768x1024, 430x932, and 390x844. All captures report zero horizontal overflow. Desktop and tablet paired rows have zero measured bottom-edge error. The largest measured content gap is 98.4px on the mobile Adventure feature, below the 120px supporting-card threshold and 160px feature threshold.

The remaining visible truth gap is catalog data, not layout: the current cover audit excludes every Short Masterpieces candidate and excludes the current approved-audiobook visual packages. Those assets must be repaired before the Short card or Selected Listening rail can truthfully appear. No placeholder or mismatched cover was added to hide that gap.
