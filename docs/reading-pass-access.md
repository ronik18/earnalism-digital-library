# Public Preview and Universal Reading Pass

Status: **implemented behind `READING_PASS_V2_ENABLED=false`; data and preview-asset migration required before staging activation**.

## Product contract

- Canonical server pages 1–3 are public and never consume balance.
- Canonical page 4 onward requires authentication, positive balance, and a current short lease.
- Audiobooks have no public preview: the public audio boundary is exactly `0` seconds.
- Every audiobook manifest, segment, sidecar, and monolithic audio route requires authentication and an active paid Reading Pass lease from the first playable byte.
- Purchased seconds are shared by every eligible book and audiobook.
- One member account may be authenticated on many devices, but only one paid session may consume time.
- Seconds, access, session ownership, and payment status are server-authoritative.
- The feature introduces no pass expiry, price change, or refund-policy change.

## Architecture

### Canonical text

`backend.domain.reading_pass.canonical_page_records` groups controlled chapter HTML at semantic block boundaries. It does not inspect viewport, font, zoom, orientation, or client pagination. Each immutable record contains:

- book slug and 1-based page index;
- chapter identity and order;
- rendered content and SHA-256;
- segmentation version;
- the derived public-preview marker.

Active segmentation is selected by `reader_segment_manifests`; the content itself lives in `reader_content_segments`. A version conflict is rejected rather than overwritten.

Public page responses may be cached. Protected page responses contain one segment, use `Cache-Control: private, no-store`, vary on authorization and lease headers, and never include adjacent protected pages.

### Lease and metering

`backend.reading_pass_service.ReadingPassService` owns the lease protocol:

- heartbeat: 10 seconds;
- maximum lease: 20 seconds;
- reconnect grace: 15 seconds;
- text inactivity: 120 seconds.

The values are server-configurable, while the public boundaries remain fixed at three canonical pages and zero public audio seconds.

Lease tokens are random opaque values. Only an HMAC-SHA256 fingerprint is stored. Every lease binds account, authentication session, device, metering session, content type, content ID, scope, version, sequence, issue time, and expiry.

Debit is calculated from server timestamps and capped by the old lease. The API accepts a next activity state, not client elapsed time. Each renewal first settles the preceding interval from the server's stored `billing_active` state, then applies the requested text/audio state. A pause therefore cannot erase time already consumed.

MongoDB transactions commit the following together:

1. conditional non-negative user balance mutation;
2. append-only `TIME_DEBIT` ledger event;
3. compatibility transaction row;
4. lease version/sequence transition;
5. heartbeat idempotency record;
6. privacy-safe audit event.

Database uniqueness enforces one `active_lock` per account and one result per heartbeat key/sequence across application instances. Terminal transitions unset the lock; paused sessions retain it until explicit end, transfer, revoke, exhaustion, or expiry.

End, transfer, revocation, and stale-expiry cleanup all settle the final server-timed interval in the same transaction before releasing the lock. This prevents repeated sub-heartbeat sessions or device switching from bypassing debit. Unknown transaction commit outcomes retry the same commit; they do not replay a possibly committed balance mutation.

### Payment integrity

The existing Razorpay order, verification, webhook, simulator, and reconciliation surfaces remain in use. Verified credit now commits the intent transition, exact integer-second increment, `PASS_CREDIT` ledger event, compatibility transaction row, and audit record in one transaction.

The ledger idempotency key is `payment:{intent_id}`. Provider order and payment IDs retain their existing unique indexes. Duplicate browser callbacks and webhooks return the already-credited intent and cannot create a second credit.

No browser-submitted amount, currency, duration, or success state is trusted.

### Audio delivery

Public audiobook preview duration is exactly `0` seconds. Do not generate,
upload, activate, or publish public preview derivatives. The retired
`scripts/generate_audiobook_preview.py` command exits with
`AUDIO_PREVIEW_DISABLED` and cannot write audio files.

Public catalog and reader-manifest responses may show locked audiobook metadata,
but never an audio URL, package-manifest URL, provider/storage URL, waveform, or
playable media. Every audiobook byte, including a `Range` request, requires an
approved release, a signed-in user, and an active paid Reading Pass lease.

Validate an approved private master packet independently with:

