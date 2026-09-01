# WebKit Article mobile stability

The Article DOM, geometry, computed fonts, fixture requests, and scroll position were stable. The only mismatch was the viewport raster in the Article hero: the differing pixels were bounded to `0,145–390,454`, had a maximum channel delta of `2`, and did not affect either close-up capture.

The primary cause is `WEBKIT_TEXT_RASTER_ONLY_NONDETERMINISM`, amplified by capture-side frame/style churn. The capture harness now establishes Article quiescence, holds its WebKit stabilization rule for the comparison pair, uses clip-based page screenshots, and does not issue a no-op scroll restoration or post-screenshot animation-frame cycle. Final evidence still requires exact SHA equality; no pixel tolerance was introduced.
