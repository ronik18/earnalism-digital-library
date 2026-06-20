# Post-Production Canary Runbook

## Purpose

`npm run release:post-production-canary` runs the safe post-deploy owner canary sequence for Earnalism after a production deployment. It produces one summary that tells the operator whether Dracula should stay live, whether fixes are needed, or whether rollback should be considered.

## Command

```bash
npm run release:post-production-canary
```

## Safety Rules

- No public publishing is performed.
- Audiobook remains disabled.
- No email or social post is sent.
- No paid provider API is called by this orchestrator.
- No production data is mutated.
- Timestamped command logs are written under `output/release-canary/YYYY-MM-DD-HH-mm-ss/`.
- The owner summary is copied to `output/release-canary/latest/summary.json` and `output/release-canary/latest/summary.md`.

## Command Order

1. `npm run launch:post-deploy-route-canary`
2. `npm run launch:backend-catalog-truth-canary`
3. `npm run launch:production-parity`
4. `npm run controlled-publication:precheck`
5. `npm run launch:payment-smoke`
6. `npm run launch:seo-audit`
7. `npm run launch:audio-audit`
8. `npm run owner:catalog-truth-audit`
9. `npm run owner:daily-growth-audit`
10. `npm run observability:audit`
11. `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
12. `npm --prefix frontend run build`

## Critical vs Warning-Tolerant Checks

Critical checks fail the command if they return nonzero:

- route canary
- backend catalog truth canary
- production parity
- controlled publication precheck
- payment smoke
- focused regression
- frontend build

Warning-tolerant checks continue the run and mark overall status `WARN` if they warn or return nonzero:

- SEO audit
- audio audit
- owner catalog truth audit
- owner daily growth audit
- observability audit

## Owner Recommendation

- `KEEP_DRACULA_LIVE`: every command passed without warnings.
- `HOLD_FOR_FIXES`: a warning-tolerant command warned/failed, or a critical non-rollback gate failed.
- `ROLLBACK`: route canary, backend catalog truth, production parity, or frontend build failed after deploy.

## Operator Response

If status is `PASS`, keep Dracula live.

If status is `WARN`, keep Dracula live only if the warnings are understood and non-publication-related. Open a focused fix PR for the warning source.

If status is `FAIL`, do not publish anything else. Follow the owner recommendation in `output/release-canary/latest/summary.md`.
