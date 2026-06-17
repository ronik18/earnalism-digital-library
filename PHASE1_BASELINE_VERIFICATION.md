# Phase 1A/1B Baseline Verification

## Phase 1A Public Cleanup Baseline

| Requirement | Verification |
| --- | --- |
| Demo/template/fashion/ecommerce URLs do not return `200` | `frontend/vercel.json` routes known removed families to `frontend/api/removed-content.js`; regression validates known retired paths return `410` and unknown retired paths return `404` |
| Removed demo URLs excluded from sitemap | `frontend/scripts/generate-seo-assets.mjs` filters blocked public path prefixes and terms; regression validates sitemap excludes blocked demo/ecommerce terms |
| Removed demo URLs crawlable during deindexing | `frontend/public/robots.txt` does not disallow `/product/`, `/products/`, `/product-category/`, `/shop/`, `/fashion/`, `/clothing/`, `/apparel/`, or retired tags; regression validates these are not disallowed |
| `410` + noindex strategy | `frontend/api/removed-content.js` sets `X-Robots-Tag: noindex, nofollow, noarchive` and returns `410` for blocked terms |
| No raw path/query reflection | Regression validates removed-content response body does not reflect raw path/query input |
| No `/shop/:slug -> /book/:slug` route | `frontend/src/App.js` only defines `/book/:slug` for book detail pages and does not define a shop slug redirect |

## Phase 1B Catalog Governance Audit Baseline

| Requirement | Verification |
| --- | --- |
| Audit script readable and executable | `scripts/audit-public-content.mjs` starts with standalone `#!/usr/bin/env node`, has 1,299 physical lines, and passes `node --check` |
| Fixture mode works | `node scripts/audit-public-content.mjs --fixture regression/fixtures/catalog-audit --output-dir /tmp/earnalism-catalog-audit-check` passed |
| Live dry-run audit works | `npm run catalog:audit` passed and audited 251 items |
| Degraded source reporting exists | `summary.source_statuses`, `summary.degraded`, and `summary.degraded_reasons` are present and regression-tested |
| Unknown/no rights metadata quarantines sensitive content | Regression validates unknown book, reader, audio asset, and book asset rights metadata produce `QUARANTINE` |
| CSV includes source/path fields | Regression validates `path`, `source_sets`, `related_slug`, `language`, `asset_health`, `asset_files`, `degraded`, and `source_warnings` headers |
| Dry-run only | Catalog audit outputs reports and recommendations only; regression validates no content is mutated or deleted |

## Syntax And Build Verification

| Check | Result |
| --- | --- |
| Backend Python syntax | `python3 -m py_compile backend/server.py` passed |
| Audit script syntax | `node --check scripts/audit-public-content.mjs` passed |
| Governance regression syntax | `node --check regression/modules/13-public-content-governance.test.js` passed |
| Governance regression suite | `npm run regression -- modules/13-public-content-governance.test.js` passed, 15/15 tests |
| Frontend production build | `npm --prefix frontend run build` passed |

## Files Confirmed

- `frontend/api/removed-content.js`
- `frontend/vercel.json`
- `frontend/public/robots.txt`
- `frontend/public/sitemap.xml`
- `frontend/scripts/generate-seo-assets.mjs`
- `frontend/src/App.js`
- `regression/modules/13-public-content-governance.test.js`
- `scripts/audit-public-content.mjs`

## Baseline Conclusion

The corrective branch restores the approved Phase 1A/1B governance baseline and removes PR #14's unrelated broad changes. No broad PR #14 runtime change remains in this corrective branch except the explicit revert mechanics and documentation reports.

