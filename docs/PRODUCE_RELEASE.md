# Two-gate release coordinator

`scripts/produce_release.py` is the single deterministic release decision
front door for a title.

Human input is limited to two packets:

1. `reader-approval.json`: approval of the conversation-rendered reader preview,
   bound to the exact manuscript and preview hashes.
2. `audio-samples-approval.json`: approval of six or seven playable conversation
   samples, bound to every sample/source hash, the exact model and voice, all
   seven listening scores, confidence, fatal-flag result, and explicit public
   release intent.

Rights, source, sanitization, manuscript, reader/index/pagination, cover,
full-audio fidelity, boundary/order, technical audio, synchronization,
checksums, storage, cache/service-worker safety, CI/build, staging, emulated
device matrix, browser, and production checks are automated. Each must provide
checksum-bound evidence and an explicit `PASS`; missing or ambiguous values
remain `BLOCKED`.

Example:

```sh
python3 scripts/produce_release.py \
  --manifest /path/to/title-manifest.json \
  --reader-approval /path/to/reader-approval.json \
  --audio-samples-approval /path/to/audio-samples-approval.json \
  --root /path/to/repository \
  --state-file /tmp/title-release-status.json
```

That evaluation returns `READY_FOR_GO_LIVE`, never `LIVE`. To continue without
a third per-title human prompt, provide the private staging receipt and enable
automatic promotion:

```sh
python3 scripts/produce_release.py \
  --manifest /path/to/title-manifest.json \
  --reader-approval /path/to/reader-approval.json \
  --audio-samples-approval /path/to/audio-samples-approval.json \
  --staging-receipt /path/to/staging_receipt.json \
  --auto-go-live \
  --root /path/to/repository
```

The persistent production environment guard remains an operational kill switch.
`LIVE` is returned only after the promotion endpoint proves the public book API,
publication status, audio and byte-range endpoints, browser playback,
mobile reader/audio journeys, resume recovery, cache-control, and absence of a
stale audio URL. The coordinator never treats public availability as rights
permission or fabricates quality/deployment truth.
