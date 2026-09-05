# PR #356 post-merge CI first-failure repair

## Evidence

- The main workflow `33976232842`, attempt `1`, failed in the smoke journey with `net::ERR_ABORTED`.
- No regression artifact was produced because the smoke command runs before the regression artifact path is created.
- The exact smoke-recorder and workflow blobs had already passed in PR #356.
- A loopback-only smoke run from the merged source passed.

## Root cause

The smoke fixture classified every non-static aborted browser request as a hard network/server failure. `ERR_ABORTED` is a client-side cancellation when a later navigation supersedes an in-flight request, so it is not proof that a route, API, Reader entitlement, cache, or production runtime failed.

## Forward correction

Ignore aborted requests in the network-failure classifier. Preserve hard failures for HTTP 5xx responses and non-aborted document, fetch, XHR, and script failures. Route timing and route-error checks continue to detect unsuccessful navigation.

## Scope boundary

This repair changes only CI smoke-fixture logic, focused tests, and this record. It changes no production runtime, data, deployment configuration, Reader runtime, cache runtime, audio runtime, or frontend runtime.