```bash
python3 scripts/audiobook_master_gate.py \
  --packet <checksum-bound-approved-master-packet.json> \
  --source <approved-local-master-or-delivery-file> \
  --slug <slug>
```

Repeat with `--activate` only after reviewing the resolved store, immutable object version ID, object size, SHA-256 metadata, source hash, duration, and distinct content-addressed preview key. The API performs a version-bound storage `HEAD`, rejects full-audio URL reuse, archives the previous active preview, and writes activation plus audit evidence transactionally.

When v2 is enabled, all existing full audiobook routes require the same account/content-bound audio lease and return private no-store responses. Native media requests use two short-lived `HttpOnly`, `Secure`, `SameSite=None` opaque cookies because an `<audio>` element cannot attach bearer headers. The backend rebinds those cookies to an active login session, exact content ID, lease hash, and expiry before serving bytes. Session mutations still require a bearer token. The service worker bypasses all Reading Pass and reader audiobook API requests.

### Position and devices

`reading_pass_positions` stores one versioned text or audio position per account/content pair. Stale versions return authoritative state and cannot grant access. Positions are restored across devices, saved after navigation/playback, and preserved through exhaustion or transfer.

`reading_pass_devices` records bounded device labels and authentication-session association. The Account screen joins these records to privacy-filtered login sessions and supports revocation. Device revocation invalidates the login and expires its active lease. Controlled transfer atomically invalidates the old lease before creating the new one.

## API

Public:

- `GET /api/reading-pass/config`
- `GET /api/reading-pass/books/{slug}/manifest`
- `GET /api/reading-pass/books/{slug}/pages/{pageIndex}` for pages 1–3
- `GET|HEAD /api/reading-pass/audiobooks/{slug}/preview/manifest`
- `GET|HEAD /api/reading-pass/audiobooks/{slug}/preview/audio`

Authenticated:

- `GET /api/reading-pass/wallet`
- `POST /api/reading-pass/sessions/start`
- `POST /api/reading-pass/sessions/transfer`
- `POST /api/reading-pass/leases/renew`
- `POST /api/reading-pass/sessions/end`
- `GET /api/reading-pass/positions/{contentType}/{contentId}`
- `PUT /api/reading-pass/positions`
- `GET /api/reading-pass/devices`
- `DELETE /api/reading-pass/devices/{deviceId}`
- protected page 4+ and all full audio package/legacy routes.

Admin migration:

- `POST /api/admin/reading-pass/books/{slug}/segments`
- `POST /api/admin/reading-pass/audiobooks/{slug}/preview`
- `GET /api/admin/reading-pass/health`

Lease-bound requests send opaque credentials in headers, never URLs:

- `X-Reading-Pass-Session`
- `X-Reading-Pass-Lease`

Machine-readable failures use `AUTH_REQUIRED`, `PASS_REQUIRED`, `BALANCE_EXHAUSTED`, `LEASE_EXPIRED`, `SESSION_ACTIVE_ELSEWHERE`, `CONTENT_NOT_AUTHORIZED`, `PAYMENT_PENDING`, `PAYMENT_VERIFICATION_FAILED`, and `RATE_LIMITED` as applicable. Missing authentication is `401`; authenticated denial is `403`.

## Database changes

Startup index migration adds:

- unique ledger `idempotency_key` when present;
- immutable segment `(book_slug, page_index, segmentation_version)`;
- segment manifest `(book_slug, segmentation_version)` and one active manifest per book;
- unique Reading Pass session ID;
- one unique string `active_lock` per consuming account;
- unique heartbeat `(session_id, idempotency_key)` and `(session_id, sequence)`;
- unique device `(user_id, device_id)`;
- unique position `(user_id, content_type, content_id)`;
- audit indexes by event/user and time.

The migration is additive and reversible while the flag is off. Existing wallet and payment fields remain compatibility projections; ledger events are the immutable audit truth.

## Content migration

Use the authenticated API tool. It is dry-run by default:

```bash
python3 scripts/migrate_reading_pass_segments.py \
  --api-base https://staging-api.example/api \
  --admin-token "$EARNALISM_ADMIN_TOKEN" \
  --all
```

After reviewing page counts and hashes:

