# Post-Production Canary Summary

Overall Status: `FAIL`
Owner Recommendation: `ROLLBACK`
Generated At: `2026-06-20T07:06:02Z`
Run Directory: `output/release-canary/2026-06-20-07-05-42`

This command is local-report only. It does not publish content, enable audiobook, send email or social posts, call paid provider APIs, or mutate production data.

## Owner Status

- Failed command: `npm run launch:backend-catalog-truth-canary`
- Route canary: `PASS`
- Backend catalog truth: `FAIL`
- Dracula live: `FAIL`
- Payment smoke: `PASS`
- SEO: `PASS`
- Audio: `PASS`
- Catalog truth: `PASS`
- Daily growth audit: `PASS`
- Observability: `PASS`
- Regression: `PASS`
- Frontend build: `PASS`

## Command Results

| Step | Status | Critical | Return Code | Log |
| --- | --- | --- | --- | --- |
| Route canary | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/01-route_canary.log` |
| Backend catalog truth | `FAIL` | True | 1 | `output/release-canary/2026-06-20-07-05-42/02-backend_catalog_truth.log` |
| Production parity | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/03-production_parity.log` |
| Controlled publication precheck | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/04-controlled_publication.log` |
| Payment smoke | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/05-payment_smoke.log` |
| SEO audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-07-05-42/06-seo.log` |
| Audio audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-07-05-42/07-audio.log` |
| Owner catalog truth audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-07-05-42/08-catalog_truth.log` |
| Owner daily growth audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-07-05-42/09-daily_growth_audit.log` |
| Observability audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-07-05-42/10-observability.log` |
| Focused regression | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/11-regression.log` |
| Frontend build | `PASS` | True | 0 | `output/release-canary/2026-06-20-07-05-42/12-frontend_build.log` |

## Safety Confirmation

- Public publishing: disabled
- Audiobook enablement: disabled
- Email/social sending: disabled
- Paid provider calls: disabled
- Production data mutation: disabled
