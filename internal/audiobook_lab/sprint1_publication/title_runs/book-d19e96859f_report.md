# গিন্নি Google Full-TTS ASR Repair Handoff

Generated: `2026-07-12T21:48:24Z`

- Slug: `book-d19e96859f`
- Classification: `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED_PRIVATE_TTS_PASS`
- Public reader: `Yes`
- Public audiobook: `No - AUDIO_HIDDEN_NOT_PUBLIC`
- Provider: `google / google-cloud-texttospeech / bn-IN-Chirp3-HD-Aoede`
- Style: `literary_warm_pacing`, speaking rate `0.94`
- Private audio: `8,256,813` bytes, `515.976` seconds, 6 chunks
- Audio SHA-256: `d8ccbdda0528ef9b0620638e944b12f5b5ed41d90cdbb0a5a99587fd4a340271`
- Sanitized manuscript SHA-256: `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe`
- Controlled chapter aggregate SHA-256: `ad4532ec513d4241d852a83595c027390b6c8dd2a9196a6d58fdfb84cbed25bf`
- TTS input sequence SHA-256: `dfc5d4e20d43c740cf8c4ed134151134c3af8bdcbf2ac4ad7da7c4bcc1383971`
- Full-book listening QA: `6/6 samples at 9.4, confidence 0.95, no fatal flags`
- Sync: `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`, measured group audio duration, `auto_estimated_sync=false`, score `10.0`
- Current endpoint observation: `HTTP 404`; no release endpoint proof or hash binding exists
- Publication action in this run: `None`

## Release Decision

The private Google narration passes construction, listening, and measured section-sync checks, but it does not pass the required audio-derived ASR/source gate. Upload and release-packet work must not start until ASR/source reaches `9.7` with first/last checks. No production metadata mutation, public audio enablement, deployment, or publication is authorized.

The root and backend controlled-launch files both exclude this slug from `audio_enabled_slugs`, and the reader manifest keeps `audio_enabled=false` and `audiobook_enabled=false`. Both mirrored `public_book.json` files still contain historical `audio_enabled=true`, `audiobook_enabled=true`, and `generate_audiobook=true` values; those stale local flags are not release proof and must be reconciled by the packet flow rather than treated as public truth. The live audiobook route returned `404`, so the title remains non-public.

## Source And QA Truth

The sanitized display manuscript is 6,485 characters and hashes to `79b0...05fe`. The controlled chapter aggregate is 6,516 characters and hashes to `ad45...25bf`; the controlled source traceability hash is `44dd...c8ce`. Google-safe text preparation produces the TTS input sequence hash `dfc5...3971`. These hashes identify different source representations and must not be substituted for one another.

The construction-provenance score is `10.0`: all six generated chunks match the recorded TTS inputs, TTS input coverage is `100%`, canonical-to-clean match is `0.9994`, and prepared-text boundaries pass. Raw ASR transcript similarity is only `0.6838`; therefore the explicit ASR/source gate fails. Construction provenance is not a substitute for audio-derived alignment.

Bounded repair probes did not clear the gate. OpenAI `gpt-4o-mini-transcribe` peaked at `8.0982`; Google `default` peaked at `5.4601`; Google `latest_long` is unsupported for `bn-IN`; and OpenAI `gpt-4o-transcribe` with explicit `bn` peaked at `6.7606`. These arms must not be repeated.

All six first/chunk/middle/final listening samples scored `9.4` at confidence `0.95`. Robotic texture, mechanical cadence, list-reading rhythm, choppy joins, fallback TTS, abrupt resets, repeated endings, and placeholder audio were all false. No 10/10 quality claim is made.

## Cost Evidence

- Current Google full TTS estimate: `$0.1287`
- Current ASR estimate: `$0.0688`
- Current six-sample listening QA estimate: `$0.3000`
- Current QA estimate: `$0.3688`
- Current Google TTS plus QA estimate: `$0.4975`
- TTS manifest prior-title estimate: `$0.9724`
- TTS manifest title estimate after adding Google TTS only: `$1.1011`
- Actual provider billing: `NOT_REPORTED`

