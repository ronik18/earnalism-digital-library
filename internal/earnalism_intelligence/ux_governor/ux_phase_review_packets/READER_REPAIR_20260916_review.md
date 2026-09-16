# Reader repair review — 16 September 2026

Status: candidate repair; not merged or deployed. Base: `664a81c17d66ae5053ff898c76db35a6a6ad30d5`. This is a software/UX repair, not title-rights clearance or a manuscript completeness review.

## Evidence and discrepancies

Live browser automation inspected The Necklace guest preview and Frankenstein signed-in preview. The user supplied Alice page-4 403/renew-200 and Frankenstein page-4 200/unavailable screenshots. Private screenshots are supplied separately to the owner; no customer token, account identifier, or browser storage is committed.

| ID | Finding and evidence | Candidate correction |
|---|---|---|
| R01 | Reader flashes unavailable on page transitions; source refetched and cleared content whenever the whole lease object changed. User screenshots show recurring protected-page requests. | Separate loading/error/access states; fetch the selected page only when its page/session identity changes. Healthy heartbeat updates preserve the article. |
| R02 | Global Reading Pass calls escaped user-token recovery due to path classification and double `/api` construction. Source-confirmed; screenshots alone do not prove the cause of every 403. | Classify Reading Pass user requests and refresh a 401 once; retain real 403 restrictions and visible recovery. |
| R03 | HTTP 200 lease responses could be Paused, Exhausted, or Stale but were treated as usable. Source-confirmed. | Require a current Running grant, handle terminal states explicitly, clear expired protected content, serialize renewal/settlement and reuse the exact idempotency key for one bounded transport retry. |
| R04 | Top-right Library is a noninteractive span; live click remains on the reader. | Real keyboard-accessible button, with session settlement before leaving. |
| R05 | Page entries are noninteractive list items, truncated to six; live Page 2 click does nothing. | All manifest pages are selectable; current-page indication, mobile selector, bounded previous/next and end-of-book state. |
| R06 | The same castle image appears above unrelated books; observed live. | Production model does not inherit the Dracula visual fixture or its illustration. |
| R07 | Frankenstein shows fixture year 1897 and verification metadata; wallet time appears as estimated reading time. Observed live. | Use actual manifest metadata; omit unknown fields and unsupported reading estimates. No fixture-derived rights claim. |
| R08 | Paragraph-only extraction drops mixed headings/lists/code and other structure. Source-confirmed. | Preserve safe semantic content in order, including Bengali and line breaks; remove executable markup. Images are constrained; wide tables scroll. No stored source text is changed. |
| R09 | Settings actions were unwired. Source-confirmed. | Working font size, theme, spacing and width preferences; close returns focus to the opener. |
| R10 | Query-only page changes preserve the previous scroll position. Source-confirmed. | A newly ready page focuses and scrolls to its heading; same-page renewals do not move the reader. |
| R11 | Leaving, browser Back, invalid-page history, or slow failed content could leave a session running. Source-confirmed. | Settle sessions on preview/invalid/disabled pages, exit and title change; never renew active reading without a ready page; respect server inactivity settings. |
| R12 | A late request could replace a newer book/page or inherit stale route state. Source-confirmed. | Scope state to title/customer, cancel page/manifest requests, validate exact edition identity and page schema, and close late-issued sessions. |
| R13 | Unbounded I/O could trap loading or settlement; source-confirmed. | Bounded deadlines, aborted stale reads, visible Library escape while loading, explicit reader/page retry. Start/end are not automatically retried after uncertain transport outcomes. |
| R14 | Save/bookmark action used an absent endpoint. Source-confirmed. | Use existing versioned reading-position endpoint and report save success/failure. |
| R15 | Alice Release & Access panel has pale text on cream; owner screenshot. | Restore readable dark-panel contrast and replace internal audio-gate explanations with customer-facing availability copy. |

The console extension-message errors in owner screenshots are not established Earnalism failures. No claim is made that every title, device, backend response, or customer entitlement has been exercised.

## Validation

- Full frontend suite: 68 suites / 393 tests passed.
- Real-router lifecycle coverage includes preview-to-protected navigation, repeated heartbeats, 403 recovery, expired/stale/exhausted access, hidden/idle tabs, failed settlement, browser Back, invalid pages, late responses, wrong manifests and missing page identity.
- Actual local HTTP transport tests prove stalled Reading Pass requests time out, cancellation closes a page request, and a stalled authentication-refresh body cannot block settlement indefinitely.
- Component tests exercise Library/page buttons, preferences, font changes, end bounds, page focus/scroll, and settings focus restoration.
- Production frontend build passed; static SEO inspected 142 snapshots and passed 2,502 assertions. `git diff --check` passed.
- No backend financial logic, access policy, balances, manuscript, title publication, audio assets, or geographic access configuration was changed.

## Remaining release checks

1. Run the existing repository CI against the candidate. Preserve release gates.
2. Visually inspect the candidate on desktop and a real mobile viewport. The cloud browser returned `ERR_BLOCKED_BY_CLIENT` for the isolated local preview; synthetic HTTP checks and DOM tests do not count as screenshot approval.
3. Obtain an explicit customer Reading Pass test budget. Automatic approval review rejected “Use Reading Time to Continue” because it could consume the customer's paid entitlement. No alternate path was used to bypass that restriction.
4. With that authorization, test Alice and Frankenstein across pages 3→4→5, several renewals, Library exit, reopen, and exhaustion/denial recovery as applicable. Record requests/statuses and settlement; do not purchase or change balances.
5. Merge through normal checks and deploy only merged `origin/main`. Verify the deployed version, routes, public previews, protected requests, mobile controls, and no recurring unavailable/refetch cycle. Revert the frontend repair if it introduces regression; a code rollback does not reverse account transactions.

Next owner prompt: “You may use up to two minutes of my Reading Pass for the final Alice and Frankenstein reader checks. Complete the candidate review and required CI, release through merged main, and verify the deployed reader. Do not purchase time, transfer devices, or change balances manually.”
