# Phase 14 Raw Download Verification

Branch: `codex/dracula-controlled-publication-candidate`

Commit checked: `a1eaa2101c747d7a627920b5ab7525f77d52d01d`

Command pattern:

```bash
curl -fsSL "https://raw.githubusercontent.com/ronik18/earnalism-digital-library/codex/dracula-controlled-publication-candidate/<path>" | wc -l
```

## Raw GitHub Line Counts

| File | Raw downloaded line count |
| --- | ---: |
| `scripts/prepare_dracula_candidate.py` | 1164 |
| `scripts/approved_to_publish_builder.py` | 289 |
| `scripts/post_deploy_route_canary.py` | 223 |
| `scripts/launch_readiness_audit.py` | 2415 |
| `backend/tests/test_dracula_candidate_scripts.py` | 192 |
| `backend/tests/test_launch_readiness_audit.py` | 235 |

## Result

Raw GitHub downloads show normal physical line breaks for the changed scripts/tests. No minified one-line Python or test files were observed.
