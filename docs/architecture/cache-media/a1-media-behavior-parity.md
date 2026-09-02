# A1.2 media behavior parity

`backend/media` now owns only exact low-level range, storage-wrapper/matching, streaming, and policy primitives. `backend/server.py` retains the B2 client registry/configuration, fail-closed raw URL policy, FastAPI responses, authorization, release truth, database access, and package orchestration.

The route inventory, normalized OpenAPI surface, and audio route signatures are unchanged. The OpenAPI fingerprint intentionally excludes FastAPI's process-order-dependent GET/HEAD `operationId`; its paths, methods, parameters, request bodies, security, and responses are all included. Current range, upstream validation, ETag, storage URL/client, streaming, and policy vectors pass unchanged. This is a module-boundary refactor only: it makes no delivery optimization or A5 hardening claim.
