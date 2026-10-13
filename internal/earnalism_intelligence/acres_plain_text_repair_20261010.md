# Acres plain-text preservation — local qualification only

Base: d79acb1952161cd56395e9bb4d7c1001ceaa69bb, aligned by authorized fast-forward.
No production changes, new publication authorization or active generation edits.

The manual Reader source-type detector matched arbitrary angle-bracket notation
as HTML. Sanitizing literal `Ph<oe>nixville,` removed the unknown `oe` tag,
producing `Phnixville,`. Retained Chapter 008 and its source hash remain unchanged.

The minimal local change recognizes supported Reader/standard HTML and unsafe
HTML tags. Arbitrary plain-text notation uses the existing html.escape paragraph
path. HTML still uses the unchanged sanitizer, attributes and URL restrictions.
No sanitization bypass, global sanitizer change or artwork modification.

Before: focused rendering tests 5 PASS / 2 FAIL (literal ligatures and unknown
notation). After: rendering plus existing content-processor safety 14 PASS.
Tests cover semantic paragraphs, angle-bracket escaping, `<oe>` and `<ae>`,
legitimate HTML, code indentation, superscript, malicious scripts/attributes/
URLs, recognition of every current sanitizer-supported tag, and the complete
hash-bound retained Chapter 008. Independent review confirms full chapter text
preservation. Mixed genuine HTML plus unknown notation remains on the existing
sanitizer path; this fix is for the demonstrated genuine plain-text source.

Changed content requires a new immutable version/hash and separately authorized
inactive storage/readback/promotion. Existing generation 1 is untouched. Native
local candidate binding evidence lives in the existing private programme packet;
it does not constitute publication QA or paid Reader acceptance.

Pilot qualification found a distinct reuse contract gap: native ingestion
READY/UNCHANGED differs from publication INGESTED/CLEANED, and generated-section
edition/visual QA is not existing canonical-text/owner-cover QA. Do not backfill
statuses or replace healthy text. Existing accepted upper-bound rights evidence
for My Life and Work remains valid with verified in-memory hash aliases and null
first-publication year. Final publication QA remains unverified.

#525 parked; Yugalanguriya privately excluded; production/deployment holds retained.
Next: independently review this local detector correction and qualify a genuine
reuse-only evidence adapter before any protected code-release decision.
