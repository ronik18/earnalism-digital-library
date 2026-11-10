# Release Decision Policy

Before every release run:

1. Identify the business goal.
2. Inspect repo evidence, production evidence, dashboards, and prior decisions.
3. Choose the cheapest safe path.
4. Avoid paid work before content, rights, cover, and provider feasibility pass.
5. Do not retry stale or mismatched audio blindly.
6. Keep reader-only live when audiobook fails.
7. Decommission invalid audio paths rather than looping.
8. Continue to the next candidate when a book reaches a terminal evidence-backed state.
9. Update `decision_ledger.jsonl` and `title_decision_history.json`.

For Bengali catalog work, audiobook failure must not block reader-only publication when reader/source/rights/covers pass.

## New audiobook jobs: automated editorial policy

The owner-directed `automated-editorial-2026-11-11` mode removes routine human
approval waits and numerical human listening/confidence floors for new jobs.
Select it explicitly in the release manifest and backend QA; do not rewrite
historical receipts or apply the preserved owner-YES patches unchanged.
`docs/automated_audiobook_editorial_policy.md` defines the shared evaluation and
promotion contract. Rights, content integrity, storage, protected access,
accounting, title holds and all cumulative operation limits remain effective.
This local source policy is not a deployment or publication receipt.
