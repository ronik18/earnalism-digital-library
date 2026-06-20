# Post-Production Canary Summary

Overall Status: `PASS`
Owner Recommendation: `KEEP_DRACULA_LIVE`
Generated At: `2026-06-20T20:30:24Z`
Run Directory: `output/release-canary/2026-06-20-20-29-20`

This command is local-report only. It does not publish content, enable audiobook, send email or social posts, call paid provider APIs, or mutate production data.

## Owner Status

- Failed command: `none`
- Route canary: `PASS`
- Backend catalog truth: `PASS`
- Dracula live: `PASS`
- Payment smoke: `PASS`
- SEO: `PASS`
- Production social preview: `PASS`
- Audio: `PASS`
- Catalog truth: `PASS`
- Daily growth audit: `PASS`
- Observability: `PASS`
- Regression: `PASS`
- Frontend build: `PASS`
- Real-user UX go/no-go: `PASS`

## Command Results

| Step | Status | Critical | Return Code | Log |
| --- | --- | --- | --- | --- |
| Route canary | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/01-route_canary.log` |
| Backend catalog truth | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/02-backend_catalog_truth.log` |
| Production parity | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/03-production_parity.log` |
| Controlled publication precheck | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/04-controlled_publication.log` |
| Payment smoke | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/05-payment_smoke.log` |
| SEO audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/06-seo.log` |
| Production social preview | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/07-social_preview_prod.log` |
| Audio audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/08-audio.log` |
| Owner catalog truth audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/09-catalog_truth.log` |
| Owner daily growth audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/10-daily_growth_audit.log` |
| Observability audit | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/11-observability.log` |
| Focused regression | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/12-regression.log` |
| Frontend build | `PASS` | True | 0 | `output/release-canary/2026-06-20-20-29-20/13-frontend_build.log` |
| Real-user UX go/no-go | `PASS` | False | 0 | `output/release-canary/2026-06-20-20-29-20/14-ux_go_no_go.log` |

## Safety Confirmation

- Public publishing: disabled
- Audiobook enablement: disabled
- Email/social sending: disabled
- Paid provider calls: disabled
- Production data mutation: disabled
