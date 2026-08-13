# Audiobook release conveyor v2

## Conversation review contract

The conveyor has two subjective per-title review points:

1. Render the checksum-bound reader preview in the conversation and record `READER_PREVIEW` approval.
2. Render six or seven checksum-bound representative audio files with conversation players and record `AUDIO_SAMPLE_SET` approval for the exact model, voice, sample-set hash, listening scores, confidence, fatal-flag result, and explicit owner public-release intent.

The second packet authorizes automatic continuation; it is not a release-gate waiver. Full-title generation or reuse, sanitization, chapter/index/pagination checks, source fidelity, technical audio, storage, cache and service-worker safety, CI/build, browser/emulated-device validation, production promotion, and post-deployment checks remain mandatory and fail closed. The persistent production automation environment guard remains an operational kill switch.

`READY_FOR_GO_LIVE` means both conversation approvals and all pre-production checks passed. Only a successful promotion response with API, range, playback, mobile reader/audio journey, resume-recovery, cache-control, and stale-URL postchecks may produce `LIVE`.

The supported path for a new audiobook is now one resumable handoff:

1. The approved Colab runner generates the MP3 and performs its local objective and listening QA.
2. Colab asks Railway for one short-lived production-B2 PUT URL and uploads the MP3 with its SHA-256 in object metadata.
3. Colab posts one compact release receipt to `/api/admin/books/{slug}/audiobook/release`.
4. Railway verifies the title's existing reader/rights state, manuscript hash, QA thresholds, B2 object size, and B2 checksum metadata before atomically activating the proxy route.
5. The public projection derives `audio_enabled`, `audiobook_enabled`, `audio_status`, and release QA fields from the server-owned release record.

The evidence ZIP is no longer a required transport artifact. The release receipt stores the decision-critical hashes, storage identity, QA summary, model/voice identity, sample-set identity, and idempotency fingerprint. Detailed local reports remain optional audit material and are never needed to activate public audio.

## Safety invariants

- Permanent B2 credentials never enter Colab or the browser.
- Public activation is fail-closed when any checksum, rights, reader, QA, or storage check is incomplete.
- VoiceOver and TalkBack physical-device checks may remain truthfully `NOT_TESTED` only under the narrow accessibility exception in `audiobook_acceptance_policy.json`. The exception must identify the owner, accept the residual risk, match the release attempt fingerprint and audio SHA-256, carry its own valid checksum, and set `other_release_gates_waived` to `false`.
- Keyboard controls, chapter navigation, pause/resume recovery, every objective and human-listening threshold, rights, storage, endpoint, browser, Git, and deployment gate remain mandatory; the accessibility exception cannot convert them to a pass or waive them.
- The same receipt is safe to retry; a different receipt cannot silently replace an active title.
- Paragraph synchronization is not a release requirement for the audio-only lane. The reader/audio lanes remain independent.
- The release record is written with an audit event and the public URL remains the gated reader proxy, never the raw B2 URL.
- Existing package-v2 releases retain their separate primary/replica evidence contract.
