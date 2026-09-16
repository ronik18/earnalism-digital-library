# Reader auth follow-up — 16 September 2026

Status: local repair, not released. PR #400 is already deployed at `3a539e96572754f5d05d2ade05c2d3cce17b9075`, live bundle `main.98bb273e.js`. Live Frankenstein free-page navigation, font-size changes, preferences/focus restoration, Library exit, and removal of the castle/1897 fixture data passed. Earlier candidate-only notes remain historical checkpoints.

The refreshed browser showed an anonymous state. Its cause is unproven; ordinary session expiry remains possible. Source review independently confirmed two pre-existing defects: `skipAuthRedirect` also prevented bootstrap refresh, and strict original-token equality rejected a valid profile after token rotation.

The follow-up separates redirect suppression from refresh; shares an eight-second refresh deadline and one replay; gives profile calls a 15-second deadline; distinguishes token rotation from an account change; and rejects stale profile, retry, and refresh responses after logout or newer credentials. Terminal 401 still clears current authentication and 403 remains denied. Retryable refresh outages fail closed without deleting a potentially recoverable credential. Server logout remains bounded and best-effort, not guaranteed revocation.

Validation: five focused suites / 29 tests; full frontend 69 suites / 408 tests; production build; 2,502 static SEO assertions; and 46 workflow-contract tests passed. Tests mount the actual AuthProvider with real Axios interceptors and cover rotation, concurrent/late 401s, terminal denial, recoverable outages, logout and account-change races. Existing real HTTP tests prove stalled refresh settlement is bounded. Independent source review found no blocking issue. These are local test results, not paid production acceptance.

Secure customer sign-in is pending. Zero of the authorized 120 Reading Pass seconds have been used. Obtain fresh CI for the follow-up, release through merged main, verify its deployed version, then complete the authorized customer page/renewal/settlement checks. No manuscript, rights, audio, publication, geographic policy, backend financial logic, or balances were changed by this follow-up.
