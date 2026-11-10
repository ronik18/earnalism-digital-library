# 45 Reader candidates: release held

All 45 original front/back web pairs were visually inspected at full and card size. The existing image validator passes all 90 deliveries. The controlled Reader validator and exact rights/component checks pass for the 45 proposed additions; no production publication has occurred.

The 52 previous title bindings and all prior registry entries remain preserved. The addition contains exactly 45 India Reader decisions, no audio package changes, no purchase opening and no rights-held titles. Original canonical chapter files are byte-preserved. Older backend chapter metadata is archived here where its serialization differed; manuscript content is identical.

Six existing launch/bootstrap assertions also pin the former 52-title cohort. The proposed patch explicitly enumerates only the 45 additions (97 total), preserves the previous cohort checks, and invokes exact package/rights validation for each addition. Those fixture changes remain unapplied. The isolated backend run has 360 passing tests and six expected-cohort failures.

Two existing historical assertions still compare the current shared registry to the preceding immutable hash: `test_open_scored_successor_only_exact_record_and_binding` and `test_sredni_private_stage_exact_record_and_actual_transaction`. Their failures remain in place. Automatic approval review rejected the attempted historical assertion edit because redirecting checks to snapshots could weaken a release gate.

`historical-assertion-successor-PROPOSED-NOT-APPLIED.patch` is a proposal only. It preserves the previous historical hash checks against the archived predecessor, then checks the exact successor registry hash. The new independent successor tests also compare archived predecessor bytes to their actual Git parent, verify the exact additive permissions and unchanged previous title bindings, validate all current Reader packages, and deny foreign, audio, untrusted-country and tampered-rights uses.

Do not merge, deploy or record LIVE until the proposed assertion handling has been explicitly reviewed and all required checks pass. Actual trusted-India authenticated Reader access, full ordered pagination, cover serving hashes, anonymous denial and held-title exclusion remain production verification requirements.

Next exact check: `python3 -m unittest scripts.test_catalogue_clearance_registry_successor scripts.test_persisted45_reader_successor -q`.
