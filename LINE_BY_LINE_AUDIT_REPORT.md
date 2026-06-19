# Line-By-Line Audit Report

Generated: `2026-06-19T05:49:53Z`

This deterministic audit scanned tracked text source/config/doc files and skipped build artifacts, generated output, virtual environments, and binary/media assets. It does not publish, deploy, call providers, or mutate production data.

| Metric | Value |
| --- | --- |
| Tracked text files scanned | 347 |
| Source/config/doc lines scanned | 131730 |
| Findings | 145 |

## Category Counts

| Category | Count |
| --- | --- |
| deployment_script | 9 |
| external_or_mutating_call_site | 20 |
| hidden_unicode | 7 |
| invalid_shebang | 6 |
| provider_guard | 20 |
| raw_html_injection | 17 |
| secret_like_string | 21 |
| unsafe_or_stale_launch_language | 38 |
| unsafe_redirect | 7 |

## Highest Priority Findings

| Severity | Category | File | Line | Finding | Recommendation |
| --- | --- | --- | --- | --- | --- |
| HIGH | provider_guard | AUDIOBOOK_VOICE_PIPELINE.md | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | AUDIO_INTEGRATION_GUIDE.md | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
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
| HIGH | provider_guard | README_audio.md | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | backend/audiobook_voice_pipeline.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | secret_like_string | backend/server.py | 441 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | backend/server.py | 454 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | provider_guard | backend/tests/test_audiobook_voice_pipeline.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | backend/tests/test_b2_audiobook_routing.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | deploy_audio_to_cdn.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | deploy_english_audio.sh | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | hidden_unicode | frontend/public/audio/ben/book-0deb35c750_timestamps.json | 5703 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/book-d19e96859f_timestamps.json | 4003 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/book-d19e96859f_timestamps.json | 4573 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/book-d19e96859f_timestamps.json | 4648 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/ginni_timestamps.json | 4003 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/ginni_timestamps.json | 4573 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | hidden_unicode | frontend/public/audio/ben/ginni_timestamps.json | 4648 | Hidden Unicode control U+200C detected. | Remove hidden Unicode. |
| HIGH | secret_like_string | frontend/src/components/Admin/ChapterUpload.jsx | 30 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/components/Admin/CoverUpload.jsx | 42 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/components/Admin/JournalEditor.jsx | 36 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/components/Admin/JournalEditor.jsx | 64 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/components/Admin/JournalEditor.jsx | 90 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | provider_guard | frontend/src/components/AudioPlayer 2.jsx | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | frontend/src/components/AudioPlayer.jsx | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | secret_like_string | frontend/src/components/SecureReader.jsx | 28 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/components/SecureReader.jsx | 34 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | raw_html_injection | frontend/src/components/SecureReader.jsx | 178 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | secret_like_string | frontend/src/context/AuthContext.jsx | 12 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/context/AuthContext.jsx | 18 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/lib/api.js | 219 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | secret_like_string | frontend/src/lib/api.js | 227 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | raw_html_injection | frontend/src/pages/Admin.jsx | 327 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Admin.jsx | 334 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Admin.jsx | 1225 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | secret_like_string | frontend/src/pages/Reader.jsx | 70 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 172 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 189 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 241 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 279 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 293 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 306 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 343 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 357 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 394 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 436 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 731 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | raw_html_injection | frontend/src/pages/Reader.jsx | 757 | Raw HTML rendering detected. | Verify sanitizer and trusted source boundaries. |
| HIGH | secret_like_string | frontend/src/pages/Reader.jsx | 797 | Secret-like literal detected. | Move secrets to environment variables or confirm this is a documented placeholder. |
| HIGH | provider_guard | generate_audio 2.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |
| HIGH | provider_guard | generate_audio 3.py | 1 | Audio/provider script references remote providers without all production audio guard flags. | Require EARNALISM_ALLOW_AUDIO_UPLOAD, EARNALISM_ALLOW_PROVIDER_CALLS, and EARNALISM_CONFIRM_PRODUCTION_AUDIO. |

Full CSV: `LINE_BY_LINE_RISK_REGISTER.csv`
