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
