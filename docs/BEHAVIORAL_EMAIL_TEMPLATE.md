# Weekly Reading Upgrade Email

## Subject

You read {{reading_minutes_this_week}} min this week. Ready for the Long Weekend Edition?

## Preview Text

Your reading rhythm is building. Add three quiet hours with a reader-only upgrade.

## Body

Hi {{reader_first_name}},

You read {{reading_minutes_this_week}} minutes on Earnalism this week. That is a real streak, not noise.

If you want to keep the rhythm going, the Long Weekend pack gives you 3 hours of reading time for INR 239.

[Continue with Long Weekend]({{discount_link}})

Use code {{coupon_code}} before {{coupon_expires_at}}.

No subscription. No autorenewal. Just reading time when you want it.

Reo Enterprise

## Merge Fields

- `{{reader_first_name}}`
- `{{reading_minutes_this_week}}`
- `{{discount_link}}`
- `{{coupon_code}}`
- `{{coupon_expires_at}}`

## Notes

- Send at most once weekly.
- Suppress for readers who purchased any pack in the last 48 hours.
- Keep the CTA URL pointed to `/pricing?pack=3h&source=weekly_email`.
