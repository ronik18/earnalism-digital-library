Selfish Giant route transition proposal

Apply only `selfish-routing-and-held-control.patch`, SHA256 `42f66f5bc490383d4540910c6585eeed8388729d2c207cca74dd89a5b68af1ad`, after the root serialized controller has accepted and integrated the exact Selfish Giant package. `proposal-manifest.json` binds all nine base/proposed files. Context copies under `proposed/` support isolated verification and are not additional requested edits.

The patch removes the three obsolete Selfish Giant `UnavailableTitle` route overrides and the unused lazy binding. It removes the title from the guarded current unavailable-list helper, allowing existing Book Detail, Reader and disabled Listener routes and existing snapshot rewrite destinations to serve the release. No deployment configuration changes are proposed. Existing route-action crawler entries already cover the six Selfish Giant URLs, so that file does not require another edit.

Current-release canary assertions become Book/Reader/disabled Listener, require exact Selfish identity and one chapter, reject stale unavailable markup, raw/media audio, wrong canonical IDs and anonymous paid-access claims. The production held-404 contracts for yugalanguriya remain unchanged. The local cross-browser negative fixture becomes bn-060 with an explicit 404 catalogue response, expects ordinary Book Detail's not-found state, and rejects content/media controls. It is not a new production 200 route or activation claim.

Historical unavailable semantic and snapshot-tamper tests remain strict through explicitly installed local held fixtures. Original historical unavailable records and generated observations are not edited; the root should archive the original App/unavailable-list/canary/test files under the existing campaign ledger before applying this transition.

No source, chapter, sync, audio policy, entitlement policy, paid-commerce logic, registry, allowlist or production record is changed by this patch. Selfish's release allowlists, exact package, public static metadata projection and bootstrap are a separate serialized root operation.

Isolated validation completed:

- `git apply --check` against the current canonical checkout: PASS.
- Babel parser over every changed JS/JSX/MJS file: PASS.
- Three focused frontend suites: 15 tests PASS.
- Canary semantic units plus three real-generator historical held/tamper tests: 26 tests PASS.
- Empty current unavailable-list releases Selfish without the historical shadow: PASS.

Required commands after root integration and projection refresh:

```bash
git apply --check /workspace/scratch/181ef0a25f05/selfish-routing-proposal-20261003/selfish-routing-and-held-control.patch
git apply /workspace/scratch/181ef0a25f05/selfish-routing-proposal-20261003/selfish-routing-and-held-control.patch
python -m unittest scripts.test_post_deploy_static_seo_canary
```

From `frontend/`:

```bash
CI=true npm test -- --watchAll=false --runInBand --runTestsByPath src/bookDetailDirectRoute.test.js src/readerDirectRoute.test.js src/pages/UnavailableTitle.test.jsx
node scripts/generate-static-seo-snapshots.mjs
node scripts/verify-static-seo-snapshots.mjs
```

Also run the required exact-head CI/static regression and configured cross-browser job normally. The full first-match rewrite/snapshot integration test awaits actual root-controlled Selfish package/allowlist/public-projection integration; the proposal did not fabricate a locally approved public projection merely to pass that test. Normal protected merge, deployment and truthful canary/readback remain required.
