# Audiobook release conveyor v2

The supported path for a new audiobook is now one resumable handoff:

1. The approved Colab runner generates the MP3 and performs its local objective and listening QA.
2. Colab asks Railway for one short-lived production-B2 PUT URL and uploads the MP3 with its SHA-256 in object metadata.
3. Colab posts one compact release receipt to `/api/admin/books/{slug}/audiobook/release`.
4. Railway verifies the title's existing reader/rights state, manuscript hash, QA thresholds, B2 object size, and B2 checksum metadata before atomically activating the proxy route.
5. The public projection derives `audio_enabled`, `audiobook_enabled`, `audio_status`, and release QA fields from the server-owned release record.

The evidence ZIP is no longer a required transport artifact. The release receipt stores the decision-critical hashes, storage identity, QA summary, model/voice identity, and idempotency fingerprint. Detailed local reports remain optional audit material and are never needed to activate public audio.

## Safety invariants

- Permanent B2 credentials never enter Colab or the browser.
- Public activation is fail-closed when any checksum, rights, reader, QA, or storage check is incomplete.
- The same receipt is safe to retry; a different receipt cannot silently replace an active title.
- Paragraph synchronization is not a release requirement for the audio-only lane. The reader/audio lanes remain independent.
- The release record is written with an audit event and the public URL remains the gated reader proxy, never the raw B2 URL.
- Existing package-v2 releases retain their separate primary/replica evidence contract.
