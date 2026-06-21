# Audiobook Regeneration Governance Report

Status: `REGENERATED_NARRATION_WORKFLOW_READY`

Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

Full audiobook status: `FULL_AUDIOBOOK_BLOCKED`

Owner status: `OWNER_APPROVAL_REQUIRED`

## Scope

This PR creates a separately approved regenerated narration workflow for Earnalism audiobooks. It does not generate audio, upload audio, enable public audio, expose audio URLs, or mutate production data.

## Governed Candidate

- Book: `kshudhita-pashan`
- Title: `ক্ষুধিত পাষাণ`
- Language: `bn`
- Product state: `PIPELINE_ONLY`
- Regeneration request: internal planning only
- Public release: false
- Full audiobook: false
- Preview: false
- Human review: required

## Required Approvals

- Owner approval
- Rights approval
- Source-text approval
- Voice-style approval
- Human listening QA approval
- Product-release approval

## Default Gate Result

The default request remains blocked because all approval checkboxes are intentionally false. `npm run audiobook:regen:precheck` should fail until approvals are recorded. Planning and manifest commands may create internal draft artifacts with `APPROVAL_REQUIRED` status and no audio URLs.

## Non-Actions Confirmed

- No public book was published.
- No public audiobook was enabled.
- No public audio URL was exposed.
- No provider API was called.
- No voice was generated.
- No external upload was performed.
- No claim of human narration was made.
