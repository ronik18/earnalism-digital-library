# Launch Monitoring Privacy Guardrails

Status: OWNER_ADMIN_ONLY_MONITORING_READY

## Scope

This policy covers first-party launch monitoring for The Earnalism Dracula reading-only production launch.

Public audiobook release remains blocked:

- public_audio_status: PUBLIC_AUDIO_RELEASE_BLOCKED
- audiobook_production_status: PRODUCTION_BLOCKED
- Listen Now CTA: not allowed
- AudioObject metadata: not allowed
- Kshudhita public CTA: not allowed

## Data Minimization Rules

Allowed event data:

- approved event name
- route
- book_slug
- anonymous session id
- timestamp
- safe metadata such as pack id, price tier, chapter id, metric name, metric value, and rating

Blocked event data:

- email
- phone
- customer name
- customer id
- raw Razorpay payment id
- raw Razorpay order id
- Razorpay signature
- webhook secret
- API keys or bearer tokens
- card, UPI, bank, IFSC, account, invoice, billing, or address details
- screenshots, invoices, or billing exports

## Endpoint Guardrails

`POST /api/analytics/event` accepts only the approved Dracula reading launch event names.

The endpoint rejects:

- unknown event names
- blocked metadata field names
- PII-like values
- payment-secret-like values
- nested payloads
- overly large metadata values

Analytics failure must never block reading, pricing, account, or payment flow.

## Dashboard Guardrails

`GET /api/admin/launch-monitor/summary` is owner/admin-only and returns aggregate counts only.

It does not return:

- user emails
- customer phone numbers
- payment ids
- order ids
- webhook payload bodies
- customer-level payment rows
- secrets or tokens

## Core Web Vitals

Core Web Vitals capture is first-party and opt-in.

Allowed metrics:

- LCP
- CLS
- INP
- FID
- FCP
- TTFB

Stored data is limited to metric name, value, rating, route, timestamp, and anonymous session id.

## Third-Party Tracking

No third-party pixels are approved for this launch monitor.

Blocked by policy:

- Google Analytics
- Meta/Facebook Pixel
- Hotjar
- Mixpanel
- Segment
- any unapproved third-party tracking pixel

## Owner Review

Owner should review dashboard output during the first 24 to 48 hours and confirm:

- payment successes match Razorpay dashboard totals
- wallet credits match successful payments
- duplicate webhook replay blockers remain visible
- support/refund queue is monitored
- public audio leak check remains clear
- public audiobook release stays blocked
