# Automated editorial release policy

New internal release jobs select `editorial_release_policy:
"automated-editorial-2026-11-11"`. The backend release QA receipt uses the same
field inside `qa`. Selection removes routine Reader-preview and listening-sample
approval packets and numerical human listening/confidence floors. It does not
invent a human review, score, owner YES, or permission to publish.

The evaluator requires an existing complete master file with its SHA-256,
source SHA-256, immutable package version, descriptor, duration and voice/model
identity. Four pilots are not a complete audiobook. Human/sample checks are
reported as `NOT_APPLICABLE`, never `PASS`. Generation admission and its original
provider, approval, transfer, attempt and spending limits are unchanged.

All existing applicable objective checks still apply. New-policy evaluation and
promotion additionally require checksum-verified evidence for `recording_rights`,
`voice_model_rights`, `music_rights`, `protected_access` and `accounting`. Silence
may be recorded truthfully in music evidence. Unsupported policy values fail
closed. Explicit publication intent and existing title holds remain effective.
Unconfirmed heuristic warnings stay advisory; confirmed defects, missing required
acceptance and failed access/charging checks remain blocking. Optional background
analysis may not silently incur inference, upload or credit costs.

For script jobs, each automated PASS references a retained JSON file by path and
SHA-256. Its schema is `earnalism.automated_release_check.v1`, its `check` matches
the gate name, and its binding includes slug, audio/manuscript checksums, package,
descriptor, model, voice and duration. Both evaluation and promotion reread and
verify the file; changing a candidate cannot reuse stale evidence. The coordinator
carries the evaluated artifact root so promotion also rechecks the full master.
Verified synchronization NOT_APPLICABLE retains its existing separate source-bound
contract. For the authenticated backend QA route, `automated_acceptance` contains
the five additional receipts with retained evidence digests and exact server-
selected slug/audio/manuscript/attempt bindings. The backend never reads paths
supplied in a QA request; its existing rights and object-storage verification is
unchanged. These are actual operator evidence, never fabricated receipts.

Jobs without this explicit policy retain their original review contract. Keep
historical listening records, raw findings and owner receipts unchanged. In
particular, preserve `1f470e8c` and its identical variants as historical inputs;
do not cherry-pick their owner-YES requirement into the new automated mode.
No existing title or public allowlist is activated by this local policy change.
Bicharak remains on owner hold.

## Paired-playback reconciliation

This policy changes editorial review only. The separately prepared paired
acceptance policy still allows its original one start, maximum 40 wallet seconds,
15-minute validity, exact member/authentication/package binding and one-shot
installation. It cannot replace a prior cap, grant or receipt, refresh an expired
attempt, reset original120 lineage, or manufacture wallet/ledger settlement.
The admission fence, terminal settlement and unknown-commit no-replay rules are
unchanged. Local synthetic tests do not install the cap or prove paid playback.

## Local work versus the ended Integration chat

The existing Integration chat ended with a platform safety rejection. Do not
resubmit it, alter safeguards, impersonate clearance or move its rejected
operation to another execution path. A read-only status or preservation action
is not a retry. Do not infer a blanket filesystem ban from an unexplained chat
error. The owner's later explicit local-only instruction permits this narrowly
scoped source reconciliation and synthetic tests in the canonical checkout,
preserving the dirty preimage. It does not authorize a new chat, push, merge,
deployment, production data access, playback, provider request or counter reset.

Only source changes and offline evidence are prepared here. Normal protected
integration/review and separately applicable runtime authority remain necessary
before any commit/push/deployment or LIVE assertion is carried out.
