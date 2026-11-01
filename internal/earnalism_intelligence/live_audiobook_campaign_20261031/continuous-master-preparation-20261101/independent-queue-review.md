# Independent narrow renewal queue review

Read-only basis: canonical ListenerExperienceV2Route.jsx renewCurrentLease/updatePlaybackState/preparePlayback/heartbeat; ListenerExperienceV2.jsx native transitions; reading_pass_service.py renew accounting. No app edits or live operations.

Finding: Route renewCurrentLease captures a requested playback state and appends an operation for every caller to a serial Promise chain. preparePlayback sets buffering and unconditionally enqueues; updatePlaybackState may already have enqueued the same buffering transition; heartbeat appends another snapshot. At3–5s per request, duplicate contiguous snapshots can materially delay the natural segment transition. This is consistent with the reported journal, but does not establish that every stalled second is caused solely by duplicates.

Smallest safe correction: share the Promise for the existing unfinished queue TAIL when requested state, lifecycle generation and session identity are identical, with no intervening distinct state. This applies uniformly to state callbacks, playback admission and heartbeat. Preserve FIFO for every distinct state transition. Clear a tail ref only if the settling operation is still that exact tail. Do not add a global latest-state debounce or permit parallel renewals. Keep token/version/sequence lookup at actual execution time and all native lifecycle ownership checks.

Required invariants and counterexamples:

1. playing→buffering→playing remains three transitions in order. Counterexample: replacing queued buffering with latest playing causes server billing_active to remain true through actual browser waiting. Dropping playing can grant uncharged speech. Backend derives new billing_active from requested state only after settling preceding server-time interval; it has no authoritative browser event timestamps.
2. A request for buffering may share only an unfinished buffering TAIL. Counterexample: buffering inflight, playing queued, buffering requested again must create a NEW buffering operation; sharing the old buffering Promise lets media proceed while a later playing operation is still changing lease state and loses a distinct interval.
3. An admission Promise must acknowledge buffering/media authority for the same session/generation, never merely a preceding playing heartbeat. Never replace await onBeforePlayback with immediate media src/play just because previous lease appears nonexpired.
4. Keep renewals serialized; obtain latest lease version/token and increment sequence when each operation runs. Counterexample: taking version/sequence at enqueue time makes both jobs use the same sequence/version, potentially yielding conflict/idempotency mismatch or replay.
5. Stop/unmount/slug change must invalidate queued work before settlement. A late success cannot restore lease, source or playback. A failed shared renewal rejects all admission waiters and triggers existing fail-closed containment once; do not silently absorb a rejection and allow source transition.
6. Heartbeats may share contiguous equal-state pending work; they must not create an ever-growing redundant queue. They must not suppress a required distinct state transition or permanently stop extending an otherwise healthy lease.
7. Keep8s lease-request and15s terminal-request timeouts intact unless separately justified. Removing timeouts or increasing beyond lease headroom hides liveness defects rather than fixing them.
8. Existing native intent cancellation must survive. Separately, handleEnded currently increments playbackIntentRef but its asynchronous source-switch callback checks node identity/connectivity without checking captured intent. If proposed patch touches this path, require pause/Stop/unmount while admission pending to prevent a late next-segment source switch/resume. Do not expand the queue correction into unrelated billing/backend changes.
9. Tail-only deduplication cannot guarantee zero-delay joins. One genuine required buffering renewal still costs one RTT; rapid distinct native state oscillations still legitimately remain queued. Do not claim seamless transitions or perfect timing from a faster unit test. Current observed source timing/lease safety must remain truthful.

Focused composed test evidence required (route+real Listener, delayed lease mock; not only isolated component mocks):

- Deferred buffering renew plus duplicate preparation and heartbeat produces one request and one shared outcome, then natural next-segment source/play proceeds after ack.
- playing/buffering/playing/buffering rapid sequence retains order, increasing sequences and latest version/token; later buffering cannot share earlier inflight buffering across playing.
- Full natural ended→renew→metadata→playing with3–5s controlled response delay; no false instantaneous UIzero requirement.
- Pause,Stop and unmount during delayed shared admission block later src/play; failed shared renew does not revive admission; End is not held behind stale renewal queue.
- Timer beyond10s with pending equal-state renewal creates no duplicate backlog; once it finishes, next heartbeat still renews.

Billing limitation: Client coalescing removes redundant identical state jobs, not the existing server receipt-time lag in charging transitions. Do not claim exact audio-event-time billing fairness based only on wallet delta or this patch. Preserve prior fraction/carry semantics and scope existing automated and real evidence separately.

Action: ask implementation lane to use tail-only state/session/generation Promise sharing; independently review its concrete diff and composed delayed tests before root integrates. No new live start, allocation or synthesis is authorized by this report.
