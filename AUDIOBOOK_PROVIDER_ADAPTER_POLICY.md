# Audiobook Provider Adapter Policy

All audiobook provider/model adapters must be dry-run safe by default.

## Adapter Contract

- Environment checks may inspect local command availability only.
- Dry-run generation must produce metadata, not audio.
- Local generation must require owner approval.
- Provider/cloud calls are prohibited unless a later phase explicitly enables them.
- Public audio URLs must remain empty until release approval.

## Research-Only Models

Research-only models may be benchmarked for internal comparison, but cannot become production release candidates until license review and owner approval are complete.

## Release Gate

`npm run audiobook:release-gate` must pass before any audio PR can move forward. The gate verifies Dracula audio remains disabled and no public audio URL or public audio claim is introduced.

