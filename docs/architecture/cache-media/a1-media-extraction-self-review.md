# A1.2 strict self-review

| Classification | Finding |
|---|---|
| REQUIRED_BEFORE_A5 | B2 registry ownership remains in `backend.server` to preserve the mutable server-level monkeypatch contract. |
| REQUIRED_BEFORE_A5 | Current synchronous body reads, chunk size, cancellation behavior, storage timeouts, and retries are intentionally unchanged. |
| REQUIRED_BEFORE_RELEASE | Production storage and browser evidence remains a separate fail-closed release requirement. |
| POST_RELEASE_MONITORING | Observe storage errors, range failures, body closure, and browser buffering only after a separately approved deployment. |
| OPTIONAL | Consider a general HTTP conditional-request helper only after proving its non-media callers remain compatible. |

Reviewed PASS: no route movement; authorization and release gating remain in `backend.server`; raw unmatched Backblaze URLs remain fail-closed; there is one retained B2 registry with lazy per-store clients; no cache, data, frontend, deployment, PR #344, or A5 behavior change is present. A1.2 blockers: 0.
