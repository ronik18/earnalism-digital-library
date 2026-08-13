# Self-healing contract

Run self-healing only with an explicitly selected local adapter:

```sh
python3 scripts/produce_release.py \
  --manifest /path/to/title-manifest.json \
  --reader-approval /path/to/reader-approval.json \
  --audio-samples-approval /path/to/audio-samples-approval.json \
  --repair-adapter /path/to/repair_adapter.py \
  --self-heal --max-repair-attempts 3
```

The adapter contract is:

```python
def repair(*, manifest, check, strategy, failed_segments, reuse_artifacts):
    return {
        "status": "PASS",
        "evidence_path": "...",
        "evidence_sha256": "...",
        "regenerated_segments": ["..."],
        "reused_artifacts": True,
    }
```

The coordinator retries only strategies marked `TRANSIENT`, in manifest order,
with a maximum of three attempts. It verifies the newly returned evidence hash,
reruns the complete evaluation, and records which segments were regenerated.
Permanent failures, missing evidence, rights ambiguity, and either pending
human gate stop the run. No status is changed to `PASS` by the coordinator alone.
