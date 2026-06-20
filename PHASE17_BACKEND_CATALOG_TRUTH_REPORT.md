# Phase 17 Backend Catalog Truth Report

## Summary

Phase 17 adds a backend catalog truth gate for the Dracula-only controlled launch.
The backend now has deterministic helpers for live-approved, pipeline-only, reader,
preview, audio, and public projection decisions.

## Changed Behavior

- `/api/books`, `/api/home`, `/api/home/books`, and `/api/featured` project only
  controlled live-approved public book metadata.
- `/api/books/{slug}` and reader endpoints fail closed for non-Dracula slugs.
- Public audiobook asset endpoints return 404 while audio is disabled.
- Public projections strip chapter body content, rights/source evidence, and audio
  storage fields.
- Daily owner dry-run reports include catalog truth fields.

## Explicit Non-Changes

- No production data was mutated.
- No book was published.
- No audio was enabled.
- No payment, provider, TTS, STT, OCR, LLM, image, email, or social API was called.
- No prices, wallet behavior, or Razorpay behavior changed.

## Validation Target

The PR is ready only if:

- backend truth tests pass,
- launch/payment/controlled-publication checks pass,
- regression checks pass,
- frontend build passes,
- catalog truth audit reports zero unapproved reader/audio/sitemap exposure.

## Rollback

Revert this PR. The changes are scoped to deterministic backend projection/gating,
local audit reporting, tests, and docs.
