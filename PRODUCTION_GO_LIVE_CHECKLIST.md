# Production GO-LIVE Checklist

## Required Before Any Public Automation Publishing

- [x] Full regression gate passes.
- [x] Frontend production build passes.
- [x] Catalog audit runs and is not degraded.
- [x] Sitemap excludes demo/template/ecommerce/fashion URLs.
- [x] Robots strategy allows removed URLs to be crawled for 410/noindex.
- [x] Removed demo URLs return 410 or 404, never 200.
- [x] Rights audit command runs from repo root.
- [x] Tier C books cannot publish.
- [x] Kill switch blocks automation actions.
- [x] Rollback metadata exists in dry-run publishing workflow.
- [x] Dry-run publishing produces non-public draft metadata only.
- [x] Audio pipeline stays metadata-only unless a later phase explicitly enables providers.
- [x] Daily growth loop keeps `public_publishing_enabled=false`.

## Manual Operator Checks

- [ ] Confirm production Railway backend env is current.
- [ ] Confirm Vercel project is the live Earnalism frontend project.
- [ ] Confirm `REGRESSION_ALLOW_PRODUCTION_TARGET=true` is set only for intentional non-PR GO LIVE workflows.
- [ ] Confirm all provider keys remain absent from local reports and docs.
- [ ] Confirm source/rights metadata export exists before running a live rights audit beyond fixtures.
- [ ] Confirm no feature flag enables public publishing by default.

## Release Commands

```bash
PYTHONPATH=. pytest backend/tests/test_rights_engine.py backend/tests/test_demand_scoring.py backend/tests/test_source_ingestion.py backend/tests/test_edition_generator.py backend/tests/test_visual_design_engine.py backend/tests/test_audiobook_voice_pipeline.py backend/tests/test_publishing_workflow.py backend/tests/test_daily_growth_loop.py backend/tests/test_automation_observability.py backend/tests/test_first_batch_dry_run.py
npm run regression:ci
RUN_E2E=1 RUN_LOAD=0 bash scripts/run_regression_suite.sh
npm run catalog:audit
python3 scripts/rights_audit.py --input regression/fixtures/catalog-audit/books.json --output-dir output/rights_audit
npm run demand:score
npm run publish:workflow
npm run audio:voice
npm run first-batch:dry-run
npm run growth:daily
npm run observability:audit
npm run regression -- modules/13-public-content-governance.test.js
npm --prefix frontend run build
```

## Post-Merge Verification

- [ ] Confirm GitHub PR checks pass.
- [ ] Confirm Vercel preview succeeds.
- [ ] Confirm no deploy job runs on PR unless intentionally configured.
- [ ] Confirm generated reports remain local artifacts and are not exposed publicly.

## Rollback

1. Revert the Phase 12 PR.
2. Re-run `npm run regression:ci`.
3. Re-run `npm run catalog:audit`.
4. Confirm `frontend/public/sitemap.xml` and `frontend/public/robots.txt` still match governance policy.
5. Keep public publishing feature flags disabled.

