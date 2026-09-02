# PR344 final CI sanitized-fixture root cause

`Account.jsx` requires both `REACT_APP_ENABLE_VISUAL_FIXTURES=1` at compile time and `visual-fixture=1` in the route query before it renders `data-testid="account-visual-fixture"`.

The previous final workflow supplied the query parameter but compiled the browser-tested bundle without the flag. The fixture-disabled local build therefore redirected `/account?visual-fixture=1` to Login; the fixture-enabled review build rendered only the synthetic `review@example.invalid` identity without authentication, Account API traffic, or mutations.

Classification: `FINAL_CI_REVIEW_BUILD_MISSING_COMPILE_TIME_VISUAL_FIXTURE_FLAG`. The mandatory `private_fixture.fixture_visible === true` assertion remains unchanged.
