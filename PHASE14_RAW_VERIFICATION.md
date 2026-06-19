# Phase 14 Raw Verification

Branch: `codex/dracula-controlled-publication-candidate`

Baseline commit before this hardening diff: `735ff9712e8951ac2f84611e5efdb77d2ecaa1eb`.

## Local Line Counts

| File | Local line count |
| --- | ---: |
| `backend/publishing_workflow.py` | 400 |
| `backend/tests/test_dracula_candidate_scripts.py` | 295 |
| `backend/tests/test_publishing_workflow.py` | 298 |
| `scripts/approved_to_publish_builder.py` | 429 |
| `scripts/prepare_dracula_candidate.py` | 1205 |
| `APPROVED_TO_PUBLISH.md` | 39 |
| `DRACULA_GATE_RESULTS.md` | 24 |
| `DRACULA_SOURCE_RIGHTS_REPORT.md` | 57 |
| `PHASE14_VALIDATION_REPORT.md` | 100 |

## Raw GitHub Download Command

After the hardening commit is pushed, verify raw GitHub line counts with:

```bash
branch=codex/dracula-controlled-publication-candidate
for file in \
  backend/publishing_workflow.py \
  backend/tests/test_dracula_candidate_scripts.py \
  backend/tests/test_publishing_workflow.py \
  scripts/approved_to_publish_builder.py \
  scripts/prepare_dracula_candidate.py \
  APPROVED_TO_PUBLISH.md \
  DRACULA_GATE_RESULTS.md \
  DRACULA_SOURCE_RIGHTS_REPORT.md \
  PHASE14_VALIDATION_REPORT.md
do
  curl -fsSL "https://raw.githubusercontent.com/ronik18/earnalism-digital-library/${branch}/${file}" \
    | wc -l \
    | awk -v f="$file" '{print f": "$1" lines"}'
done
```

## Result

Local files show normal physical line breaks and passed `scripts/check-hidden-unicode.py`. Raw GitHub verification should be repeated after this cleanup commit is pushed because the current working tree contains the final unpushed hardening diff.
