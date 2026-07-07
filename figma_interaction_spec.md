# Earnalism Interaction Spec

## Conversion Events
- `hero_primary_cta_click`
- `hero_secondary_cta_click`
- `bengali_card_click`
- `english_card_click`
- `approved_audio_card_click`
- `book_card_read_click`
- `book_card_listen_click` only when approved

## Privacy Rule
Events use the existing sanitized first-party analytics helper. PostHog remains disabled unless `REACT_APP_ENABLE_POSTHOG=true`.

## Motion
- Soft entrance and hover motion only.
- Respect reduced motion preferences.
- No slideshow-heavy above-fold interaction.

## Audio
- Browser/system speech fallback is not presented as an audiobook.
- Expected gated/unavailable states are calm UI states, not errors.
