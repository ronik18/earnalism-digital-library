# Growth Analytics Readiness

Status: `BLOCKED_ANALYTICS_GAPS`

| Event | Detected |
| --- | --- |
| page_view | False |
| book_view | False |
| preview_start | False |
| reading_started | False |
| reading_session_completed | False |
| pricing_view | True |
| checkout_start | True |
| payment_success | True |
| payment_failed | True |
| newsletter_joined | False |
| referral_invited | False |
| referral_converted | False |
| institution_interest | False |
| audio_preview_played | False |
| cta_clicked | False |

Schema artifact: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/analytics_event_schema.json`

| Mock Validator | Value |
| --- | --- |
| status | PASS |
| mock_payload_count | 8 |
| errors | [] |
| external_calls | [] |

Tests must keep analytics mocked/disabled and must not send real events. Missing canonical events cap the growth readiness score at `8.5/10` until instrumentation is complete.
