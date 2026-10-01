# Production Analytics and Reading Funnel

Production: https://theearnalism.com

## Measurement layers

- Vercel Web Analytics measures aggregate visitors and page views. `@vercel/speed-insights` remains performance telemetry and is not a visitor counter.
- Earnalism's first-party `analytics_events` collection is authoritative for product journeys and conversion. It groups by a random anonymous browser-tab session ID and records `production`, `preview`, or `local` deployment environment.
- HTTP requests, API polls, health probes, static assets, and crawler activity are not counted as visitors. The Admin launch monitor displays human-facing client events, not server request totals.

## Event contract

| Event | Source and trigger | Conversion authority |
| --- | --- | --- |
| `page_view` | Router navigation to a customer-facing route; excludes admin and internal harness routes | No |
| `homepage_view`, `library_view`, `pricing_view` | Matching router location; duplicate effect replay is suppressed, a later back-navigation counts again | No |
| `title_view` | Book detail response loaded and slug matches the requested route | No |
| `reader_preview_started` | Reader displays a validated page whose runtime manifest marks it as preview | No |
| `signup_started`, `signin_started` | User submits an auth method; credentials are not recorded | No |
| `signup_completed`, `signin_completed` | Successful auth API response | No |
| `reading_pass_offer_viewed` | Live offer response is non-empty | No |
| `checkout_started` | Backend created a real provider order and top-up intent | No |
| `checkout_failed` | Provider initialization/failure/dismissal or order creation fails | No |
| `purchase_completed` | Server verifies captured payment and completes idempotent Reading Pass credit | **Yes, server only** |
| `listener_view`, `listener_started` | Verified runtime-approved playable manifest and active lease; emits nothing for unavailable audio | No |

`reader_preview_completed` has no event because there is no canonical completion threshold. `payment_success_return` is retained only as a legacy event name; it is not a purchase and is not used by the current commercial funnel. `checkout_started` and `purchase_completed` are not accepted as client-emitted events.

The full event/callsite inventory is [`analytics-event-inventory.json`](analytics-event-inventory.json).

## Definitions

- **Visitor:** Vercel's aggregate visitor estimate; not guaranteed to equal a unique person.
- **Session:** random ID held in `sessionStorage` for a browser-tab journey.
- **Page view:** one customer-facing route navigation; not a unique visitor.
- **Title view:** a matching, successfully loaded book-detail response.
- **Reader start:** a runtime-validated preview page is displayed.
- **Signup:** started is a form attempt; completed follows a successful response.
- **Checkout start:** a provider order and intent were created; this is not a purchase.
- **Purchase:** a captured payment was verified and the related Reading Pass credit succeeded.
- **Conversion rate:** anonymous sessions reaching the next ordered funnel stage divided by sessions reaching the current stage.

The Admin launch monitor reports today, 24-hour, 7-day, and 30-day production windows; session counts, page-view events, top routes, referrer categories, campaigns, and ordered funnels with conversion/drop-off. Preview and local events can be accepted for release verification but are excluded from production aggregates. Admin access remains protected by the existing authorization model.

## Attribution and privacy

- Anonymous journey IDs are tab-scoped; no raw visitor profile is constructed.
- Only pathname is stored. Query strings and continuation parameters are stripped.
- Safe attribution is limited to `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, and coarse referrer categories (`direct`, `organic`, `social`, `referral`, `campaign`, `unknown`).
- No passwords, tokens, provider credentials, payment identifiers, customer identifiers, names, emails, phone numbers, card/UPI/bank details, billing payloads, raw referrer URLs, or user-agent strings are included in newly stored events.
- Historical analytics documents are not rewritten and may contain metadata collected before minimization.
- Analytics ingestion and storage are best-effort. An analytics outage must not interrupt navigation, Reader, signup, checkout, wallet credit, or entitlement behavior.
- Vercel Web Analytics uses the platform's aggregate measurement. See [Vercel Analytics privacy documentation](https://vercel.com/docs/analytics/privacy-policy).

## Configuration and limitation

First-party event networking is disabled unless the frontend is built with `REACT_APP_ENABLE_LAUNCH_ANALYTICS=true`; tests can use the explicit window override. Web Analytics is a separate platform integration and does not depend on that first-party flag. Hosted Vercel/Web Analytics totals need processing time after deployment. The product funnel cannot stitch across tabs or safely identify people, so reports use sessions rather than individuals.

No production purchase is synthesized for verification. Purchase authority is tested through the verified payment/credit server path and retry-idempotency tests.
