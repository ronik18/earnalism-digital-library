# A3 observability overhead

PASS. Metrics are process-local, use six fixed policy IDs, fixed operation/result names, and fixed latency/size buckets. With 100 warmups and 500 synthetic record samples, median recording cost was 1,292 ns, p95 was 1,375 ns, and maximum was 12,500 ns. Focused operations verified cache correctness with metrics enabled. This is local bounded-state evidence, not a production latency claim.
