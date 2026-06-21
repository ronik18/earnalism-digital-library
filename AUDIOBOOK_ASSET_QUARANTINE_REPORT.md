# Audiobook Asset Quarantine Report

Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

Public reachability result: `PASS`

No audiobook or generated/demo audio asset is intentionally public. This report covers the local hardening that moved previously direct-reachable audio assets out of `frontend/public` and tightened release gates so the same issue cannot return quietly.

## Audited Locations

| Location | Result |
| --- | --- |
| `frontend/public/audio` | Removed from public static surface. |
| `frontend/public` | No audio-like files remain. |
| `frontend/build/audio` | Stale generated build copy removed locally; build no longer recreates it. |
| `frontend/build` | No audio-like files remain after build. |
| Backend public projections | Existing catalog truth strips `audio_url`, `audiobook_url`, `audiobook_assets`, and audiobook internals from public projections. |
| Backend audiobook routes | Existing Dracula and Kshudhita audiobook routes remain 404 while audio is disabled. |
| Cloudinary/B2 URL fixtures | Safe test fixtures only; not public metadata. |
| Seed/catalog fixtures | Regression fixtures contain mock audio paths only for audit behavior; not deployed public assets. |
| SEO snapshots | No `AudioObject`, public audio URL, or Listen Now claim. |
| Sitemap/social metadata | No public audiobook URL, audio file URL, or AudioObject metadata. |
| Tests and reports | References remain as guardrails, historical reports, or fixture mocks. |

## Assets Found Before Quarantine

The following tracked files were previously under `frontend/public/audio` and therefore direct-reachable in a static deploy:

| Group | Files |
| --- | --- |
| `ben/book-0deb35c750` | `.mp3`, `_chapters.json`, `_highlight.vtt`, `_meta.json`, `_timestamps.json` |
| `ben/book-63afd5e9be` | `.mp3`, `_chapters.json`, `_highlight.vtt`, `_meta.json`, `_timestamps.json` |
| `ben/book-d19e96859f` | `.mp3`, `_chapters.json`, `_highlight.vtt`, `_meta.json`, `_timestamps.json` |
| `ben/ginni` | `.mp3`, `_chapters.json`, `_highlight.vtt`, `_meta.json`, `_timestamps.json` |
| `en/bharat-at-the-crossroads` | `.mp3`, `_chapters.json`, `_highlight.vtt`, `_meta.json`, `_timestamps.json` |

Total quarantined tracked files: `25`.

Generated stale build copies were also found under `frontend/build/audio` and removed from the ignored build output. These were generated copies, not source evidence.

## Assets Quarantined

All tracked files above were moved to:

```text
internal/audio_quarantine/frontend-public-audio/
```

Classification after move:

| Asset Class | Classification | Public Reachable |
| --- | --- | --- |
| Quarantined MP3 files | internal fixture/review only | no |
| Quarantined timestamp JSON | internal fixture/review only | no |
| Quarantined VTT files | internal fixture/review only | no |
| Quarantined metadata/chapter JSON | internal fixture/review only | no |
| Regression fixture audio paths | safe mock | no |
| Backend test Cloudinary/B2 URLs | safe mock/test only | no |
| Historical documentation references | review/documentation only | no |

## References Found

The audit found expected audio references in these categories:

- Backend safety code and tests for stripping public audiobook fields.
- Catalog truth and production canaries that assert audiobook endpoints stay 404.
- `README_audio.md`, `AUDIO_INTEGRATION_GUIDE.md`, and older audio pipeline docs with historical/local instructions.
- `scripts/open_source_audiobook_onboarding.py` and related dry-run/generation tooling.
- `frontend/src/pages/Reader.jsx` and unused `AudioPlayer` components with legacy `/audio/{lang}/{slug}.mp3` fallback code.
- Regression fixtures under `regression/fixtures/catalog-audit/`.

No public static metadata, sitemap, social preview, or SEO snapshot is allowed to expose these references as active audiobook availability.

