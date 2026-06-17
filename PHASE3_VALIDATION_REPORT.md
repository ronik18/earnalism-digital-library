# Phase 3 Validation Report

Phase: demand and growth-priority scoring.

Validation start commit SHA: `92bf26d` (`Add deterministic demand priority scoring`).

## Commands Run

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py backend/demand_scoring.py backend/tests/test_demand_scoring.py scripts/demand_priority.py package.json DEMAND_SCORING.md PHASE3_VALIDATION_REPORT.md` | PASS |
| `python3 -m py_compile backend/demand_scoring.py` | PASS |
| `python3 -m py_compile backend/tests/test_demand_scoring.py` | PASS |
| `python3 -m py_compile scripts/demand_priority.py` | PASS |
| `pytest backend/tests/test_demand_scoring.py` | PASS. 13 tests passed. |
| `npm run demand:score` | PASS. Wrote CSV, Markdown, and JSON reports under `output/demand/`. |
| `npm run catalog:audit` | PASS. 251 items audited. |
| `npm run regression -- modules/13-public-content-governance.test.js` | PASS. 15 tests passed. |
| `npm --prefix frontend run build` | PASS. Frontend compiled successfully. |

## Line-Count / Raw File Verification

Local normalized line counts:

- `backend/demand_scoring.py`: 566 lines
- `backend/tests/test_demand_scoring.py`: 169 lines
- `scripts/demand_priority.py`: 107 lines
- `package.json`: 35 lines
- `DEMAND_SCORING.md`: 197 lines
- `PHASE3_VALIDATION_REPORT.md`: 70 lines

Raw GitHub verification should show normal LF line breaks after this branch is
pushed. No minified or one-line Python file is expected.

## Hidden Unicode Scan

The hidden Unicode checker scanned for:

- U+202A to U+202E
- U+2066 to U+2069
- U+200B
- U+200C
- U+200D
- U+FEFF
- CR-only line endings

The scan passed for the Phase 3 files and reports.

## Demand Report Generation

`npm run demand:score` generated:

- `output/demand/demand_priority_report.csv`
- `output/demand/demand_priority_report.md`
- `output/demand/demand_priority_report.json`

The reports include `action_status` and `blocking_reason`. Tier C and
unknown-rights items are not normal generation candidates.

## Production Mutation Confirmation

No production content was mutated. Phase 3 remains deterministic and dry-run
only. It does not call LLM, TTS, image, paid, or external market APIs.

## Remaining Risks

- Score weights are deterministic heuristics and should be recalibrated with
  production engagement data over time.
- Phase 3 consumes rights metadata but does not replace Phase 2 legal/rights
  verification.
