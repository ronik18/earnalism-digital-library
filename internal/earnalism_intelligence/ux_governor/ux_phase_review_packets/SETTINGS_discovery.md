# SETTINGS Discovery

Generated: 2026-07-08T10:02:29Z

## Phase Status

- Current phase: SETTINGS discovery only.
- Last approved phase: AUDIOBOOK_PLAYER.
- Owner decision recorded: `APPROVE_AUDIOBOOK_PLAYER_AND_PROCEED_TO_SETTINGS`.
- SETTINGS implementation is not started in this step.
- MARKETING_LANDING remains blocked until SETTINGS implementation, validation, owner review, and explicit owner approval.

## Files Inspected

- `frontend/src/pages/Reader.jsx`
- `frontend/src/components/SecureReader.jsx`
- `frontend/src/context/SettingsContext.jsx`
- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/pages/Reader.releaseTruth.test.js`
- `frontend/src/components/AudioPlayer.jsx`
- `frontend/src/components/AudioPlayer.releaseTruth.test.js`

## Current Settings Integration

Reader settings are implemented inline in `frontend/src/pages/Reader.jsx`; no separate Reader settings component was found. `frontend/src/context/SettingsContext.jsx` is a site/social/share settings context and is not the Reader reading-preference surface.

The Reader route remains `/reader/:slug`, and the settings sheet is opened by the topbar settings button with `aria-label="Open reading settings"`.

## Existing Reader Setting Controls

- Theme: `Light`, `Sepia`, and `Night`.
- Font size: `Small`, `Medium`, `Large`, `XL`.
- Line spacing: `Comfortable`, `Relaxed`, `Airy`.
- Reading width: `Narrow`, `Classic`, `Wide`.
- Bengali/English font mode:
  - Bengali: `Literary Bengali serif`, `Clear Bengali sans`.
  - English: `Editorial serif`, `Clean sans`.
- Reading focus: `Normal`, `Focus`.
- Reduced motion: `Calm`, `Reduced`.
- Highlight intensity: `Low`, `Medium`, `High`.
- Narration speed appears only when shared release evidence allows narration for the book.

## Accessibility Findings

- Settings controls use `role="group"`, `aria-labelledby`, `aria-pressed`, and specific button labels.
- The settings sheet is currently a dialog with `aria-modal="false"`.
- No explicit focus trap or focus-return handling was found for the settings sheet.
- TOC drawer uses `aria-modal="true"`; settings sheet does not currently match that modal behavior.
- Next implementation should verify keyboard order, visible focus, Escape/close behavior, focus return to the invoking settings button, and screen-reader announcement of setting state.

## Persistence Findings

- Reader preferences appear to be component-local `useState` values.
- No Reader preference `localStorage` persistence was found for theme, font size, line spacing, reading width, font mode, highlight intensity, reduced motion, or focus mode.
- Existing `localStorage` use in `Reader.jsx` is for auth/admin tokens and is not Reader preference persistence.
- Next implementation should add bounded, versioned preference persistence only if it does not break privacy, hydration, or shared-device expectations.

## Mobile And Layout Risks

- Settings and TOC must be verified at 390x844 and 430x932 before review.
- Long Bengali font-mode labels can wrap; implementation should keep labels dignified without causing horizontal overflow.
- Segmented controls need mobile-friendly wrapping and tap targets.
- Settings sheet should avoid covering essential reading controls without a clear close path.
- TOC drawer and settings sheet should maintain no horizontal overflow.

## Release-Gate Risks

| Title | Settings/Reader audio risk | Required behavior |
| --- | --- | --- |
| `book-2b9853ec52` | Approved Bengali pilot may expose Reader audio only from approved manifest/release evidence. | Keep evidence-gated; do not infer from slug or static path. |
| `a-ghost-story` | Paid Listen remains HOLD until production route/manifest/player proof. | No paid Listen expansion. |
| `book-d19e96859f` | ASR/source repair pending. | No Listen, player controls, narrator, duration, waveform, progress, or AudioObject. |
| `book-f5d593e1f4` | ASR/source repair pending. | No Listen, player controls, narrator, duration, waveform, progress, or AudioObject. |
| `muchiram-gurer-jibanchorit` | Representative timeout repair pending. | No Listen or player UI. |
| `pather-panchali` | Audiobook NO-GO pending full-work source/rights scope and cover repair. | No audio UI. |
| `bn-066` | Stage 1 ready, paid audition blocked by `paid_tts.lock`. | No paid audio UI while lock is active. |

## SETTINGS Implementation Target

- Calm, useful, accessible Reader settings.
- Light, sepia, and night themes remain clear and premium.
- Font size, line height, reading width, Bengali font mode, highlight intensity, reduced motion, and focus mode remain easy to understand.
- Bengali labels should be dignified and native, not technical.
- Reader settings should feel like a literary comfort panel, not a developer preferences drawer.
- Controls must be keyboard reachable and screen-reader sensible.
- Mobile settings and TOC must not overflow at 390x844 or 430x932.
- No audio controls or audiobook claims may appear unless approved release evidence exists.

## No-Regression Guardrails

- Do not modify HOME, LIBRARY, BOOK_DETAIL, READER, or AUDIOBOOK_PLAYER source during SETTINGS discovery.
- Do not touch `paid_tts.lock`.
- Do not run Sarvam, TTS, representative auditions, canary retries, upload, publication, metadata mutation, or release-gate mutation.
- Do not reintroduce static `/audio/...` derivation, browser/system speech fallback, word-level sync claims, or AudioObject for non-approved audio.
- Do not approve paid Listen campaigns.
- Do not claim full preview/production validation or launch-wide 10/10.

## Next Exact Command

```bash
cd /private/tmp/earnalism-parallel-prelaunch && sed -n '1,240p' internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/SETTINGS_discovery.md
```
