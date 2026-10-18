# Reader preparation expiry — local qualification only

Base: d79acb1952161cd56395e9bb4d7c1001ceaa69bb. Owner authorized preservation,
canonical restoration and local fix/qualification only. #525 stays parked.

Captured production failure: Chapter6 requires19 chunks75–93; only75–83
completed before the20s preparation anchor expired. Session ended with zero
debit and balance3255 unchanged. Do not repeat a production session here.

Correction: separate the server's fixed text-preparation budget (default60s,
integer1–120) from unchanged20s renewable leases. Three existing anchor-creation
paths use this budget: initial start, cooled-down retry, and earned preparation
after positive settled reading. No new API/client field or environment setting.
Existing retained anchors are never extended by upgrade, renew or restart.
The existing120s cooldown, positive-debit rule,10s heartbeat, lease grace,
inactivity/accounting and all access checks remain unchanged. Preparation is
still nonbillable; readable time is never backdated. Longer preparation requires
continuing valid short leases. This addresses the observed20s bound, not every
possible network delay; delivery beyond60s still fails closed.

Newly executed: two regressions FAIL on original service; focused preparation,
service concurrency and policy tests69PASS on corrected service. Includes45s
opening then normal10s billing,60s timeout without debit, no restart extension,
old20s-anchor compatibility, expired short-lease denial, identity/publication
denial, revocation, malformed phase/config, idempotency, fixed preview and audio
policy. Python compilation and git diff whitespace checks PASS.

## Additional isolated qualification (2026-10-18)

Real Mongo:29PASS (12preparation,17admission), one Motor event-loop deprecation
warning. Actual transactions/indexes on an owned loopback replica set at27029,
unique UUID namespaces dropped by fixtures and verified absent afterward.
New45s preparation/readability/10s billing,61s expiry and45s revocation cases
preserve zero preparation debit and durable authority. No production DB used.

Real Chromium:6PASS at390/768/1440, delayed45s and expired61s cases at each width.
Actual local frontend build/pagination plus real Python lease service; isolated
in-memory DB and synthetic API transport. All19chunks delivered before readable
transition at45100ms controlled time; zero preparation debit. Indentation and
superscript preserved; no horizontal overflow. Subsequent readable usage debited
80synthetic seconds before genuine inactivity paused and removed protected text.
Expired case:19-chunk window deliberately incomplete, no readable text, session
expired with preparation_timeout, zero debit and unchanged600fixture balance.
No production API/Reader requests. Controlled clocks are not network benchmarks.

Build PASS; mandatory hook172snapshots/3647assertions/zero failures. Generated
sitemap date-only churn reverted to keep scope. No application frontend source
changed. Initial npm ci without repository-required --legacy-peer-deps failed;
correct repository install succeeded without lockfile/package edits. Python
dependencies restored privately; no product change made for missing local tools.

Evidence: private archive browser-delayed/qualification.json and screenshots,
browser-expiry/qualification.json. Local test suite is not production signed-
proxy, native zoom or actual India Reader acceptance. Historical production
failure remains open until separately authorized release/acceptance. No commit,
push, deployment, production session, recovery or administrative balance change.

Canonical survivors and old Git metadata copied and verified with rsync dry
checksum comparison; complete old branch history bundle verified before owner-
authorized reset to current origin/main. Private recovery location:
/Users/ronikbasak/.codex/archives/reader-preparation-expiry-20261018-Qs6E3u
Primary repository dirty work untouched; only canonical branch realigned.

READER_PRODUCTION_VERIFIED=NO
READER_LANE_COMPLETE=NO
PERFORMANCE_WORK=PAUSED
DEPLOYMENT=NOT_PERFORMED

Next: focused review and exact-candidate protected CI/release authorization.
No deployment or production acceptance authorized by this local qualification.
