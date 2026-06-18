# Next 30 Day Automation Plan

## Week 1: Rights And Source Backfill

- Export sanitized production book metadata for rights audit.
- Backfill rights metadata for highest-demand Tier A candidates first.
- Resolve all Tier C and unknown-rights items into block, quarantine, or approved state.
- Add source hashes, content hashes, provenance hashes, and source licenses for approved candidates.

## Week 2: Controlled Candidate Dry-Runs

- Rerun demand scoring after rights/source cleanup.
- Select 3 to 5 Tier A candidates with `READY_FOR_GENERATION`.
- Run ingestion with `--include-text` locally only for approved texts.
- Run edition, visual, audio, and publishing workflows in dry-run mode.
- Review QA, source coverage, and rollback metadata manually.

## Week 3: QA And Preview Operations

- Conduct human editorial review for historical context, SEO copy, landing copy, and social excerpts.
- Perform audiobook listening review for any preview audio candidates.
- Validate Bengali/English reader rendering on desktop and mobile.
- Verify no internal source URLs, rights evidence, or admin metadata leaks into public pages.

## Week 4: Activation Planning

- Prepare a separate activation PR for one low-risk Tier A item only.
- Keep feature flags disabled by default and enable only explicit draft creation if approved.
- Run GO LIVE regression, catalog audit, rights audit, and production canary.
- Document rollback owner, rollback command, and incident owner before any public exposure.

## Success Metrics

- 0 critical rights blockers.
- 0 demo/template URLs returning 200.
- 100/100 regression module scores.
- Public publishing disabled unless explicitly approved.
- At least 3 high-demand Tier A candidates ready for final human review.

