# Earnalism Home Performance Sprint V1

Act as the lead systems architect and senior frontend engineer for The Earnalism. Preserve the approved premium visual design and all fail-closed reader and audiobook release truth while eliminating the text-first/loading-preview experience on the public home route.

Implement one exact prerendered React home shell and hydrate it without replacing the root DOM. Keep the header and premium hero in the critical render path. Defer the listening rail, curated shelf collage, site tour, and below-fold imagery through code splitting plus intersection or idle scheduling. Replace oversized brand imagery with dimensioned AVIF/WebP derivatives, normalize same-origin absolute covers into responsive local derivatives, separate reader/route CSS from the home bundle, version immutable hero assets, compact and cache home curation off the critical path, and enable production field web-vital telemetry.

Acceptance evidence must include mobile and desktop production builds, browser hydration with zero mismatch errors, no loading-preview node, no horizontal overflow, CLS below 0.05, initial transfer below 700 KB, mobile FCP at or below 1.2 seconds, mobile field LCP at or below 2 seconds, and desktop Lighthouse at or above 95. Do not claim the field LCP gate until real production traffic confirms it.

Run the complete frontend suite, focused backend curation/release-truth tests, the UX governor, a production build, mobile/desktop Lighthouse, and production route canaries. Commit only performance-sprint files; exclude concurrent publication or catalog work. Merge and deploy only from the exact merged `origin/main` commit.
