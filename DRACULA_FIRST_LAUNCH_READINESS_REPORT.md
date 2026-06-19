# Dracula First Launch Readiness Report

Recommendation: `KEEP_DRACULA_LIVE`

## What Changed

- Backend public book and reader APIs now gate public access to Dracula only.
- Homepage now presents a Dracula-first controlled launch.
- Library now presents Dracula as the only live release and future books as pipeline.
- Book cards prevent unapproved reader links.
- Dracula page includes source, rights, audio-unavailable, and pass CTAs.
- Reader disables Dracula audio controls and tracks reader-start/completion events.

## What Did Not Change

- No production data was mutated.
- No audiobook was enabled.
- No additional books were published.
- No LLM, TTS, STT, OCR, image, paid, email, social, or external provider call was added.

## Rollback

Revert this PR/commit. Dracula's controlled publication database state can remain intact; the rollback only restores the prior broad-catalog public UI/API behavior.

## Remaining Risks

- CRA metadata remains client-side.
- Manual browser QA should be performed before deploy.
