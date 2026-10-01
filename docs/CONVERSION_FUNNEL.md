# Earnalism production analytics

This document supersedes the earlier campaign funnel notes in this file. The
current event taxonomy and callsites are inventoried in
[`analytics-event-inventory.json`](analytics-event-inventory.json), and the
operating definitions and privacy rules are in
[`../READING_LAUNCH_FUNNEL_TRACKING_PLAN.md`](../READING_LAUNCH_FUNNEL_TRACKING_PLAN.md).

## Measurement layers

- Vercel Web Analytics is the source for aggregate traffic and page views. The
  separate `@vercel/speed-insights` integration measures performance, not
  visitors.
- The protected Admin launch monitor uses the first-party `analytics_events`
  collection for page journeys, product actions, and the ordered funnel.
- `checkout_started` is emitted by the backend only after it creates the real
  provider order and Reading Pass intent. `purchase_completed` is emitted only
  after verified payment and successful entitlement credit, and is idempotent
  across payment/webhook retries.
- A visitor estimate, browser-tab session, page-view event, checkout, and
  purchase are different metrics. Raw HTTP requests are never shown as visitors.

The Vercel project has Web Analytics enabled. First-party analytics networking
is configured with `REACT_APP_ENABLE_LAUNCH_ANALYTICS=true` for Preview and
Production. Production delivery becomes active when this source is deployed;
the Preview API intentionally remains isolated from the production backend.

No analytics event includes passwords, auth tokens, payment credentials,
customer identifiers, direct contact information, raw query strings, raw
referrer URLs, or user-agent strings. See the event inventory for legacy event
names and their current source/status.
