# Duplicate Or Stale Docs Report

Phase and launch reports are evidence snapshots, not publication approval. Any stale GO language must stay subordinate to `FINAL_GO_NO_GO_DECISION.md` and `controlled-publication:precheck`.

| Severity | Category | File | Line | Finding | Recommendation |
| --- | --- | --- | --- | --- | --- |
| HIGH | unsafe_redirect | CLEANUP_REPORT.md | 29 | Potential legacy /shop to /library redirect. | Removed demo routes must go to removed-content, not the SPA shell or library. |
| HIGH | unsafe_redirect | CLEANUP_REPORT.md | 51 | Potential legacy /shop to /library redirect. | Removed demo routes must go to removed-content, not the SPA shell or library. |
| HIGH | unsafe_redirect | LAUNCH_FIXES_REPORT.md | 5 | Potential legacy /shop to /library redirect. | Removed demo routes must go to removed-content, not the SPA shell or library. |
| HIGH | invalid_shebang | PHASE1_BASELINE_VERIFICATION.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | invalid_shebang | PHASE4_VALIDATION_REPORT.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | invalid_shebang | PHASE5_VALIDATION_REPORT.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | invalid_shebang | PHASE6_VALIDATION_REPORT.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | invalid_shebang | PHASE7_VALIDATION_REPORT.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | invalid_shebang | PHASE8_VALIDATION_REPORT.md | 1 | Shebang appears after line 1. | Move shebang to the first physical line. |
| HIGH | provider_guard | README_audio 2.md | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | frontend/src/components/AudioPlayer 2.jsx | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | generate_audio 2.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | scripts/open_source_audiobook_onboarding 2.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | secret_like_string | scripts/prepare_technical_book 2.py | 531 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | scripts/prepare_technical_book 2.py | 532 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | provider_guard | scripts/run_audiobook_backfill 2.sh | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| MEDIUM | unsafe_or_stale_launch_language | APPROVED_TO_PUBLISH.template.md | 3 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | CONTROLLED_PUBLICATION_PRECHECK.md | 11 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | DEPLOYMENT.md | 3 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | DEPLOYMENT.md | 145 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | DEPLOYMENT_FLOW_SAFETY_REPORT.md | 35 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | FINAL_ACTION_PLAN.md | 9 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | FINAL_ACTION_PLAN.md | 10 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | FINAL_GO_NO_GO_DECISION.md | 23 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | FIRST_BATCH_REAL_SOURCE_MATRIX.md | 5 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | PHASE13C_VALIDATION_REPORT.md | 42 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | PHASE13D_VALIDATION_REPORT.md | 12 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | PHASE13D_VALIDATION_REPORT.md | 34 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | PHASE13D_VALIDATION_REPORT.md | 40 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | POST_DEPLOY_VERIFICATION.md | 27 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | README_audio.md | 172 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | backend/tests/test_launch_readiness_audit.py | 227 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | deployment_script | scripts/commit_push_deploy 2.sh | 328 | Deployment command detected. | Ensure it is documented, main-branch gated, and not part of tests. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/controlled_publication_precheck.py | 21 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/controlled_publication_precheck.py | 112 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/controlled_publication_precheck.py | 117 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1267 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1397 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1472 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1474 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1772 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 1812 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2080 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2103 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2126 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2134 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2191 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2209 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2253 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2306 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2343 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/launch_readiness_audit.py | 2370 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/line_by_line_launch_audit.py | 191 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/post_deploy_route_canary.py | 131 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
| MEDIUM | unsafe_or_stale_launch_language | scripts/post_deploy_route_canary.py | 170 | Launch/GO language requires review. | Keep launch status HOLD unless evidence satisfies the publication precheck. |
