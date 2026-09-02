# A5 local audio benchmark

Synthetic local bodies were read at 1 MiB and 3,145,745 bytes with concurrency 1, 5, and 20. Every read was at most 1,048,576 bytes and every body closed. The slow-body heartbeat remained below 20 ms while reads were on the async thread boundary. Local elapsed measurements are explicitly `INCONCLUSIVE_LOCAL_NOISE`; they are not production latency or cost evidence. Metadata caching was not activated, so no HEAD-call reduction is claimed.
