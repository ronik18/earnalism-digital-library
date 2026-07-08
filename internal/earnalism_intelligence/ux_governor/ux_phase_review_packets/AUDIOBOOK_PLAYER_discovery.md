# AUDIOBOOK_PLAYER Discovery

Generated: 2026-07-08T06:48:52Z

## Phase Status

READER is owner-approved for phase progression. AUDIOBOOK_PLAYER is now the active UX phase in discovery-only mode. No player redesign, paid audio work, publication mutation, release-gate mutation, or production validation was performed in this step.

## Scope

This discovery audits current audiobook/player exposure paths and identifies the safe implementation target for the next phase. AUDIOBOOK_PLAYER must not expose public audio from slugs, static paths, partial metadata, local fallback fixtures, or browser/system speech.

## Files Inspected

- `frontend/src/components/AudioPlayer.jsx`
- `frontend/src/components/AudioPlayer 2.jsx`
- `frontend/src/components/AudioPlayer.css`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`
- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/bookDetailPresentation.js`
- `frontend/src/components/JsonLd.jsx`
- `frontend/scripts/visual-luxury-smoke.mjs`
- `frontend/src/pages/Reader.releaseTruth.test.js`
- `frontend/src/lib/bookDetailPresentation.test.js`
- `frontend/src/lib/audioReleaseSafety.test.js`

## Active Audio Exposure Paths

| Surface | Status | Release-truth classification | Notes |
| --- | --- | --- | --- |
| `Reader.jsx` inline reader audio control | Active | SAFE_WITH_APPROVAL_GATE | Uses `canExposeAudiobookControls(book)` before generated audio availability or controls. Reader phase removed public speech fallback and static `/audio/...` derivation. |
| `BookDetail.jsx` Listen CTA | Active | SAFE_WITH_APPROVAL_GATE | CTA uses shared `bookDetailPresentationForBook(publicBook)`, which delegates to `audiobookReleaseState(publicBook)`. No ad hoc slug/title/static URL approval logic found. |
| `BookCard.jsx` Listen CTA | Active | SAFE_WITH_APPROVAL_GATE | Listen card only renders when `audiobookReleaseState(book).canShowControls` is true. |
| `ApprovedAudiobookSpotlight.jsx` | Active, optional | SAFE_WITH_MANIFEST_GATE | Fetches `/reader/book/:slug/manifest`, maps manifest audio into a book object, and hides itself unless `audiobookReleaseState` approves controls. Default slug is empty unless explicitly configured. |
| `JsonLd.jsx` / `BookDetail.jsx` structured data | Active | SAFE_BOOK_ONLY_CURRENTLY | Current Book Detail emits `@type: Book`; no active `AudioObject` path was found. |
| `AudioPlayer.jsx` | Not imported in active source scan | DEAD_CODE_PUBLIC_RISK_IF_RECONNECTED | Legacy component derives `/audio/${lang}/${bookSlug}.mp3` and `/audio/${lang}/${bookSlug}_timestamps.json`, exposes duration/progress, and describes word-level timestamps. Must be removed or rewritten before any public AUDIOBOOK_PLAYER implementation. |
| `AudioPlayer 2.jsx` | Not imported in active source scan | DEAD_CODE_PUBLIC_RISK_IF_RECONNECTED | Duplicate legacy component with the same static `/audio/...` and word-level timestamp risks. Must not be reconnected. |
| `InternalAudiobookPlayerPrototype.jsx` | Internal component | INTERNAL_ONLY_REVIEW_REQUIRED | Contains duration/progress prototype copy and must remain internal-only. Do not reuse for public player without release-state gates. |
| `frontend/public/service-worker.js` `/audio/` handling | Public service worker | INFRA_RISK_REVIEW | Service worker has `/audio/` fetch/cache handling. The player implementation must ensure no static public audio URL is derived or precached from unapproved metadata. |

## Search Classification

