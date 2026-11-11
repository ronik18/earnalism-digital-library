# Reading Pass purchase invoices

New verified purchases create one immutable commercial invoice in the same Mongo
transaction as the pass credit, wallet transaction, ledger and audit event. Both
checkout verification and signed webhooks use that existing credit service.
Replayed callbacks do not create another invoice or credit. Existing credited
payments are not backfilled or emailed by deployment.

The invoice contains REO ENTERPRISE's published name/address, buyer email captured
at checkout, a unique purchase-derived invoice number, issue date, minutes,
amount/currency and payment reference. It is included in the email body and as a
self-contained printable HTML attachment. No scripts, tracking pixels or remote
assets are included. The retained owner facts say the seller is not GST-registered;
no GST is collected or represented as a tax invoice. This does not enable UK/US
paid sales, change prices or alter accounting/refund policy.

## Existing business SMTP

The selected mailbox is `sales@reoenterprise.org`, hosted by Google Workspace.
The application uses `smtp.gmail.com:587`, verified STARTTLS and a Google app
password, never the mailbox's normal password. Credentials stay in Railway secrets.

- `PURCHASE_INVOICE_EMAIL_ENABLED=false` is the safe source/default state.
- `PURCHASE_INVOICE_SMTP_USER=sales@reoenterprise.org`
- `PURCHASE_INVOICE_SMTP_PASSWORD`: the mailbox's app password, supplied privately.
- Enable with `PURCHASE_INVOICE_EMAIL_ENABLED=true` only after source/CI and SMTP
  configuration is ready for the qualified release. Startup performs TLS/login only
  and logs `Purchase invoice SMTP authentication verified`; it sends no test mail.
  Verify actual delivery only with a separately approved owner-mailbox test.

Do not paste the password into chat, source, shell arguments, reports or logs.
Only the account owner creates/enters credentials. If the organization's policy
does not allow app passwords, retain the existing protection and use an approved
OAuth/relay configuration instead; do not disable account security.

## Delivery and operational semantics

One task per API process claims Mongo outbox rows atomically across replicas.
It uses the existing application DB client, one SMTP submission at a time,
five-second socket timeouts, a 300-second claim lease and at most three attempts
with bounded delay. No new Mongo client or generic worker pool is created.
SMTP acceptance marks the row `sent`; it is not proof of inbox placement/read.
SMTP cannot guarantee exactly-once delivery after an ambiguous acknowledgement.
A recovered lease can send the same invoice again with the same Message-ID and
invoice number. This never creates another bill or wallet credit.

Email failures modify only delivery metadata. Invalid billing details are held
as `review_required`; test payments are `suppressed_test`. Three failed attempts
remain `failed` for support reconciliation, without restarting the payment or
resetting any credit/observation counter. Normal queries use two narrowly scoped
outbox indexes. The explicit invoice flag authorizes only this transactional-mail
worker and its invoice indexes, including while `cap-only-v1` is retained.
Reader publication, general startup maintenance, all other background-job flags
and every historical grant/counter/recovery gate remain unchanged. Never disable
acceptance containment to enable invoice delivery. With invoice email disabled,
no invoice worker or invoice-index startup occurs.

## Qualification

Mandatory regression includes `backend/tests/test_purchase_invoices.py`: synthetic
callback races, legacy replay, invalid/header-injected data, test-payment
suppression, invoice rendering, SMTP TLS ordering and redacted/bounded failure.
The existing disposable Mongo harness additionally verifies atomic rollback,
concurrent callbacks and cross-worker claims. It creates no actual payments,
customer invoices or SMTP messages. A separate owner-approved business-mailbox
test is needed to verify actual delivery; never use a real purchase as a test.

Historical purchase/native recovery validators, both Git histories and consumed
limits remain unchanged. The active source-only protocol pin and generated
source inventory must reflect the exact committed new server, while historical
source and native bindings remain preserved and fail closed.
