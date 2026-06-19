# Growth Analytics Readiness

Status: `PASS`

| Event | Detected |
| --- | --- |
| page_view | True |
| book_view | True |
| preview_start | True |
| reading_started | True |
| reading_session_completed | True |
| pricing_view | True |
| checkout_start | True |
| payment_success | True |
| payment_failed | True |
| newsletter_joined | True |
| referral_invited | True |
| referral_converted | True |
| institution_interest | True |
| audio_preview_played | True |
| cta_clicked | True |

Schema artifact: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/analytics_event_schema.json`
Mock sink supported: `True`

| Mock Validator | Value |
| --- | --- |
| status | PASS |
| mock_payload_count | 15 |
| covered_events | ['page_view', 'book_view', 'preview_start', 'reading_started', 'reading_session_completed', 'pricing_view', 'checkout_start', 'payment_success', 'payment_failed', 'newsletter_joined', 'referral_invited', 'referral_converted', 'institution_interest', 'audio_preview_played', 'cta_clicked'] |
| coverage_complete | True |
| errors | [] |
| external_calls | [] |

Tests must keep analytics mocked/disabled and must not send real events. Canonical events are schema-validated through a mock sink; production analytics should still be verified after operator-approved deployment.
