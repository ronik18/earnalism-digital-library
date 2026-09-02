# Reader high-zoom control evidence — before

The 390px/200%, 320px/150%, and 320px/200% states were captured in Chromium before the Reader CSS correction. The mobile top bar was a non-wrapping flex row with a three-button fixed cluster, while its zoomed logical inline space was 195px, 213px, and 160px respectively. Its required single-row inline size was 434.94px, 331.20px, and 434.94px.

The controlled capture data is at `/tmp/pr344-reader-high-zoom-before`; the JSON companion records the browser-derived boxes and the exact clipped controls. The defect is a `NON_WRAPPING_FIXED_CONTROL_ROW` combined with `CONTROL_CLUSTER_MINIMUM_WIDTH_EXCEEDS_AVAILABLE_WIDTH`.
