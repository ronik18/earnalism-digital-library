# Decommission Policy

Do not delete books destructively without explicit approval.

When an audiobook path repeatedly fails:

- If the reader is valid, keep reader live and hide/decommission audio.
- If audiobook score is below `9.0` after allowed attempts, mark audio as `AUDIO_DECOMMISSION_CANDIDATE`.
- If audio has robotic, mechanical, choppy, fallback, placeholder, stale, or mismatch flags, hide audio immediately.
- If source/content/rights fail, mark the full title `FULL_TITLE_DECOMMISSION_CANDIDATE` or `TERMINAL_BLOCKED_WITH_EVIDENCE`.
- Write tombstone/evidence and exclude the failed path from repeated waves.

For Bengali books, stale local audio that repeatedly fails manuscript match should be decommissioned while preserving the reader where valid.
