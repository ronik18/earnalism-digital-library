# Phase 15 Raw Verification

## Scope

This verification covers the Kshudhita Pashan Bengali Gothic pipeline hardening for PR #34. It confirms the candidate remains pipeline-only, Dracula remains the only live controlled reading candidate, and no audio, publishing, payment, provider, or production mutation was performed.

## Raw line-count verification

```text
421 backend/tests/test_dracula_candidate_scripts.py
1023 scripts/prepare_bengali_candidate.py
1205 scripts/prepare_dracula_candidate.py
429 scripts/approved_to_publish_builder.py
169 frontend/src/lib/controlledLaunch.js
99 frontend/src/components/BookCard.jsx
459 frontend/src/pages/Home.jsx
272 frontend/src/pages/Library.jsx
119 frontend/src/lib/funnelAnalytics.js
150 regression/modules/14-ux-conversion-static.test.js
2466 scripts/launch_readiness_audit.py
24 KSHUDHITA_PASHAN_SOURCE_RIGHTS_REPORT.md
21 KSHUDHITA_PASHAN_RIGHTS_DECISION.md
13 KSHUDHITA_PASHAN_ONBOARDING_REPORT.md
17 KSHUDHITA_PASHAN_AUDIO_PREVIEW_PLAN.md
10 PHASE15_BENGALI_GOTHIC_AUDIO_READINESS_REPORT.md
11 BENGALI_GOTHIC_INTEREST_DASHBOARD.md
175 output/publication_candidates/kshudhita-pashan/source_evidence.json
53 output/publication_candidates/kshudhita-pashan/rights_evidence.json
606 output/publication_candidates/kshudhita-pashan/audio_preview_plan.json
32 data/publication_candidates/kshudhita-pashan.source.json
77 PHASE15_RAW_VERIFICATION.md
7851 total
```

## Validation commands

```text
python3 scripts/check-hidden-unicode.py backend/tests/test_dracula_candidate_scripts.py scripts/prepare_bengali_candidate.py scripts/prepare_dracula_candidate.py scripts/approved_to_publish_builder.py frontend/src/lib/controlledLaunch.js frontend/src/components/BookCard.jsx frontend/src/pages/Home.jsx frontend/src/pages/Library.jsx frontend/src/lib/funnelAnalytics.js regression/modules/14-ux-conversion-static.test.js scripts/launch_readiness_audit.py KSHUDHITA_PASHAN_SOURCE_RIGHTS_REPORT.md KSHUDHITA_PASHAN_RIGHTS_DECISION.md KSHUDHITA_PASHAN_ONBOARDING_REPORT.md KSHUDHITA_PASHAN_AUDIO_PREVIEW_PLAN.md PHASE15_BENGALI_GOTHIC_AUDIO_READINESS_REPORT.md BENGALI_GOTHIC_INTEREST_DASHBOARD.md PHASE15_RAW_VERIFICATION.md output/publication_candidates/kshudhita-pashan/source_evidence.json output/publication_candidates/kshudhita-pashan/rights_evidence.json output/publication_candidates/kshudhita-pashan/audio_preview_plan.json data/publication_candidates/kshudhita-pashan.source.json
python3 -m py_compile scripts/prepare_bengali_candidate.py scripts/prepare_dracula_candidate.py scripts/approved_to_publish_builder.py backend/tests/test_dracula_candidate_scripts.py scripts/launch_readiness_audit.py
PYTHONPATH=. pytest backend/tests/test_dracula_candidate_scripts.py
npm run regression -- modules/14-ux-conversion-static.test.js
npm run regression:ci
npm run controlled-publication:precheck
npm run launch:payment-smoke
npm run launch:seo-audit
npm run launch:post-deploy-route-canary
npm run launch:production-parity
npm run launch:readiness
npm --prefix frontend run build
```

## Results

- Hidden Unicode and line-ending scan passed for the scanned files.
- Python compile passed for the changed candidate and launch audit scripts.
- Candidate script tests passed: 15 passed.
- UX conversion static regression passed: 10 passed.
- Regression CI passed: 12 suites passed, 2 skipped by design, 57 tests passed.
- Controlled publication precheck passed.
- Payment smoke passed in test mode. No live payment was run.
- Production route canary passed.
- Production parity passed.
- Frontend production build passed.
- SEO audit returned `BLOCKED_FOR_BOOK_SEO` because CRA book detail metadata is still client-rendered and needs prerender/SSR/static snapshots for durable book SEO. This is an existing launch-hardening blocker and not caused by the Kshudhita pipeline candidate.
- Full launch readiness returned `HOLD_FOR_FIXES` only because of the known book-SEO blocker. UX, payment, analytics, security, production parity, performance, and controlled routing checks passed or passed with documented audio warnings.

## Safety confirmation

- Kshudhita Pashan remains pipeline-only.
- No Start Reading, Read Preview, Listen Now, or Full Audiobook CTA is exposed for Kshudhita Pashan.
- Audio preview remains planning-only: `READY_FOR_AUDIO_PREVIEW_PLANNING`.
- Actual audio remains blocked until provider and QA pass: `AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA`.
- Dracula remains the only live controlled core reading candidate.
- No Tier B or Tier C item was published.
- No production data was mutated.
- No live payment provider call was made.
- No TTS, STT, LLM, OCR, image, email, social, or paid provider API was called.