The `$0.4975` and `$1.1011` values have different scopes. No synthetic cumulative total or unreported actual charge is claimed.

## Current Blockers

Private audio exists, but ASR/source `0.6838 < 9.7` and first/last ASR boundaries are not proven. Public release also lacks upload/checksum evidence, metadata approval, endpoint hash binding, and browser proof.

All B2 variables are missing: `B2_ACCESS_KEY_ID`, `B2_SECRET_ACCESS_KEY`, `B2_BUCKET`, `B2_S3_ENDPOINT`, and `B2_REGION`. All Cloudinary alternatives are missing: `CLOUDINARY_URL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`. Admin credentials are also missing: `EARNALISM_ADMIN_TOKEN`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.

## Upload Continuation

First place the owner-authorized QA evidence where the existing upload hook requires it:

```bash
cp internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_release_gate_evidence.json internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts/auto_premium_qa.json
```

After supplying either the complete B2 credential set or a complete Cloudinary credential set, run the repo upload hook:

```bash
python3 internal/audiobook_lab/scripts/factory_hooks/upload_hook.py \
  --slug book-d19e96859f \
  --run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --catalog-run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --manifest book_import_manifest.json \
  --language ben \
  --title 'গিন্নি' \
  --author 'রবীন্দ্রনাথ ঠাকুর' \
  --max-attempts 1 \
  --fail-closed
```

The hook must produce `upload_manifest.json` with all five local/remote checksums matching. The release-packet builder additionally requires a source-bound `upload_manifest_release_evidence.json`; the raw hook manifest is not sufficient because it does not contain the manuscript SHA-256 or the builder's `upload_checksum_pass` gate.

## Endpoint Continuation

The following repo command performs production admin metadata mutation and is therefore recorded only as a future continuation after separate explicit public-release authorization and after `EARNALISM_ADMIN_TOKEN` or `ADMIN_EMAIL` plus `ADMIN_PASSWORD` is supplied. It was not run:

```bash
python3 internal/audiobook_lab/scripts/factory_hooks/metadata_hook.py \
  --slug book-d19e96859f \
  --run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --catalog-run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --manifest book_import_manifest.json \
  --language ben \
  --title 'গিন্নি' \
  --author 'রবীন্দ্রনাথ ঠাকুর' \
  --max-attempts 1 \
  --fail-closed
```

Only after `metadata_hook_result.json` passes and the endpoint is genuinely live, run the production browser gate:

```bash
python3 internal/audiobook_lab/scripts/factory_hooks/browser_hook.py \
  --slug book-d19e96859f \
  --run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --catalog-run-dir internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts \
  --manifest book_import_manifest.json \
  --language ben \
  --title 'গিন্নি' \
  --author 'রবীন্দ্রনাথ ঠাকুর' \
  --max-attempts 1 \
  --fail-closed
```

No builder-compatible `endpoint_proof.json` exists now. It must be based on real `200/206` endpoint, metadata, range, browser, audio-hash, and manuscript-hash evidence; the current `404` must not be converted into a pass.

## Release Packet Continuation

After source-bound upload evidence and real endpoint proof exist, build the repo's local review-only packet outside the source tree:

```bash
python3 internal/audiobook_lab/scripts/sprint1_release_packet_builder.py \
  --qa-evidence internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_release_gate_evidence.json \
  --upload-manifest internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts/upload_manifest_release_evidence.json \
  --endpoint-proof internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_google_full_tts/endpoint_proof.json \
  --output-dir /private/tmp/earnalism-book-d19e96859f-release-packet \
  --source-root /private/tmp/earnalism-sprint1-paid-20260713-1
```

The builder makes no API, provider, deployment, or live-publication call. It must fail closed until every upload and endpoint gate is supported by evidence.

## Next Exact Command

The cheapest safe next action is non-paid normalization-layer verification. Do not run the upload hook yet:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/bengali_asr_normalization.py --self-test
```