- `speechSynthesis` / `SpeechSynthesisUtterance`: no active public Reader/player source risk found in the current scan. Reader tests explicitly guard this.
- `/audio/`: public-risk tokens remain in legacy `AudioPlayer.jsx`, `AudioPlayer 2.jsx`, service worker handling, and tests. Active Reader source no longer derives static `/audio/...`.
- `word-level`, `word level`, `word sync`: active BookDetail and Reader tests guard against this copy. Legacy `AudioPlayer` comments still mention word-level timestamps and must be removed or rewritten before public reuse.
- `Listen`: active BookDetail, BookCard, and ApprovedAudiobookSpotlight render Listen/Open Audiobook only through shared release-state approval. Non-approved titles remain hidden.
- `narrator`, `duration`, `waveform`, `progress`: active Reader has a small waveform/progress UI only inside the approval-gated generated audio branch; legacy AudioPlayer has duration/progress public-risk if imported.
- `AudioObject`: no active public structured-data emission found; tests guard BookDetail source against `AudioObject`.
- `static audio fallback`: no active Reader static fallback after Reader phase; legacy players are static-path based and must be replaced.

## Title-Specific Release Gate Findings

| Title / slug | Current public audio status | Player requirement |
| --- | --- | --- |
| `book-2b9853ec52` / দুই বিঘা জমি | Only approved when current manifest/endpoint evidence is present | Player may render only from approved manifest assets and measured paragraph/stanza sync metadata. |
| `a-ghost-story` | Paid Listen remains HOLD pending production route/manifest/player proof | Do not mark paid-listen-ready from local metadata alone. |
| `book-d19e96859f` | No Listen; ASR/source repair pending | Player must remain hidden. |
| `book-f5d593e1f4` | No Listen; ASR/source repair pending | Player must remain hidden. |
| `muchiram-gurer-jibanchorit` | No Listen; representative timeout repair pending | Player must remain hidden. |
| `pather-panchali` | Audiobook NO-GO | Player must remain hidden. |
| `bn-066` | Stage 1 only; paid audition blocked by lock | Player must remain hidden. |
| Reader-first English/Bengali titles | Reading editions only | Player must remain hidden; no narrator/duration/waveform/progress or audio structured data. |

## Implementation Target For Next Phase

1. Replace or quarantine legacy `AudioPlayer.jsx` and `AudioPlayer 2.jsx` so no public code path can derive `/audio/${lang}/${bookSlug}.mp3`.
2. Build any public player from a shared approved release-state object and explicit approved manifest assets only.
3. Require provider-backed audio URL, sidecar URLs, checksum/version metadata, and approved release state before rendering controls.
4. Describe sync as `section-following narration` or `paragraph/stanza sync`; never claim word-level sync unless true word-level sidecars exist and are approved.
5. Keep `JsonLd` as Book-only unless approved audio structured-data policy is explicitly implemented and evidence-backed.
6. Keep `ApprovedAudiobookSpotlight` optional and manifest-gated; no default A Ghost Story probe.
7. Add tests that prove legacy static player paths are not importable/usable in public routes, non-approved titles show no controls, and approved controls require manifest evidence.
8. Add AUDIOBOOK_PLAYER visual smoke only after implementation; do not weaken strict default full-route smoke.

## Accessibility And Mobile Risks

- Controls need clear accessible names for play/pause, seek, volume, transcript/sync status, and close/minimize states.
- Mobile player must avoid horizontal overflow at 390x844 and 430x932.
- Reduced motion must be respected for waveform/progress animation.
- Keyboard focus order must not trap the reader or hide settings/TOC access.

## Performance Risks

- Do not preload audio for hidden/non-approved titles.
- Do not prefetch static `/audio/...` assets from slug-derived paths.
- Do not add heavy waveform libraries for decorative effects.
- Use metadata preload only after approval and explicit user intent where possible.

## Release-Truth Guardrails

- No browser/system speech fallback as audiobook.
- No static `/audio/...` fallback.
- No player route or controls from slug/title/language/narrator/duration/local fallback metadata.
- No stale audio URL exposure.
- No `AudioObject` unless approved audiobook evidence and structured-data policy explicitly allow it.
- No paid Listen campaign claim for A Ghost Story until production route/manifest/player evidence passes.
- No public controls for Bengali canary repair titles or prelaunch candidates.

## Next Recommended Action

Start AUDIOBOOK_PLAYER implementation only after this discovery is reviewed. The first implementation step should quarantine or rewrite the legacy `AudioPlayer` components before adding any player-facing polish.

## Next Exact Command

```bash
cd /private/tmp/earnalism-parallel-prelaunch && sed -n '1,260p' internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/AUDIOBOOK_PLAYER_discovery.md
```
