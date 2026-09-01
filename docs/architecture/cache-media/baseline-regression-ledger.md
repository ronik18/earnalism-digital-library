# Known baseline regression ledger

The ledger contains all 16 original reproduced failures: three cleanup and 13 legacy audio-routing/package tests. Each entry has a stable ID, exact JUnit node ID, base and untouched-PR result, final result, root cause, authority decision, evidence, replacement coverage, blocker status, and follow-up condition.

No original failure is silently removed from the record. Final suite reports must be green; the fingerprint verifier rejects missing evidence, absent replacement coverage, an unexpected fingerprint, or any final failure.
