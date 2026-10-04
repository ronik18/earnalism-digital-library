# Google sign-in transition

## Actual architecture and root cause

The application uses Google Identity Services' implicit popup flow, not a routed
OAuth callback or authorization-code exchange. The popup returns an access token
to the Login component, which submits it to the existing same-origin `/api/auth/google`.
The backend verifies Google's audience and identity, rejects blocked users, creates
its existing reader session, sets the refresh cookie, and returns `{token, user}`.

Previously the component left the ordinary form visible throughout verification,
ignored the returned profile, then fetched `/api/users/me`. The auth provider's
state update triggered a declarative redirect to `next` (default `/account`) while
the callback also requested `/library`. A profile failure was swallowed by
`refreshUser`, permitting a success notification without confirmed hydration.
Google completion also failed to advance the provider's authentication generation.

```mermaid
sequenceDiagram
    participant UI as Login
    participant GIS as Google popup
    participant Auth as AuthProvider
    participant API as Verified backend
    UI->>GIS: Existing implicit sign-in
    GIS-->>UI: Credential callback
    UI->>UI: Show Signing you in (hide form)
    UI->>Auth: userGoogleLogin (single-flight)
    Auth->>Auth: Advance generation; resolving state
    Auth->>API: POST /api/auth/google (credentials included)
    API-->>Auth: Verified session token + authoritative user; refresh cookie
    Auth->>Auth: Validate response; commit current generation only
    Auth-->>UI: Authenticated identity
    UI->>UI: One replace navigation to safe internal next
```

Failed verification restores a retryable anonymous form. No artificial delay is
used. No redundant profile request is needed to establish the Google session.
Existing profile refresh remains available for account/Reader consumers. A persisted
back/forward-cache restore verifies the current stored session before routing,
because an older document can otherwise revive stale anonymous React state.
The pageshow listener is removed on unmount and does not run on ordinary loads.
Direct Google sign-in defaults to `/library`; a valid explicit `next` is retained.
Email sign-in and already authenticated visits retain their `/account` default.
External, protocol-relative, malformed, control-character and auth-loop return
paths fall back to an internal destination. Google cancellation stays on the form.

## Security boundary

Backend Google verification, audience validation, blocked-user handling, cookie
attributes, refresh/session issuance, JWT signing, and access guards are unchanged.
Only the existing backend-issued reader token is persisted using the existing
storage contract. No Google credential is persisted or included in evidence.
No permissions, payments, entitlements, rights or catalogue state changed.

## Production baseline observed (unpatched)

A real Google account selection was exercised in Chrome on 2026-10-04.
The ordinary Sign In form remained visible immediately after account selection.
Safe Network evidence:

| Request | UTC request time | Status | Duration |
| --- | --- | --- | --- |
| POST /api/auth/google | 2026-10-04T06:50:00.523Z | 200 | 1.933406 seconds |
| GET /api/users/me | 2026-10-04T06:50:02.459Z | 200 | 0.816407 seconds |

Final observed path: `/account`, despite the callback's competing `/library` navigation.
The refresh cookie was Secure, HttpOnly, SameSite=Lax, path=/, host=theearnalism.com.
Only attributes were recorded, never cookie/token values, emails, raw OAuth URLs
or credential-bearing request/response bodies.

Local transition tests use generated fixture credentials and deferred responses.
These establish pending-state, error, race and routing behavior, not live Google
provider authorization for a new localhost origin. Remote protected CI and actual
preview Google sign-in remain release gates; no deployment is authorized here.

## Local browser evidence and validation

Chrome was exercised at measured CSS viewports 1440×900 and 390×844 with the
actual Login/AuthProvider components in an isolated generated fixture harness.
The SDK callback and HTTP outcomes were generated fixtures, not live Google
verification. Verification was held unresolved until an explicit test action:
the ordinary form was absent, and the live status displayed Signing you in.
Completing verification navigated once to `/library` or the requested
`/reader/dracula?page=2`. Rejection restored the form; retry succeeded.
Refresh preserved the destination. After the back/forward-cache correction,
Back and Forward exposed no anonymous form for the valid restored session.
WebKit is not exposed by the available browser-control providers; its check is
not claimed. Preview testing with the real Google OAuth configuration is pending.

Validated commands:

- `CI=true npm test --prefix frontend -- --watchAll=false --runInBand`
- `.venv-uat/bin/python -m pytest -q backend/tests/test_google_auth_session_contract.py backend/tests/test_admin_authorization_hardening.py backend/tests/test_auth_password_safety.py backend/tests/test_reader_device_session_binding.py`
- `npm run build --prefix frontend` (includes static SEO generation/verification)
- `REGRESSION_FRONTEND_URL=http://127.0.0.1:3107 REGRESSION_API_URL=http://127.0.0.1:8107 CI=true REGRESSION_MODE=pr npm run regression -- --json --outputFile=/tmp/earnalism-google-regression-final.json`
- `git diff --check`

Disposable MongoDB and Redis, backend and built frontend were provisioned with
`scripts/start_local_uat.sh` using dedicated loopback ports 27037, 26407, 8107,
and 3107. No production database/API was used for regression execution.
The frontend defines no separate lint/typecheck script; the build's compiler
and existing lint integration passed. PR #516 owns the focused slot, so this
branch is committed locally without pushing, opening a conflicting PR or deploying.

Final local results: 98 frontend suites / 639 tests passed; targeted auth tests
3 suites / 52 tests passed; backend auth 33 passed; production build passed;
static SEO 172 snapshots / 3,647 assertions / 0 failures; broad PR-mode
regression 143 passed / 0 failed / 4 unchanged skips. Diff check passed.
