# Two-gate release coordinator

`scripts/produce_release.py` is the single deterministic release decision
front door for a title.

Human input is limited to two packets:

1. `reader-approval.json`: approval of the rendered reader sample and exact
   manuscript/preview hashes.
2. `audio-profile-approval.json`: approval of the exact TTS model, voice, and
   profile hash.

Rights, source, manuscript, artifact, synchronization, checksum, staging,
browser, and production checks are automated. They must provide explicit
`PASS` results; missing or ambiguous values remain `BLOCKED`. No provider,
storage, or deployment action is performed by this evaluator.

Example:

```sh
python3 scripts/produce_release.py \
  --manifest /path/to/title-manifest.json \
  --reader-approval /path/to/reader-approval.json \
  --audio-profile-approval /path/to/audio-profile-approval.json \
  --root /path/to/repository \
  --state-file /tmp/title-release-status.json
```

The command returns `LIVE` only when both human packets match the exact hashes
and every automated check is explicitly `PASS`. It never treats public
availability as rights permission and never fabricates a quality or deployment
result.
