# Earnalism payment receipt · Task A

Isolated design implementation. All fixtures are synthetic and visibly marked SAMPLE. No sending, payment processing, credentials, database access, or production integrations are included. Only this directory is changed.

## Deliverables

`output/receipt.pdf` is generated directly from `output/receipt.html` by installed Chromium 149 using DevTools `Page.printToPDF`, with A4 CSS and tagged PDF enabled. It is not independently typeset. `output/receipt-preview.png` is rasterized from that actual PDF using macOS PDFKit. Desktop and 390/320 pixel receipt and email PNGs, schema, JSON sample, HTML, plain text email, and an unsent MIME fixture with exact PDF attachment are included in the source ZIP.

## Contract v1.0.0

`receipt.schema.v1.json` is Draft 2020-12 JSON Schema. Required fields:

- `schemaVersion: "1.0.0"`, `templateVersion: "receipt-not-registered-v1"`, `sample: true`
- `receiptNumber`, `orderNumber`, `capturedPaymentReference`
- `issuedAtUtc`, `capturedAtUtc`: strict calendar-valid UTC timestamps ending in Z
- `sellerSnapshot: {legalName,address,supportEmail,website}`
- `buyerSnapshot: {name,email}`
- `productSnapshot: {name,durationSeconds,quantity,unitAmountPaise}`
- `amounts: {paidAmountPaise,currency}`
- `gstStatus: "NOT_REGISTERED"`, `paymentStatus: "CAPTURED"`
- `entitlementStatus: "PENDING" | "ACTIVE" | "EXPIRED" | "REVOKED"`

This intentionally narrow contract supports only one Earnalism Reading Pass, 1800 seconds / 30 minutes, paid amount 4900 integer paise INR. The display is exactly ₹49.00. An upstream system must supply references, capture truth, amounts, immutable snapshots, and entitlement truth. No identifier generation, capture decision, access activation, or tax calculation occurs in the template. UTC is retained in data and semantic time attributes; display uses Asia/Kolkata (IST). Issuance before capture is rejected. Unknown fields, invalid dates, unsupported versions, non-integer money, other currencies/statuses and GST registration modes fail closed.

`sample: true` is deliberately required for this deliverable. Production issuance requires a separately reviewed contract/version; removing a SAMPLE label alone does not authorize issuance. A future registered template could be added under a separate version and schema, but is disabled here; `REGISTERED` is rejected. There is no GST line, GSTIN, SAC, exemption claim, or tax math.

## Safety and email

Every supplied display string is escaped at interpolation; no raw HTML property exists. Fixed href values are constrained by seller snapshot constants. Control characters and bidi overrides are rejected. The renderer clones supplied data and does not mutate it. The dependency-free validator implements the subset of schema keywords actually used; the schema was independently checked with Python jsonschema Draft 2020-12.

`renderEmail` uses table-based payment details, inline styling, a CID logo, plain text alternative, semantic headings and scoped table headers. `email-fixture.mjs` creates only a local `.eml` fixture, addressed to a reserved `.invalid` recipient, with no transport. Its PDF attachment is the exact rendered file and is verified after base64 decoding. Email preview embeds the same logo as a data URI; the MIME HTML uses `cid:earnalism-logo`. Email-client compatibility was not tested against Outlook/Gmail services; browser checks are not a claim of inbox certification.

## Reproduce

Requires Node >=22 and an already available Chromium renderer. No npm installation is required.

```sh
node build.mjs
CHROMIUM_EXECUTABLE=/absolute/path/to/installed/chromium node verify.mjs
node email-fixture.mjs
node --test test/*.test.mjs
swift -module-cache-path /tmp/receipt-swift-cache verify-pdf.swift "$PWD/output"
```

The browser runs with a new temporary profile and blocks HTTP(S) assets. No remote assets are needed for printing. `verify.mjs` exports the PDF and checks receipt and email at desktop, 390px and 320px, accessible main/headings, broken images, overflow, rupee display, A4 content bounds, maximum schema-length fields, and WCAG AA text contrast. Gold is decorative. `verify-pdf.swift` independently confirms one A4 page and required extracted text, then creates the actual PDF preview. This is focused accessibility verification, not a full assistive-technology audit.

## Provenance and scope

Public homepage read on 2026-10-24 UTC: https://theearnalism.com. Its rendered header references https://theearnalism.com/assets/brand/earnalism-brand-lockup.png. Downloaded asset SHA-256: `951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919`. Asset pixels are unchanged, inspected visually and embedded locally. `brand-asset.mjs` verifies the checksum before rendering.

The repository patch symlinks the already present, byte-identical frontend brand asset to avoid duplicating binary content. The standalone source ZIP dereferences that symlink and contains the actual PNG bytes, so it runs without the rest of the repository.

Prior Library source `libfile_2f919a84e5e88191ac217c0fccccde31` was materialized with supported Library helpers and inspected. Its brand module and escaping approach were reused. The prior palette, tax illustration and independent ReportLab typesetting were not carried forward.

Exact palette: darkburgundy #521D32, deepburgundy #3E1727, parchment #FFFAF3, beige #F0E4D5, softgold #D6BC95, body #35292B. All required seller, product, support and GST wording follows the supplied brief.

Branch `task-a/receipt-design-20261025`, base `20aa0a020`. Repository AGENTS.md was read. Its canonical integration branch rule was superseded by the explicit task instruction to implement independently in an isolated worktree. No .agents directory exists in this checkout. No Reader/Listener, Railway configuration, PR540/552, production, payment integration, merge, deployment or customer email was touched.
