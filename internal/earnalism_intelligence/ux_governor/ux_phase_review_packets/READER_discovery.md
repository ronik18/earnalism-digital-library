# READER UX Phase Discovery

Generated: 2026-07-08T05:55:30Z

## Scope

BOOK_DETAIL is owner-approved for phase progression. READER is now the active UX phase in discovery-only mode.

This packet identifies the Reader implementation surface, comfort/a11y risks, and release-gate risks. It does not redesign Reader, run paid audio, mutate publication state, or approve launch.

## Routes And Source Files

- Route: `/reader/:slug` in `frontend/src/App.js`.
- Main component: `frontend/src/pages/Reader.jsx`.
- Reader shell and typography CSS: `frontend/src/index.css`.
- Secure text wrapper: `frontend/src/components/SecureReader.jsx`.
- Upsell component: `frontend/src/components/Funnel/ReaderUpsellPrompt.jsx`.
- Release-state gate: `frontend/src/lib/audioReleaseSafety.js`, imported by `Reader.jsx` as `canExposeAudiobookControls`.
- API path helper: `frontend/src/lib/api.js`.
- Cover resolver: `frontend/src/lib/bookCoverResolver.js`.
- SEO: `frontend/src/hooks/useSEO.js`.

## Content Loading Path

- Manifest load: `fetchReaderBook()` calls `${API}/reader/book/${bookId}/manifest`.
- Chapter load: `fetchReaderChapter()` calls `${API}/reader/chapter/${bookId}/${chapterId}`.
- Manifest normalization: `normalizeReaderManifestResponse()` places `data.audio` under `book._readerManifest.audio` and merges audio assets into `book.audiobook_assets`.
- Chapter HTML is sanitized by `sanitizeReaderHtml()` before rendering.
- Reader frontmatter is normalized by `extractReaderFrontMatter()`.
- Content is paginated by `paginateReaderHtml()`.

## Theme Logic

- Theme state: `theme`, default `beige`.
- Available themes in `THEMES`:
  - `beige`, displayed as `Light`.
  - `sepia`, displayed as `Sepia`.
  - `dark`, displayed as `Dark`; next phase should rename customer-facing copy to `Night` if owner wants exact spec alignment.
- Theme variables set CSS custom properties:
  - `--reader-canvas`
  - `--reader-surface`
  - `--reader-ink`
  - `--reader-accent`
  - `--reader-border`
- Theme classes:
  - `premium-reader--beige`
  - `premium-reader--sepia`
  - `premium-reader--dark`

## Settings Logic

- Font size: `FONT_SIZES`, `fontSizeIdx`, rendered in Reading Settings.
- Line height: `LINE_SPACING_OPTIONS`, `lineSpacingMode`, with separate English/Bengali values.
- Margin width: `READER_MARGIN_OPTIONS`, `marginMode`, mapped to `--reader-measure`.
- Bengali font mode: shared `fontFamilyMode` toggles `Serif` / `Sans`; Bengali maps to `BENGALI_SERIF` or `BENGALI_SANS`. The next implementation should label this as Bengali font mode when `isBengali` is true.
- Highlight intensity: `HIGHLIGHT_INTENSITY_OPTIONS`, `highlightIntensity`, with CSS classes `premium-reader--highlight-*`.
- Reduced motion: `reducedMotionMode`, class `premium-reader--reduced-motion`; global `prefers-reduced-motion` CSS also exists.
- Focus mode: `focusMode`, class `premium-reader--focus`.
- Settings sheet: `reader-settings-sheet`, dialog-like panel with segmented controls using `aria-pressed`.

## Typography Findings

- Bengali detection: `containsBengaliText()` checks title, chapter title, and content.
- Bengali body font candidates:
  - `BENGALI_SERIF = 'Noto Serif Bengali', 'Lora', Georgia, serif`
  - `BENGALI_SANS = 'Noto Sans Bengali', Inter, sans-serif`
- English body font candidates:
  - `READER_SERIF = 'Lora', Georgia, serif`
  - UI fallback via `UI_FONT`.
- CSS has dedicated `.reader-content--bengali` and `.reader-content--english` rules.
- Risk: settings copy currently says `Font` with `Serif` / `Sans`; Bengali-specific dignity may improve if the implementation phase uses localized labels and confirms Bengali line-height in screenshots.

## Mobile Reading Risks

