# Governed release intelligence

The release coordinator may learn only from verified operational outcomes. It
can reorder already-declared technical repair strategies using successful
history, measured cost, and measured latency. It cannot add strategies, lower
thresholds, change rights, approve a human gate, or infer production success.

The optional learning ledger contains strategy IDs and operational metrics only;
it does not store manuscript text, credentials, approval evidence, or media.
Malformed rows are ignored. A strategy is eligible only when it is explicitly
marked `TRANSIENT`, belongs to an allowed technical check, reuses successful
artifacts, and returns new checksum-verified evidence.
