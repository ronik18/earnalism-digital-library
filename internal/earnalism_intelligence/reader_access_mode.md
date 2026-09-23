# Text Reader access mode

The initial production mode is `PILOT_FULL_FREE` in `backend/data/controlled_launch.json`. It is limited to the three controlled pilot slugs, an authenticated signed India release-proxy assertion, accepted Reader-delivery rights, and a publication-bound lease. It creates no wallet debit. The first three canonical pages remain public previews; a signed-in reader needs a lease beyond page three.

`COMMERCIAL_ENTITLEMENT` is prepared but **not authorized or active**. A later release instruction may change the controlled launch mode only after paid commerce is separately qualified and enabled, and an exact accepted rights decision covers `reading_pass_session_start`, `reading_pass_page`, and `reading_pass_lease_renewal` for each title and territory. The production server denies commercial admission until both conditions are met. The existing metered Reading Pass service supplies balance checks, publication-bound leases, idempotent heartbeat debit, and revocation. A client flag or stored balance alone never grants access.

The release instruction must also update the frontend's paid-commerce presentation gate in `frontend/src/lib/controlledLaunch.js` and validate the resulting exact commit through protected CI, merge, deployment, and production smoke. This is a configuration/release change, not a Reader authorization redesign. Do not flip only the frontend flag, do not expand the title allowlist, and do not enable audio. Existing free leases stop authorizing protected pages when the server changes mode; a reader must acquire a new lease under the new policy.

The current source configuration remains `PILOT_FULL_FREE`, paid commerce disabled, public audio disabled. No payment, rights, publication, or production state is changed by this document.
