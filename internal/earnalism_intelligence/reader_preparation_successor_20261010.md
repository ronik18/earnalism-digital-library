# Reader preparation successor — qualification, not release

Base: `a8ecbacf2310e917071ef2b2c0b6063204814039` (merged #527).
Original reference: `9f8e9fc97cdbf9923eaa0c1bc992147593a1fff5`, tree
`d6d71308fb1bbb6d64d5dd670765b1901fde82f6`. The original commit, private
review/evidence and verified bundle remain unchanged. Archive ref:
`refs/archive/reader-preparation-original-20261010`.

## Integration

Preserved original first, then owner-authorized clean canonical alignment to
current main, then `cherry-pick --no-commit` of the original repair. No conflicts.
#527 response serialization, availability discriminator, admin UI/regressions
and owner-review workflow are unchanged relative to current main.
Reader service, UI lifecycle, API adapter and original qualification tests are
unchanged from the original repair. Shared schema adds only optional `text_phase`;
shared server adds only start/renew arguments, on top of #527's changes.

New work is qualification-only: real Mongo race tests and isolated browser
harness support for currently served public production frontend assets. No
admin compatibility implementation fix was needed. No rights, publication,
content, prices, balances, entitlement, territory or audio activation change.

## Fresh qualification

| Gate | Result |
|---|---|
| Current-main failing-before | Expected failure reproduced: delayed 19-chunk case Paused with only 75–83 delivered; 73 PASS / 1 expected FAIL. Private `opening-failing-current-main-a8ecbacf.log` |
| Successor frontend | 101 PASS: 93 Reader/chapter/content plus 8 admin reporting |
| Successor backend unit/API/security | 89 PASS: original 84 plus 5 admin summary regressions |
| Real Mongo | 26 PASS: 9 new preparation race cases plus 17 existing protected-text admission cases |
| Accounting | 16 preparation unit cases PASS; actual Mongo zero preparation/backdated debit, single durable debit under races, concurrent distinct historical-session settlement preserves balance |
| New frontend/new service browser | 390/768/1440 PASS; 16,212 / 16,262 / 16,212ms controlled-clock readiness; actual accelerated wall run 229 / 267 / 243ms, not production network latency |
| Actual served old frontend/new service browser | Slow opening Paused (old defect allowed), zero debit; fast opening formatting/readability PASS, subsequent 10s reading debit 10; no production APIs/sessions |
| Build | PASS; required hook 172 snapshots / 3647 assertions / zero failures. Date-only sitemap generation churn removed, not committed |
| Syntax/diff/JSON | PASS |

MongoDB 8.2.7: dedicated owner-authorized disposable localhost:27019 replica set
`readerPreparationUAT`, private temporary data path, real Motor/PyMongo
transactions and production-equivalent uniqueness constraints. All test
namespaces are synthetic UUID-scoped and dropped in `finally`; no production
database is used. Not a multi-node failover or exhaustive fault-injection claim.
The races cover duplicate/idempotent renewal, stale versions, prepare/readable,
readable/inactive, end/expire/revoke versus renew, and concurrent settlement.
One new-test fixture initially referenced `version` before assignment; corrected
the assertion placement without changing service behavior or expectations.
Browser teardown initially closed before public asset callbacks finished;
fixed harness drain ordering and reran successfully, without swallowing errors.
An aggregate run also exposed pre-existing test import-order configuration:
unit modules imported the server with Reading Pass disabled before Mongo
modules set their environment defaults. Requalification uses explicit enabled
UAT startup configuration and the dedicated synthetic test secret, not changed
production defaults or weakened denial expectations.

Private browser reports under the existing Reader archive:
`successor-browser/qualification.json`, `successor-mixed-fast/qualification.json`,
`successor-mixed-slow/qualification.json`. New frontend uses actual local build,
real pagination/fonts/layout, actual lease service with isolated in-memory DB
and synthetic transport. Mixed cases use actual served homepage/static assets
locally; all application API requests stay synthetic. No production Reader
route/session, account login or balance operation occurs. Code indentation and
superscript preserved; foreground/focus valid; no horizontal overflow.

Observed public production frontend:
`/static/js/main.c3879f85.js`
SHA256 `7a172d9f71731dd9bcc3ca65683688238237ece014399b46493aa232d8c046a2`;
Reader `/static/js/20.94fea4db.chunk.js`
SHA256 `04b3d097d03dfaf7e60bd1cfbe7780d632c2edd14822be8971b8cb9d944285cb`.
These bind observed served bytes, not an inferred source/deployment SHA.

## Fresh release authorization required

The original exact-head release authorization does not transfer. Review and
authorize the successor HEAD/tree/base from the private exact-head packet.
Next protected boundary: permission to publish the focused successor for
exact-head CI/review, protected merge and ordered deployment/acceptance.
No push, PR, merge, deployment or production Reader session happened here.

Deploy backend first, verify exact serving revision/health/contract with a
demonstrably nonpersisting qualification, then deploy the matching frontend and
bind its deployment/build/served assets. The old frontend remains safe but
retains its slow-opening defect during that window. Legacy sessions/audio
retain old behavior; optional signal is sent only when advertised.

Rollback is coordinated, not backend-only while preparation sessions remain:
gate new paid starts via the approved existing control, settle/drain preparation
sessions, restore the legacy frontend, then backend. New frontend can use old
responses without the field, but old backend cannot enforce the new preparation
bound and rejects a new field from an already-new session. Do not restore known
defective content or infer approval for production control mutations from this
plan. No migration/recovery is required. No additional #527 interaction risk
was found within tested serialization/reporting scope.

Post-release checklist: exact backend/frontend provenance; one ordinary-account
India-origin frontend → signed proxy → backend acceptance for Agentic AI With
Python; identity/eligibility, chapter-six 19 chunks, zero preparation debit,
valid rendered indentation/superscript, subsequent measured reading debit,
genuine inactivity settlement, saved logical position/away-back/full reload,
mobile/desktop layout, native zoom 125/150/restore100 last. Save each boundary.
Unsigned denial is separate negative evidence. On failure preserve the first
boundary; no repeated paid sessions, re-promotion or balance changes.

Existing promotion (generation1, 211 segments, manifest
`2d6e081a92bbeac0e5364cf2`) was not touched. Historical 13s deduction remains
separate: old starts enabled billing and renewal settled that prior interval
before `active=false`; exact timestamps/receipt are needed to determine the
pre-readable portion and any separately authorized correction.

PROMOTION_VERIFIED=YES
READER_PRODUCTION_VERIFIED=NO
READER_LANE_COMPLETE=NO
READY_FOR_SCOPED_TECHNICAL_SIGNOFF=NO
PERFORMANCE_WORK=PAUSED
SUCCESSOR_RELEASE_AUTHORIZED=NO

Next prompt: Review the fresh exact successor packet and authorize its protected
publication/release only, with backend-first deployment and one scoped production
Reader acceptance; no content, balance, #525, listener or purchase work.
