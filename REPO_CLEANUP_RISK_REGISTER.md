# Repo Cleanup Risk Register

| Risk | Status | Mitigation |
| --- | --- | --- |
| Accidentally removing launch/legal/payment/audio evidence | Controlled | Evidence/history files classified KEEP_EVIDENCE_OR_HISTORY and not moved. |
| Breaking regression suite by moving duplicate-looking test files | Controlled | Only files with live counterparts, zero references, and no package-script use were quarantined; active counterpart paths remain. |
| Public audio leak | Controlled | No public assets were moved into `frontend/public` or `frontend/build`; audio scan remains required. |
| SEO snapshot/build breakage | Controlled | Static snapshot files are kept; validation includes SEO audit and frontend build. |
| Admin/launch monitor exposure | Controlled | No admin auth code was modified. |
| Payment behavior change | Controlled | No payment flow files were modified. |
| Ambiguous assets accidentally quarantined | Controlled | All REVIEW_REQUIRED files were left untouched. |