```bash
python3 scripts/migrate_reading_pass_segments.py \
  --api-base https://staging-api.example/api \
  --admin-token "$EARNALISM_ADMIN_TOKEN" \
  --all --apply --activate
```

Never reuse a segmentation version for different content. Change the version and perform another dry run.

## Frontend behavior

The Reader obtains feature state from the server manifest. When disabled, the existing reader is unchanged. When enabled and segments are active:

- `p` identifies a canonical server page; viewport pagination remains presentation-only;
- page 4 starts or transfers a protected lease before requesting content;
- the timer stays visible, uses `HH:MM:SS`, and reports `Running`, `Paused`, `Preview`, `Connecting`, or `Active on another device`;
- screen readers receive one announcement when balance crosses 5 minutes, 1 minute, 10 seconds, and exhausted;
- approved audiobooks play only the separate public preview until the member explicitly continues; protected playback activates billing with a server heartbeat and native media cookies;
- text and audio positions synchronize through versioned server records, and Account lists/revokes device sessions;
- protected HTML is cleared when the lease pauses, expires, or exhausts;
- resume is explicit and obtains a new lease;
- paywall focus is trapped, Escape closes it, and focus returns;
- controls remain at least 44 by 44 CSS pixels;
- mobile placement respects safe-area insets and avoids the reader controls;
- service-worker storage is bypassed for every Reading Pass and protected audio response.

The local countdown is visual only. Server renewals replace it with authoritative balance.

## Observability

`reading_pass_audit` records session start, lease renew/pause/expiry, transfer, debit, credit, replay suspicion, device revocation, and segment activation without tokens, cookies, protected text, or payment secrets.

`GET /api/admin/reading-pass/health` exposes non-PII active/overdue session counts, negative-wallet invariants, wallet-alias mismatches, immutable-ledger/balance mismatches, and one-hour audit-event totals for dashboards. Ledger reconciliation reads canonical `signed_seconds` and falls back to legacy `credit - debit` rows, so historical compatibility events remain auditable without mutation. Reading Pass routes have their own configurable per-identity rate-limit scope and return `RATE_LIMITED` with `429`.

Operational monitors must alert on:

- negative user balance;
- duplicate active leases;
- ledger/balance divergence;
- credited payment without a ledger credit;
- protected route success without a lease;
- replay and authorization-denial spikes;
- renewal failure and transfer-rate spikes.

## Rollout

1. Deploy code with `READING_PASS_V2_ENABLED=false`.
   Generate a dedicated 32+ character `READING_PASS_TOKEN_SECRET`; enabling without it fails startup.
2. Run index/startup migration and verify no uniqueness conflict.
3. Dry-run canonical segments for every live reader title.
4. Apply and activate segment manifests in staging.
5. Do not generate or register public audiobook previews; protected playback begins only after an active paid Reading Pass lease.
6. Verify old full-file public URLs are unavailable.
7. Run payment, lease, content, service-worker, responsive, and concurrency suites.
8. Enable the server flag only in staging.
9. Validate 320, 360, 390, 768, 1024, and 1440 px; mobile landscape; safe-area; keyboard; and desktop 200% zoom.
10. Roll out gradually only after staging has zero invariant violations.

Backend enforcement must be enabled before any production UI claims the new access model.

## Rollback

1. Set `READING_PASS_V2_ENABLED=false`.
2. Redeploy the merged source.
3. Leave segment, ledger, session, device, position, and audit records intact.
4. Do not delete payment credits or immutable ledger events.
5. Archive, rather than overwrite, an incorrect active segment manifest.
6. Revoke any still-active v2 sessions if the rollback follows an authorization incident.

The additive indexes and collections may remain; dropping them is not required for functional rollback.

## Residual limitations and release blockers

- Web software cannot prevent screenshots, screen recording, speakers-to-microphone recording, or manual transcription of legitimately displayed content.
- A delivered short text segment cannot be made unreadable against a fully hostile browser after delivery; short leases, segment-only responses, no-store, and DOM clearing bound exposure.
- Production cannot enable v2 until every live reader has an active canonical segment manifest and every approved audiobook is protected by the active-pass media authorization path.
- Physical-device background/locked-screen playback must be validated with the final protected-media player before production enablement.
- MongoDB transactions require a replica set/sharded deployment; startup and staging preflight must fail closed if transaction support is absent.
