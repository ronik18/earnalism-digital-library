# Unpublished India website legal drafts

**Publication status:** `UNPUBLISHED_DO_NOT_REGISTER_ROUTE`. No route for these drafts is registered in `frontend/src/App.js`. Do not expose this file, its internal evidence references, or any bracketed owner-input field to the public site.

## Publication gate

Before a public legal page is registered, complete only the factual fields the source cannot establish: public business address; privacy and grievance contact channels; provider geography and cross-border access; actual production analytics state; retention decisions; and, if paid checkout is enabled, merchant agreement and cancellation/refund treatment. Check the final page against the deployed product; do not publish placeholders.

## Privacy Policy draft — factual scope only

Earnalism's source currently indicates collection or handling of account/contact/newsletter names and email addresses; support messages; browser authentication/session information; Reading Pass activity and position data; a browser device/session identifier; optional launch analytics; and payment-related checkout operations through Razorpay. Source inspection does not establish provider regions, cross-border access, retention periods, or whether optional analytics is enabled in production. This draft must not claim a retention period, data-sale practice, or provider configuration until those facts are confirmed.

Recorded operator fact: `REO ENTERPRISE`, sole proprietorship, operating Earnalism as its venture/brand. The public support address in source is `sales@reoenterprise.org`. Public fields still required: `[OWNER INPUT REQUIRED: public business address]`; `[OWNER INPUT REQUIRED: privacy-request contact]`; `[OWNER INPUT REQUIRED: grievance contact]`; `[PROVIDER VERIFICATION REQUIRED: hosting/database/storage/backup regions and access]`; `[DEPLOYMENT VERIFICATION REQUIRED: analytics enablement]`; `[OWNER POLICY REQUIRED: retention and account-deletion handling]`.

## Terms of Use draft — factual scope only

Earnalism provides controlled digital reading. The launch configuration holds Reader and audio exposure pending accepted release decisions. Source identifies a one-time prepaid Reading Pass model and no automatic renewal claim. Any final Terms must preserve non-waivable consumer rights, describe actual availability/change behavior, identify the operator and contact channel, and avoid representing held titles as released or any text as universally rights-cleared.

## Copyright/IP notice and complaint process

The public notice should invite a complainant to supply: contact details; the claimed work; the Earnalism title/content concerned; the basis of the claim; and supporting information. Internal handling is title-scoped: `RECEIVED` → `UNDER_REVIEW` → `TEMPORARILY_HELD` where warranted → `RESOLVED_REMOVE` or `RESOLVED_RESTORE`. A complaint for one title must not automatically disable other titles. This is not described as a DMCA process or government certification.

## Payment, cancellation, and refund terms

Do not publish these terms until the merchant agreement/version and the operator-approved treatment for unused prepaid time, pass expiry, service outage, title unavailability, cancellation, and refunds are verified. The existing UI's one-time-prepaid language is not a substitute for those facts or an approved customer remedy.

## Source basis

- `frontend/src/App.js`, `frontend/src/pages/Contact.jsx`, and `frontend/src/pages/Pricing.jsx`
- `frontend/src/lib/funnelAnalytics.js`, `frontend/src/lib/readingPassApi.js`, and `backend/server.py`
- Digital Personal Data Protection Rules, 2025 notification and Consumer Protection framework listed in `india-website-legal-matrix.json`
- Candidate commit: `23d8c7b629e88f42866f3592973c3809542e6317`; tree: `ea4ca75da612e9b5b6f745a8af880799056b4d28`.
