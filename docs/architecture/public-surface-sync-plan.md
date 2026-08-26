# Public-surface synchronization plan

## Audited baseline

The source-to-route inventory is in `public-route-inventory.md`. Production
baseline navigation was inspected through the browser; direct shell HTTP checks
were blocked by a transient local DNS resolver error and are recorded as an
external baseline limitation, not treated as a product failure. The immutable
reference checksums match `reference-manifest.json`.

## Implementation sequence

1. Add a lean shared public-surface primitive and a single visible preview-copy
   constant. Update public presentation and static SEO consumers to use it.
2. Reconcile shared header, footer, loading, empty, error and not-found states
   with the premium dark/ivory family and a prominent, aspect-safe lockup.
3. Apply the shared structure to discovery, commerce, book, editorial, support,
   auth, account and campaign families without changing their data or action
   flows.
4. Preserve V2 Reader, Listener and About as standalone experiences; make only
   deterministic presentation/copy integration changes that cannot alter
   authorization or release truth.
5. Run focused truth tests, production build, static SEO verification, route
   smoke, responsive/overflow checks, accessibility checks and regression.

## Non-goals

No backend, database, payment, entitlement, Reading Pass timing, audio release
truth, deployment architecture, dependency, or destructive cleanup change is
in this lane. Missing legal/reset/410 routes remain absent rather than being
invented. Legacy paths remain rollback-contained.

## Owner-review package

The package will contain route inventory, implementation plan, before/after
screenshots where browser reachability permits, responsive key-route captures,
truth results, and an honest list of unavailable visual comparisons. Pixel
identity is claimed only for complete reference regions; dynamic catalog and
release truth always outrank illustrative reference content.