- Mobile controls are topbar plus bottom bar, with settings as a sheet.
- Required implementation validation should capture:
  - `/reader/book-2b9853ec52`
  - `/reader/a-ghost-story`
  - `/reader/radharani`
  - `/reader/dracula`
  - mobile `390x844` and `430x932`.
- Risks to verify:
  - Bottom audio/reader controls can crowd page navigation.
  - Long Bengali titles in the topbar can truncate too aggressively.
  - Settings sheet height and segmented controls may overflow on short mobile screens.
  - TOC drawer uses fixed width `w-72`; verify no horizontal overflow.

## Accessibility Risks

- Strengths:
  - Settings and TOC open controls have accessible names.
  - Settings use `aria-pressed` for segmented controls.
  - Reading progress range has an aria label.
  - Top-up modal uses dialog semantics.
- Risks for implementation phase:
  - Settings sheet uses `role="dialog"` with `aria-modal="false"`; verify keyboard focus and escape/close behavior.
  - Segmented controls need visible focus states in all themes.
  - Theme contrast must be verified for dark/night and sepia.
  - Reader topbar and bottom controls should remain keyboard reachable when auto-hidden.
  - Settings controls expose state via `aria-pressed`, but the group labels are spans; consider `fieldset`/`legend` or `aria-labelledby` if needed.

## Performance Risks

- Pagination measures content in a hidden DOM node after load and on resize.
- Generated audio highlighting uses requestAnimationFrame/timeouts during playback.
- Chapter prefetch can run when the user is eligible.
- Asset prefetch can fetch generated audio manifest/timestamps for next chapter if audio is allowed.
- Risk: long Bengali books may create heavy hidden measurement work and layout shifts; implementation should profile mobile route smoke before visual claims.

## Release-Gate Risks

| Risk | Current Finding | Required Next-Phase Action |
| --- | --- | --- |
| Browser/system speech fallback | `Reader.jsx` contains `window.speechSynthesis` and `SpeechSynthesisUtterance`; `startTTS()` currently prefers approved generated audio and otherwise shows a toast, but browser speech code remains in component. | Remove, isolate, or prove it cannot be presented as audiobook. No public fallback speech-as-audiobook. |
| Static audio fallback | `audioAssetUrl()` can derive `/audio/${lang}/${slug}.mp3` and timestamps paths. `hasGeneratedAudioEnabled()` gates through `canExposeAudiobookControls()`, but missing explicit assets could still derive a stale route after approval metadata. | Require explicit manifest/assets for public audio or document safe fail-closed behavior. |
| Word-level claim | Source has word-level internals (`tts-word`, timestamp word offsets) and legacy component comments outside Reader. Current customer copy says `Section-following narration` and `Paragraph/Stanza Sync`. | Keep customer copy section-following only; do not claim word-level sync. |
| Approved controls | `hasGeneratedAudioEnabled()` returns false unless `canExposeAudiobookControls(book)` passes. | Preserve shared release-state gate. |
| Bengali pilot | `isNarrationDisabledForBook()` special-cases `LIVE_APPROVED_SLUG` as disabled. This may be stale after the pilot is live if Reader manifest evidence now exists. | Audit carefully in implementation; do not expose pilot audio unless manifest/endpoint evidence passes. |
| Audio metadata | Hidden `<audio data-testid="generated-audiobook">` renders only when `generatedAudioSlug` exists. | Verify with visual smoke and DOM checks that non-approved books do not create audio element/player controls. |

## READER Target For Implementation

- Quiet reading room.
- Calm literary typography.
- Comfortable Bengali and English reading.
- Light, sepia, and night themes.
- Useful and accessible reader settings.
- No oversized or claustrophobic text.
- No horizontal overflow on `390x844` and `430x932`.
- No browser/system speech fallback presented as audiobook.
- No fake audiobook, stale audio URL, or static audio fallback.
- No word-level sync claim for paragraph/stanza sync.
- No paid audio, production mutation, or launch-wide 10/10 claim.

## Recommended Next Implementation Scope

1. Preserve manifest-gated audio controls.
2. Remove or hard-disable browser speech fallback from public Reader UI.
3. Ensure static `/audio/...` derivation cannot expose stale audio without explicit manifest assets.
4. Improve settings accessibility labels and Bengali font-mode wording.
5. Validate mobile settings, TOC, and bottom controls.
6. Add READER-scoped visual smoke only if needed, without weakening full-route smoke.

## Next Exact Command

```bash
cd /private/tmp/earnalism-parallel-prelaunch && sed -n '1,260p' internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/READER_discovery.md
```
