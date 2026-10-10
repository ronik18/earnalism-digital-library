# Nonbillable Reader preparation — local qualification only

Starting HEAD: `6b6de845518ba88c2c242afd1b25cd709806265d`.
Owner scope: loading/readable/inactive lease correction. No production operation,
content recovery, publication/configuration change, refund or #525/admin work.

## Demonstrated failure and contract

Retained failing-before: 19 required chunks (75–93); only 75–83 delivered at
16.112s, assembly/pagination pending. The 10s inactive heartbeat paused before
readability. Fast complete delivery passed. This is a local reproduction, not
a retrospective proof of every production request's completion time.

Paid HTTP text starts now advertise `text_phase=preparing` with billing off.
The server deadline uses the unchanged maximum lease (default 20s); renewals
cannot extend it. Only a validated visible protected fragment in a focused
foreground tab signals `readable`. Billing starts then, never backdated.
`inactive` settles the preceding billable interval and pauses. Failed, hidden,
blurred, abandoned and expired preparation cannot be billed as active reading.

A per-user/publication-version anchor survives session/device restarts. A
positive settled reading debit releases it; otherwise a fresh bounded start
requires retained deadline + unchanged inactivity interval (default 120s).
This is a retry cooldown, not longer authority or a changed inactivity policy.
Readable time cannot be retroactively relabeled preparation. Server authority,
expiration, versions, sequences, idempotency and balances remain enforced.
This is not server proof of a human reading on a malicious client: bounded
authorization and accounting prevent unlimited preparation grants.

## Newly executed qualification

| Check | Result |
|---|---|
| Frontend lifecycle/chapter/content | 93 PASS, including retained regressions, delayed/fast 19 chunks, missing/incompatible assembly inputs, chunk/hash errors, slow/failed fonts, slow image decode, zero layout, visibility, retry, resume, within-chapter navigation |
| Backend preparation/concurrency/policy/admission/security/proxy | 84 PASS, including 16 preparation cases; two existing dependency deprecation warnings |
| Accounting | 16.112s preparation = zero; next 10s readable = debit 10; next 3s then inactive = debit 3; resume preparation zero |
| Concurrent idempotency | 100 identical preparation renewals: one receipt/version transition, 99 duplicates, zero debit |
| Production build | PASS; mandatory hook ran 172 snapshots / 3647 assertions / zero failures, not a separate catalogue audit |
| Python compilation, Node syntax, diff whitespace | PASS |
| Real Chromium 390/768/1440 | PASS, real app layout + actual lease service, synthetic transport and isolated in-memory DB |
| Browser opening | 16,212ms controlled clock at all widths; wall execution approximately 234–277ms with accelerated waits, not production latency |
| Browser accounting/inactivity | Zero preparation/readable-transition debit; subsequent real reading debit; unchanged 120s inactivity pauses and clears protected rendering |
| Browser formatting/layout | Four-space indentation and superscript preserved, foreground/focus valid, no overflow; screenshots after existing entrance animation completes |

Private retained evidence:
`/Users/ronikbasak/.codex/archives/reader-sanitizer-repair-20261009/`
contains `OPENING_REPRODUCTION_SCOPE_BOUNDARY_20261010.md`,
`opening-failing-before.log`, and `preparation-browser/qualification.json` plus
screenshots. The harness blocks non-loopback requests and uses original
synthetic content, not production credentials/content. It is not HTTP/Mongo
transaction integration or production signed-proxy acceptance. Initial macOS
Python 3.9 collection failed; successful qualification used existing Python 3.12.

## Compatibility / release review

Optional `text_phase` is sent only after the server advertises support; audio
omits it. Existing legacy sessions keep old semantics. Old text clients against
new backend have nonbillable starts but retain the slow-opening pause defect
until frontend upgrade. New frontend against old backend uses legacy behavior,
not invented preparation support. Old backend rejects a new phase field if a
deployment reverses during an already-new session.

Deploy backend first, qualify its contract through an existing demonstrably
nonpersisting path, then matching frontend. Mixed backend revisions must not
silently revert prepared sessions to billable starts. Drain/end preparation
sessions before coordinated rollback: old code cannot safely interpret their
phase/bound. No migration/bootstrap is needed. Real Mongo concurrency and the
integrated production signed proxy remain release checks, not completed here.

Historical 13s debit: old text starts enabled billing; renewal settles the prior
interval before applying `active=false`. An inactive renewal around 16.112s
can therefore debit unreadable opening time. Exact 13s arithmetic requires
original timestamps/cutoff/receipt. If all deducted time was preparation, it is
inappropriate under the new policy. No refund is implemented. Separate owner
authorization must bind the exact session/ledger receipt and verified amount.

Next required authorization: review this exact local candidate and authorize
protected PR/CI/merge, backend-first code deployment and one scoped India-origin
authenticated frontend → signed proxy → backend acceptance. No content promotion
or balance adjustment is included. Post-release acceptance: bind both revisions;
verify delayed opening/zero preparation debit/readable debit, formatting,
navigation/resume, inactivity, expiry/revocation, unsigned denial and unchanged
territory/publication/audio boundaries. #525 stays parked until Reader integrity
is verified and canonical ownership is explicitly returned.

PROMOTION_VERIFIED=YES (existing recovery, not repeated)
READER_PRODUCTION_VERIFIED=NO
READER_LANE_COMPLETE=NO
READY_FOR_SCOPED_TECHNICAL_SIGNOFF=NO
PERFORMANCE_WORK=PAUSED
RELEASE_AUTHORIZED=NO
DEPLOYMENT=NOT VERIFIED

Next prompt: Review the exact local nonbillable Reader preparation candidate;
authorize only its protected code release and scoped production acceptance if
the retry bound and mixed-version/rollback plan are accepted.
