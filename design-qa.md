# Listening Room homepage visual QA

Visual source: approved Option B mock at `/Users/ronikbasak/Documents/ChatGPT Image Sep 28, 2026, 09_31_05 AM.png`.

| Viewport | Before (production Option B) | After (local production build) | Result |
| --- | --- | --- | --- |
| 1440px | `/Users/ronikbasak/.codex/worktrees/optionb-production/earnalism-digital-library/production-screenshots/option-b-1440.png` | `/tmp/earnalism-listening-room-qa/full-1440.png` | 4 discovery cards; 4 benefit columns; Reading Room in 45/55 composition; no horizontal overflow |
| 1024px | `/Users/ronikbasak/.codex/worktrees/optionb-production/earnalism-digital-library/production-screenshots/option-b-1024.png` | `/tmp/earnalism-listening-room-qa/full-1024.png` | Discovery and benefits use 2-column layouts; Listening Room remains balanced; no horizontal overflow |
| 390px | `/Users/ronikbasak/.codex/worktrees/optionb-production/earnalism-digital-library/production-screenshots/option-b-390.png` | `/tmp/earnalism-listening-room-qa/full-390.png` | Discovery stacks to one column; Listening Room copy precedes image; no horizontal overflow |

The first rendered pass exposed a missing `Leaf` icon import. The import was corrected and the rendered page was recaptured at all three widths. Browser validation reported no page exceptions. With `PUBLIC_AUDIO_EXPOSURE_ENABLED=false`, the Listening Room remains discoverable, while title-specific `Listen` links and audio elements are absent.

The local public commerce flag is disabled, so this preview renders the existing non-commerce Reading Pass state. No prices, payment controls, or entitlement behavior were changed.

Visual review confirms the approved cream/burgundy hierarchy and official production logo remain intact. The new still-life image keeps books central and the headphones secondary to the wider page. No production change has been made. Protected PR checks, merge, deployment, and production smoke remain pending.

final result: passed locally; awaiting protected CI and production release
