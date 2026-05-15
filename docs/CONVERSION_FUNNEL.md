# Earnalism Conversion Funnel

## Component Layout

```text
Instagram / YouTube traffic
        |
        v
/micro-story
  - three 3-minute story previews
  - Afternoon Pause CTA, pack 30m, INR 49
        |
        v
/pricing?pack=30m
  - selected pack highlight
  - Razorpay top-up through existing payment flow

Reader page
  - chapter completion reaches the bottom
  - one contextual prompt per browser session
  - An Evening In CTA, pack 1h, INR 89
  - 48-hour EVENING15 coupon timer in localStorage

Reader completion rewards
  - completion event sent to backend
  - 3-day streak unlocks a 10-minute wallet credit
  - credit is idempotently claimed through REST
  - toast confirms credit without interrupting reading

Weekly email
  - use the behavioral template in docs/BEHAVIORAL_EMAIL_TEMPLATE.md
  - merge reading minutes and discount URL from email provider
```

## Analytics Events

- `micro_story_hero_cta_click`
- `micro_story_card_cta_click`
- `pricing_pack_cta_click`
- `pricing_test_purchase_complete`
- `reader_upsell_shown`
- `reader_upsell_cta_click`
- `reader_upsell_dismissed`
- `reader_completion_recorded`
- `reader_reward_claimed`

Events are stored through `POST /api/analytics/events`. The endpoint stores event names, sanitized metadata, role/id when available, referer, user agent, and timestamp. It does not store request bodies, tokens, manuscript text, or payment secrets.

## Current Tier Prices

- Afternoon Pause: INR 49
- An Evening In: INR 89
- Long Weekend: INR 239
- The Reader's Reserve: INR 499
