# Minimum IN / US / UK commerce implementation

This change supplies offline tools and customer cancellation information. It does not reopen purchases, accept new rights, change territory guards, issue invoices, qualify live financial behaviour or authorise another observation. No claim of complete legal compliance is made.

## Implemented

- Existing exact component, checksum and rights validators are reused by `python3 -m scripts.compliance_readiness`. It inventories every controlled publication, distinguishes Reader and audio scope for IN/US/GB, reports current commerce facts separately, and never writes release state. The report uses the current package decision, not proposed intake records. A missing current US scope does not erase historical US acceptance. Separate audio package authority remains an additional requirement.
- `python3 -m scripts.commerce_accounting PRIVATE_EXTRACT.json` reads existing normalised evidence only. It produces balanced per-currency draft journals, receipt/credit-note data, per-payment reconciliation exceptions and an input digest. It has no network, DB or provider adapter. No output is an issued tax invoice, payment receipt from a provider or independent evidence of source authenticity.
- Identical event replay is collapsed; conflicting IDs, repeated economic references, missing captures, overspending, invalid/refund allocations, unknown fields, currencies and unsupported adjustment types fail. Outstanding and negative per-payment clearing balances cannot cancel each other into false reconciliation.
- Terms now accurately disclose the purchase pause and offer a direct request email and downloadable optional cancellation form. Existing mandatory remedies, no expiry and no auto-renewal remain unchanged. UK paid checkout is still disabled, so no ineffective consent checkbox is added to an unavailable flow.
- Named grievance officer is reconciled with the already accepted contact; record-retention guidance no longer assumes an external accountant.

## Exact evidence input contract

The accounting input is an object with `schema: earnalism.accounting-extract.v1`, `scope: complete_payment_histories` and an `events` array. Supply the complete history of each included payment, not a calendar-month fragment. Every event needs `id`, `kind`, `reference` (unique economic event), `payment_id`, `currency` (INR/USD/GBP), timezone-aware `at` and retained `evidence_sha256`. The normaliser is responsible for independent authenticity, joins and true ordering; an input hash is not a provider attestation.

Additional fields:

| kind | fields |
|---|---|
| capture | gross_minor, tax_minor, granted_seconds, tax_snapshot |
| usage | delivered_seconds |
| refund | returned_seconds, gross_minor, tax_minor |
| settlement | gross_minor, fee_minor, bank_minor, bank_evidence_ref |

Tax snapshot needs country, classification, rule_version, tax_point, registration_basis, customer_location_evidence_ref and US state where relevant. The supported tax point is capture only. These fields must come from the actual reviewed tax treatment; the tool does not infer a rate or validate a tax number. Amounts are integer minor units. Usage recognises the net allocated consideration cumulatively; unused seconds retain their liability. Rounding uses cumulative delivered plus refunded seconds, with earlier recognised/refunded allocation retained, so the final cent is allocated once. Refunds must match that allocation or require a separately reviewed adjustment path.

Provider fees are gross expense, not automatically eligible input tax. No FX revaluation, cross-currency payout, chargeback, redemption-tax voucher or consumed-time refund is silently posted. Unsupported evidence requires its appropriate reviewed journal path, rather than deleting the event. Draft exports are private customer/accounting data: store outside git/public assets with restricted permissions. Never place real extracts in tests or build artifacts.

## Remaining essential facts and activation work

`business_facts.json` retains the existing sole-proprietor evidence and the owner’s 8 November confirmation: not GST registered, PAN-wide service turnover not above INR 20 lakh, not UK VAT registered and no US physical presence. It separately records remaining applicability: financial-year boundaries and other compulsory registration triggers, mixed Reading Pass classification/tax point, actual invoice/settlement operation, US economic nexus/taxability, UK VAT route, UK consumer flow and privacy scope. Owner-confirmed absence of registration is not a tax exemption. VERIFIED fields are pointers to inspect, not authenticated admission tokens. This report cannot override the runtime purchase pause or any historical recovery validator.

Before paid country activation, complete those applicable facts, connect a qualified existing-evidence normaliser and invoice issuance/storage path, implement the resulting checkout fields/consents and satisfy current financial acceptance under actual authority. This is incomplete while those facts and operations remain unqualified. A blocked country or format does not block independently cleared work. No new CA/lawyer approval is invented, but statutory filings, audit or representation that actually apply cannot be waived.

Official bases: [HMRC digital VAT](https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers), [ebook/audio distinction](https://www.gov.uk/guidance/zero-rating-books-and-printed-matter-for-vat-notice-70110), [CBIC service rates](https://cbic-gst.gov.in/hindi/gst-goods-services-rates.html), [UK cancellation law](https://www.legislation.gov.uk/uksi/2013/3134/part/3/made). Full research remains in the private planning packet prepared 8 November 2026. Tax rules are versioned by effective date; this code is not a tax engine.

## Preservation and release

Reader PR661 remains separate at d048a2bfc883039811ea1c606d4b98f331030d6e. Payment remote head remains 5e739e69d3086a14d83f802f7cc5b3da9b90ddf0. No runtime backend source or release manifest is changed here. All six consumed observations remain consumed; there is no seventh claim, capture, paid session or load test. Merge/deploy only through the existing exact-head regression, build and protected release pipeline. A CLOSED informational frontend deployment is distinct from opening international commerce.

## Local qualification

145 focused Python tests passed, including unchanged rights/intake/closure/territory tests and 17 new accounting/inventory cases. Eight frontend tests passed. Node 24 production build completed; 172 static snapshots passed 3704 assertions, including non-JavaScript cancellation links. First isolated static generation lacked the unchanged root launch fixture; it was supplied from HEAD and the complete final build passed. All 48 original operation-journal files match the retained pre-release hashes. CI and deployment are separate outcomes and are not asserted here.
