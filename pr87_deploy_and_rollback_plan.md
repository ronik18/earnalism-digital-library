# PR87 Deploy And Rollback Plan

## Merge Command When Approved

```bash
cd /private/tmp/earnalism-clean-source-only-merge-20260706T191326Z
git status --short
git add frontend/package.json frontend/package-lock.json frontend/vercel.json frontend/scripts/visual-luxury-smoke.mjs frontend/scripts/vercel-ignore-build.mjs frontend/src/lib/api.js frontend/src/components/ShelfTwoSlideshow.jsx frontend/src/pages/Home.jsx frontend/src/index.css regression/modules/05-url-navigation.test.js regression/modules/12-migration-data-consistency.test.js regression/modules/14-ux-conversion-static.test.js regression/modules/15-reader-content-quality.test.js pr87_blocker_rescue_plan.json vercel_preview_unblock_report.json kshudhita_pipeline_regression_report.json controlled_launch_catalog_regression_report.json pr87_source_scope_audit.json pr87_preview_validation_report.json pr87_merge_readiness_report.md pr87_deploy_and_rollback_plan.md pr87_comment_summary.md repo_cleanup_report.md sprint_go_live_dashboard.md internal/earnalism_intelligence/decision_ledger.jsonl internal/earnalism_intelligence/sprint_learnings.md
git commit -m "fix: unblock PR87 validation gates"
git push origin codex/clean-source-only-merge-20260706T191326Z
```

## Post-Push Preview Checks

- Confirm Vercel no longer reports ignored/canceled build for PR #87.
- Validate preview routes: `/`, `/library`, `/book/dracula`, `/reader/dracula`, `/book/a-ghost-story`, `/reader/a-ghost-story`.
- Confirm no unapproved audiobook controls appear.
- Confirm graphical covers remain visible and not clipped.
- Run Lighthouse on the preview homepage or accept local production-equivalent result only with owner approval.

## Rollback

Revert the blocker rescue commit if it regresses CI or preview:

```bash
git revert <blocker-rescue-commit-sha>
git push origin codex/clean-source-only-merge-20260706T191326Z
```

No production metadata, audio assets, generated release artifacts, or destructive deletions are part of this patch.
