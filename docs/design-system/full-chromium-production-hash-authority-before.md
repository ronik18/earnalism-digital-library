# Full Chromium production-hash authority reproduction

The exact-head workflow run `33534427000` completed the Chromium `65/65/65`, Firefox `20/20/20`, and WebKit `20/20/20` populations. Its real-output full-Chromium validator then failed before package generation.

`validateFullChromiumMatrix` compared the observed capture value `199ff2d18bc0df16f5e4e2bdc9bcf8ceba24d26c3ee92360802db80c1dbc31b1` with its implicit synthetic fallback `synthetic-production-surface`. The real workflow invocation supplied `--output` but no explicit real expected hash.

Classification: `SYNTHETIC_PRODUCTION_SURFACE_EXPECTATION_USED_FOR_REAL_CAPTURE`.
