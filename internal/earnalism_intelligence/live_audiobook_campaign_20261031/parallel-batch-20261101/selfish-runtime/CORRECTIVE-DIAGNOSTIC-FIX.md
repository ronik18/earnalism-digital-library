# Corrective driver diagnosis and minimal procedural correction

The executed driver is preserved verbatim in CORRECTIVE-DRIVER-EXECUTED.js. It contains no credentials, identity or balance values. This is an execution record, not permission to run it again.

Observed: Error of unknown message, elapsed4.345seconds, observations=[], normal end not confirmed. Exact failure location is bounded to normal Authorize click, its following AX read, waiting for Play, following AX read, chapter click or chapter AX read. The first scripted Play call occurs only AFTER the first observation append; therefore this driver never reached scripted Play. It is NOT proven that the Authorize request was sent, nor proven absent. Reservation is not an actual start count. The outcome stays uncertain and must not be silently replayed.

The catch discarded e.message and no failing-step variable existed. The finally block read normal network events but did not persist them before closing the owned tab. That lost request-count evidence. After close, documented CDP rejects access to that tab; no alternate/session-storage/credential workaround was used. A new read-only normal preauthorization page subsequently confirms exact owner credit delta0 and no start request in that read-only page, but does not establish whether the previous normal start was dispatched or settled.

Readonly locator counts on the normal UI: exact Authorize1, original chapter regex1, flexible chapter regex1. No evidence supports changing the locator string or blaming a missing chapter control. The attempted extra offline accessible-name diagnostic could not run because dom-accessibility-api is unavailable; nothing was installed. Original three restart/progress tests passed and their source is preserved unchanged.

Minimal diagnostics correction BEFORE any root-authorized future execution:
1. Persist a stage/checkpoint before EVERY awaited normal UI operation, including before-click, after-click, play-wait, chapter-click and before-Play. Keep these outer-scope bindings available for postflight.
2. Preserve Error.name and the scrubbed first message line plus explicit stage/locator. Mask bearer/token/cookie/query values, emails and balance display values; never dump raw AX/account state or headers. Do not reduce all errors to a generic category.
3. Passively record and persist normal Network.requestWillBeSent, responseReceived and loadingFailed events during each stage. Keep only same-origin paths without query strings, method/status/request ID/timestamp. Never headers, credentials or raw profile/lease bodies. Bind an actual start count only to the observed normal POST; count uncertain starts as consumed, never absent.
4. On normal start200, bind its session privately and persist the redacted request receipt IMMEDIATELY before further chapter/player work. On normal end200, persist ended/status and derived owner delta before closing. If deadline requires early close, save available event summary first within the deadline; record gaps honestly.
5. Preserve the70second owned-tab safety deadline. Stop/settle only a known owned session; no takeover/transfer/third start under the old internal instruction. Root must adjudicate any continuation after inspecting the evidence and unchanged cumulative120credit owner scope.

No app patch or redeployment is justified by this diagnostic failure. No new session was run to test this correction.
