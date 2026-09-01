# Risk register and approval boundaries

Redis plan, eviction policy, replica count, region, Railway topology, storage provider, and billing tier remain owner-only decisions.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| unsafe pickle deserialization | HIGH; mitigation: safe codec/key-version migration | risk-register.json |
| stale authorization | HIGH; mitigation: precise entitlement invalidation | risk-register.json |
| cache stampede | HIGH; mitigation: selected cross-replica singleflight | risk-register.json |
| large-file memory/event-loop pressure | HIGH; mitigation: measure and ensure upstream async/cancellation behavior | risk-register.json |
| Redis memory/eviction mismatch | HIGH; mitigation: live capacity baseline | risk-register.json |
| cross-tenant key collision | MEDIUM; mitigation: uniform schema version and identity contract | risk-register.json |
| Range/signed URL/object outage/PDF uncertainty/workflow conflict/metrics gap | MEDIUM; mitigation: characterization tests and serial release | risk-register.json |

The A0.1 audit found historic duplicate publication-packet checksum assertions and obsolete public-asset test expectations. They are governed by the baseline regression ledger; neither changes controlled-publication truth, authorization, nor the production release gate.
