# Earnalism Luxury UX Rebirth Audit

Generated: 2026-07-06

## Current Live Impression

The live site already has a strong literary tone and a premium first impression, especially on the homepage hero, Coming Soon board, and Shelf II-style presentation. The weakest issues are not pure aesthetics; they are trust and route truth issues: promoted reader/detail journeys can fail when production API data is unavailable, and audiobook visibility must be handled conservatively.

## Findings

| Area | Finding | Severity | Action |
| --- | --- | --- | --- |
| Release truth | Audiobook UI must not appear unless metadata, QA, release gate, and asset URL all prove approval | Critical | Added `audioReleaseSafety` helper and used it in cards/detail/reader |
| Reader trust | Browser/system speech fallback could be mistaken for audiobook availability | Critical | Reader now blocks fallback narration when release gate is not approved |
| Dracula detail route | Live audit showed `/book/dracula` could resolve to not-found/error when API was unavailable | High | Added controlled metadata fallback for Dracula only; no audio/content exposure |
| Reader route | `/reader/dracula` remains API-backed and can fail when reader manifest is unavailable | High | Improved error copy; did not create shadow reader content |
| Accessibility | Low-contrast gold microcopy and site-tour ARIA issue failed axe | High | Darkened readable gold token, added progressbar semantics, fixed dark-panel label contrast |
| CSS validity | Standalone audio player stylesheet used invalid `var(...) / alpha` syntax and `border-radius: full` | Medium | Replaced with valid rgba values and `999px` radius |
| Local validation | Local static routes hit production API and are CORS-blocked | Medium | Classified separately as local limitation; build/a11y shell still pass |

## Top 30 High-Impact Fixes

1. Preserve audiobook release-gate truth everywhere audio is referenced.
2. Remove public browser/system narration fallback.
3. Make reader-only states feel intentional, not incomplete.
4. Add approved audiobook spotlight only from provider-backed reader-manifest evidence.
5. Add premium audio-hidden badges to catalog cards.
6. Add detail-page trust panel explaining reader/audio/release truth.
7. Make approved audiobook entry points appear only after production manifest proof.
8. Keep `/api/books` conservative while allowing `/reader/book/:slug/manifest` to unlock reader audio.
9. Add tests for stale asset, release-gate, reader-manifest, and blocked-audio states.
10. Add formal weighted Luxury UX Index instead of vibe-based scoring.
11. Upgrade library audiobook shelf from “not live” copy to release-gate-controlled copy.
12. Improve loading skeletons for book detail.
13. Fix invalid audio player CSS.
14. Fix WCAG contrast for gold microcopy.
15. Fix site-tour ARIA semantics.
16. Ensure controlled Dracula metadata fallback does not expose unapproved content.
17. Keep reader content API-controlled until production reader manifests are reliable.
18. Validate all route changes from production build, not dev-only state.
19. Avoid generated screenshots/traces in git.
20. Continue same-origin deployed browser validation to remove localhost CORS noise.
21. Expand premium empty/error states for API failures.
22. Improve catalog discovery once live API can be tested same-origin.
23. Add reader route resilience only through approved content manifests.
24. Continue mobile polish on detail and reader flows.
25. Keep book-factory and UX branches/worktrees separate.
26. Add deployed preview Lighthouse/INP/LCP/CLS evidence before claiming 9.7.
27. Clean unrelated content/release artifacts from the UX diff before PR.
28. Verify approved audiobook controls on `a-ghost-story` same-origin reader route.
29. Add richer “continue reading/listening” once authenticated data is reliable.
30. Re-score after preview deployment with console/a11y/performance evidence.

## Latest Delta

- Added reader-manifest-aware approved audiobook spotlight for production-approved audio only.
- Added unit coverage around audiobook control visibility.
- Formalized the weighted Luxury UX Index and documented why the branch is not yet 9.7-ready.

## Screenshot Evidence

Generated screenshots are under `output/ux-rebirth/` and are intentionally ignored from git.
