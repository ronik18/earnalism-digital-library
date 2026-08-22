# Lean Home, Library, and Commerce Redesign

## Decision

Keep the existing React frontend and FastAPI modular monolith. This program adds one internal frontend design-system directory and visual-contract fixtures; it does not introduce a framework, package, state manager, CSS framework, database, API version, or service boundary.

## Route and data contract

`/`, `/library`, and `/pricing` keep their public routes and current APIs during PR 2. Before any backend work, the program records local request count, compressed payload size, query count, and p50/p95. A backend change is permitted only after a measured budget failure and must retain route and response compatibility.

## Product truth

Visual references are geometry authority only. Release truth, payment offers, canonical-page previews, authentication, Reading Pass entitlements, and audiobook release gates remain authoritative. The public copy is limited to the first three pages, approved-audio preview where applicable, shared Reading Pass time, and no subscription or autorenewal only when those statements are true.

## Visual contract

The source board is immutable. `reference-manifest.json` records the pixel dimensions, bytes, and SHA-256 values for the three required reference images. The Playwright harness uses fixed viewports, deterministic fixtures, disabled animations, and narrowly scoped masks only for dynamic data.

## Cleanup contract

`scripts/generate_redesign_inventory.py` is dry-run only. It creates inventories and a quarantine manifest but never deletes, moves, uploads, or calls a provider. Any provider inventory, quarantine, or deletion needs an explicitly approved later PR and a rollback manifest.

## Phase boundary

PR 1 is inventory and contract only. Customer-facing page changes begin only after this PR is reviewed and merged. PR 3 is skipped unless current API measurements exceed the documented page budgets.
