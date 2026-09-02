# A8 backend integration root cause

The previous `pytest -q backend/tests` invocation addressed a default backend
URL at `http://127.0.0.1:8000` without first starting the repository's
supported loopback UAT harness. The root cause is
`BACKEND_SERVER_HARNESS_NOT_STARTED`, not a cache/media correctness result.

The reusable harness is `scripts/start_local_uat.sh`; CI supplies only a
disposable MongoDB replica-set service, synthetic UAT data, and a loopback
backend. No production service, credential, Redis, or object storage is used.