## Changes Made

- Moved tracked files from `frontend/public/audio/` to `internal/audio_quarantine/frontend-public-audio/`.
- Removed stale ignored build copies from `frontend/build/audio/`.
- Updated `AUDIOBOOK_READINESS_REPORT.md` to show no public audio assets detected.
- Hardened `scripts/audiobook_accessibility_release_gate.py` to fail on audio-like files in `frontend/public` or `frontend/build`.
- Added focused unit tests for public/build audio asset leakage.
- Extended SEO regression to fail when public/build audio-like files exist.
- Extended UX regression to assert the stricter release-gate language.
- Normalized zero-width/bidirectional control characters out of quarantined `.json` and `.vtt` sidecars so changed text artifacts pass the repository safety scanner. Audio binaries were not rewritten.

## Remaining Blocked State

- `PUBLIC_AUDIO_RELEASE_BLOCKED` remains correct.
- Public audio is not enabled.
- Dracula audio remains disabled.
- Kshudhita Pashan remains pipeline-only.
- Derivative audiobook rights remain missing.
- Model commercial-use permission and model license evidence remain missing.
- Voice/narrator rights and voice cloning risk resolution remain missing.
- Bengali and English human listening QA remain missing.
- Owner approval and rollback evidence remain missing for public audio.

## Tests Run

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py AUDIOBOOK_ASSET_QUARANTINE_REPORT.md AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md AUDIOBOOK_READINESS_REPORT.md FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md backend/tests/test_audiobook_accessibility_release_gate.py backend/tests/test_controlled_publication_precheck.py scripts/audiobook_accessibility_release_gate.py scripts/controlled_publication_precheck.py regression/modules/11-seo.test.js regression/modules/14-ux-conversion-static.test.js output/launch/audio_asset_audit.json` | PASS, 11 files |
| `find internal/audio_quarantine/frontend-public-audio -type f \\( -iname '*.json' -o -iname '*.vtt' \\) -print0 | xargs -0 python3 scripts/check-hidden-unicode.py` | PASS, 20 files |
| `git diff --check` | PASS |
| `python3 -m py_compile scripts/controlled_publication_precheck.py backend/tests/test_controlled_publication_precheck.py scripts/audiobook_accessibility_release_gate.py backend/tests/test_audiobook_accessibility_release_gate.py` | PASS |
| `node --check regression/modules/11-seo.test.js` | PASS |
| `node --check regression/modules/14-ux-conversion-static.test.js` | PASS |
| `PYTHONPATH=. pytest backend/tests/test_controlled_publication_precheck.py backend/tests/test_audiobook_accessibility_release_gate.py` | PASS, 17 passed |
| `npm run controlled-publication:precheck` | PASS |
| `npm run catalog:audit` | PASS, 46 items audited |
| `npm run launch:audio-audit` | PASS |
| `npm run audiobook:release-gate` | PASS_EXPECTED_BLOCKED, `PUBLIC_AUDIO_RELEASE_BLOCKED`, 23 blockers |
| `npm run launch:seo-audit` | PASS |
| `npm run launch:social-preview-audit` | PASS |
| `npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | PASS, 65 passed |
| `npm --prefix frontend run build` | PASS |
| Final direct scan of `frontend/public` and `frontend/build` for audio-like files | PASS, no files found |

## Rollback Instructions

Rollback is not recommended unless a later approved public audiobook release exists. If rollback is required:

1. Move files from `internal/audio_quarantine/frontend-public-audio/` back to `frontend/public/audio/`.
2. Revert the release-gate hardening in `scripts/audiobook_accessibility_release_gate.py`.
3. Revert the related unit and regression checks.
4. Rebuild frontend.
5. Rerun `npm run audiobook:release-gate`, `npm run launch:audio-audit`, SEO/social audits, and regression.

Any rollback that makes audio files public must be paired with approved derivative audiobook rights, model/voice evidence, listening QA, accessibility evidence, owner approval, and rollback/takedown approval.
