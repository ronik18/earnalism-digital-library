# Reader manifest cache canary follow-up — 16 September 2026

Status: narrow validation-tool repair in progress; fresh corrected canary evidence pending. PR #401 merged as `2773053f2672e6a3528d306ba1c66e481225b322`, and Railway provider evidence proves deployment of that commit. Earlier local-only records remain historical checkpoints.

The deployed canary passed 11 of 13 checks. Both reader-manifest probes returned HTTP 200 with `private, no-store` and no ETag, but the parsed Vary value showed only `accept-encoding`. Source inspection confirmed two observation defects in `scripts/railway_deployment_status_canary.py`: converting `response.headers.items()` to a dict discards duplicate same-name fields, and first-match case-insensitive lookup misses additional differently cased fields. The report therefore cannot establish that the origin or edge dropped Authorization/Cookie variation.

The scoped correction preserves repeated raw header fields and combines case-insensitive header values before evaluating the existing strict cache checks. Focused tests must cover duplicate and mixed-case fields plus missing required variation. No server, frontend, workflow, financial or content behavior changes, and no gate relaxation, are part of this follow-up. No customer data is recorded here.

Acceptance remains pending until focused tests and the corrected raw-header-preserving production canary pass. A parser fix alone is not evidence that deployed headers are correct; if required Vary values are still missing, the original gate must continue to fail and origin/edge behavior must be investigated.

Next command: `python -m pytest -q backend/tests/test_railway_deployment_status_canary.py`; then review and release the focused candidate and rerun the existing production canary with deployment provenance.
