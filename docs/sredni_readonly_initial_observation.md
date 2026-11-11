# Initial own-metadata observation

The original Sredni permission authorizes a bounded abort-only initial observation
before release qualification. The operator previously required the complete
startup/recovery write receipt even for that observation, creating a readiness
cycle. This source change separates the two admissions; it grants no new access.

For `observe` only, a private source receipt may use
`ACTUAL_ATTESTED_SOURCE_READONLY_INITIAL_OBSERVATION`. It still binds the actual
serving commit, measured runtime, source files, frozen descriptor/package, current
member and original120 preservation. Its separately pinned execution receipt must
use `SREDNI_OWN_MEMBER_METADATA_READ_ONLY`, `observation_only: true`, and
`observer_source_files_sha256` for the reviewed local observer. The running
application and observer versions are distinct, explicit evidence; neither is
invented or relabelled as the other.

Every owner/member/journal/profile, freshness, expiry and one-shot intent check
remains. The existing observer validates the candidate's India rights, performs
only its fixed own-member/Sredni reads and aborts the snapshot transaction. It
creates no namespace, index, grant, wallet/ledger change, startup observation or
available-credit claim. Keep the existing 50-second inner/60-second outer bound.
An existing attempted operation is not permission to choose another ID and retry.

Prepare-namespace, provision and close retain the original fully qualified serving
source, startup, recovery and private-stage requirements. The new read-only source
mode cannot authorize any of those actions or paid playback. An initial result
does not clear release gates. Do not fabricate missing source/identity/execution
receipts to make the CLI run.

This does not reconcile the original pending native component, implement the
frontend limit amendment, lift Bicharak's hold, renew consumed observations or
authorize allocation/synthesis. Those constraints remain independently effective.
