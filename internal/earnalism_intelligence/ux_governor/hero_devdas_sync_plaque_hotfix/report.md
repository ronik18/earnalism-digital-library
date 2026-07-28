# Home Hero Devdas Synchronization And Plaque Hotfix

Status: source, production build, responsive browser, interaction, and release-safety validation passed. The branch is intentionally uncommitted and not deployed.

## Root cause

Devdas was not a live carousel slide in the current production data. Its cover was part of the four-book row baked into `premium-library-reference-exact-1440.webp`. The earlier hero placed a small translucent metadata/control treatment over that row while rendering separately indexed canonical covers beside it. The mask did not cover the full baked row, so Devdas remained visible under metadata for an unrelated active slide.

## Repair

- Added an explicit ordered `hero_featured_slugs` curation sequence that omits Devdas while retaining Devdas in `sprint1_active_slugs`, the global catalog, and literary shelves.
- Kept a frontend fail-closed exclusion for the stable `devdas`, `debdas`, and `devdas-study-edition` slugs.
- Normalized each hero record to one stable slide object and derived the active cover, title, author, destination, alt text, accessible label, counter position, and data identity from that object.
- Replaced the pointed/fragmented treatment with a fixed-height editorial plaque and 44px control dock in a dedicated CSS Grid column.
- Replaced the complete baked book-row region locally, then rendered one dominant active canonical cover with restrained previous/next covers in a separate 3-D stage.
- Reconciled failed image preloads back to the visible index so subsequent previous/next actions cannot jump.
- Preserved heading, CTAs, navigation, tablet, phone, benefits panel, feature rail, analytics hooks, routes, and audiobook release truth.

## Browser acceptance

Validated at 1536x864, 1366x768, 1024x768, 768x1024, and 390x844.

- Devdas in hero DOM: no.
- Meaningful desktop slides: exactly previous, active, and next.
- Active root/plaque/cover IDs: equal.
- Hidden focus targets: 0.
- Duplicate DOM IDs: 0.
- Horizontal overflow: 0px.
- Broken hero images: 0.
- Controls: 44x44 CSS pixels.
- One-step next navigation: pass.
- Pause and explicit resume: pass.
- ArrowRight navigation and keyboard-focus autoplay stop: pass.
- Mobile autoplay disabled: pass.

## Automated validation

- Backend home curation suites: 35 passed.
- Focused carousel/frontend suites: 21 passed.
- Related Home/frontend suites: 8 passed.
- Production build: passed.
- Curation JSON validation: passed.
- `git diff --check`: passed.
- Public/build audio file scan: no matches.
- Runtime browser-speech, static `/audio`, word-level-sync, and `AudioObject` scan: no matches outside test fixtures.
- Paid provider calls: none.
- `paid_tts.lock`: active, `current_holder: none`, `allowed_next_holders: []`.

The CRACO build emitted pre-existing missing local controlled-publication warnings during SEO generation. It still compiled successfully. Generated `robots.txt` and `sitemap.xml` changes were restored and are not part of this patch.

## Evidence

Before and after images are stored in the adjacent `before/` and `after/` directories for all five requested viewports. Detailed geometry and machine-readable acceptance results are in `acceptance.json`.

## Remaining limitations

- The protected desktop reference bitmap still contains its historical four-book row internally. The full catalog region is replaced visually because regenerating the bitmap would also risk altering the protected device and scene artwork.
- The local static browser cannot load production public settings, so it emits the expected local network warning. No hero/carousel console errors occurred.
- This repository has no standalone lint or TypeScript typecheck script; the configured CRACO production compilation passed.

Next exact command:

```bash
cd /private/tmp/earnalism-hero-devdas-plaque-repair && git diff --check && git status --short
```
