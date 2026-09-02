# Future customer PDF delivery contract

This is a design boundary only. A future approved PDF product must use durable storage, authorize before metadata or bytes, and stream without complete backend buffering. It must define safe response headers, conditional semantics, cancellation and frontend cleanup, tenant/resource isolation, replacement handling, security tests, memory/load tests, and explicit rollout approval.

Redis may never store PDF bytes, fragments, data URIs, file handles, generators, or response objects. A bounded metadata cache is a future conditional decision only after measured demand and exact invalidation evidence. A6 chooses neither a route nor a storage provider.
