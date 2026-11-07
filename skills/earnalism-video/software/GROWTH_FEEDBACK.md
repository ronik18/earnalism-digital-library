# Evidence-based growth feedback

Use for an authorized analytics audit or a planned content experiment. This is an optional improvement loop, not a new release gate, publishing permission or scheduled automation. Preserve factual, graphical, caption, rights, voice/listening and delivery standards and the one consolidated final release decision.

## Capture before interpreting

- Use existing authorized native analytics or owner-provided exports. Do not buy analytics, connect new accounts, change visibility, post test variants or disclose private data to another service without the relevant authority.
- Timestamp each snapshot with timezone, account/channel, video ID, first **public** time, capture time, native report dates/window label, duration, format, traffic source, follower/subscriber count at publication if known, and evidence path/export. Keep unknown values `null`, not zero.
- Preserve platform labels, numerator, denominator, units and definition/version date. YouTube Shorts starts/replays and engaged views are different measures; use the current definitions. Instagram views/plays can include replays and are not unique reach. Record any changed definition before joining historical series.
- Native “First 24 hours” is not proof of 24 public hours. In the verified introduction report, its displayed Oct31–Nov1 window began before the Nov1 public GO LIVE receipt, following a private draft. Validate native window origin against the first-public receipt; quarantine pre-public/QA exposure. Do not label that report a public launch result or reconstruct a missing public-only total.
- Separate ordinary/public, private QA, paid/boosted, Trial Reels and any cross-platform distribution. A Trial Reel reaches non-followers: it is not private and is not a randomized control. Retain the original records and confounders.
- Keep **viewers ≠ reach**, **views ≠ engaged views**, **subscriber/follower net change ≠ gained**, and **shares ≠ DM sends** unless the native field explicitly measures sends. Never backfill a missing denominator from a similar-looking field.
- Bind scope to **each widget**, not merely the selected page date. Verified YouTube pages show a Since-published headline beside a Since-uploaded lifetime retention card with different AVD/choice values. Preserve both observations, their processing notices and native origins; do not pick the larger value or combine a numerator from one with a denominator from the other. The visible table-column order can differ from its metric-picker/query order; extract actual headers.
- Missing public-time/window-origin evidence means unknown pre-public overlap, not `false`. When available, retain the interval between the authorized public-change action and successful readback; a later verification timestamp or a date-only label is not an exact first-public time. Record precision. Contradictory reported ages or fixed-age endpoints prevent a matched comparison; they do not erase the raw observation.
- Reading native Insights can autoplay a preview. Capture counters before deliberate playback, avoid repeated public QA, and record any incidental playback. A read-only audit does not certify counters free of operator activity. Preserve unresolved replay/scope/processing anomalies rather than declare them organic successes or automatically invalid plays.

## Native outcomes and fair comparisons

|Surface|Choose a primary outcome for this test|Diagnostic and guardrail measures|
|---|---|---|
|Instagram Reel|Follows per reach, shares per reach, or watch seconds according to the question|Unique/non-follower reach, saves per reach, actual retention/skip curve, profile actions, substantive responses|
|YouTube Short|Engaged viewing, stayed-to-watch or subscribers gained per engaged view according to the question|Raw starts separately, average view duration, retention, traffic source, related-video journey where observable|
|YouTube landscape|Watch time per registered thumbnail impression for packaging when native data supports it; otherwise one stated native outcome|CTR within the same impression surface/source, average view duration, retention, subscribers gained, next-video/returning audience where available|

- Report exact counts alongside rates: for example, 2 follows/200 reached, not only 1%. A zero denominator yields unknown. Account-level profile conversion is a period funnel; do not attribute all profile follows to one Reel without a native attribution field.
- Watch seconds per registered thumbnail impression requires actual **watch time from those impressions**. Total all-source watch time or Shorts-feed viewing cannot substitute. Likewise, a Shorts end-screen click rate is not its Related-video click rate. Unavailable related-video movement remains unknown.
- Average watch seconds ÷ duration is a descriptive, potentially replay-inclusive ratio. It may exceed 100%; it is not completion probability. Completion requires a native end-retention/completion measure with its own denominator.
- Match platform and format first, then public age/window, duration band, topic/learning job, traffic/distribution source and audience size at publication. Use actual context, not just convenient bands. Never rank a 3-second ident against a full explanation as a creative winner.
- Prefer the account's mature, comparable-post median and spread. With only a few posts, list each observation rather than inventing a stable benchmark. Pooled studies are priors, not Earnalism targets.
- A fresh capture can contain stale audience, retention or Earn counters. Keep each displayed cutoff/processing notice; do not reconcile incompatible rollups by arithmetic or infer best posting hours from an unavailable heatmap. Current subscriber totals, historical eligibility counters and observed revenue are separate measures.
- Keep discovery, retention and conversion distinct. Extra reach may dilute follows per reach while increasing total follows; higher completion may mean less useful watch time on a shorter video. Show both absolute outcomes and rate tradeoffs.

## Predeclare one controlled test

Use [the experiment template](templates/growth-experiment.template.json); fill only what the question needs before exposure.

1. State the viewer, learning value and hypothesis. Choose one platform/surface and one principal change: opening reveal, title/thumbnail, explanatory length, specific follow/next-lesson promise, or posting window.
2. Declare the primary metric's native name, numerator, denominator/units, report scope and expected direction. Define a practically worthwhile absolute/rate difference and its cost rationale; do not borrow a universal “viral” threshold.
3. Keep content/factual quality and other variables as stable as possible. Use native randomized packaging tests where available. Otherwise balance/rotate comparable topics and windows and call it a quasi-experiment; two different episodes are not a clean A/B test.
4. Set an effort/time budget, stopping/review point and guardrails: no factual/accessibility loss, intelligibility harm, misleading packaging or unauthorized spend. Preserve accepted audio unless the task authorizes changing it.
5. Plan sufficient observations using the baseline, practical effect and uncertainty. There is no universal required view count or post count. Posts/audiences, not every replay, are the independent experimental units; overlapping audiences and repeat views weaken independence.
6. Record controls, actual deviations, collaborations, reposts, boosts, account changes and seasonal/news effects. Do not delete weak results or stop the first time a noisy metric looks favorable.

## Review rhythm without an extra approval loop

|When new data is available|Purpose|Decision scope|
|---|---|---|
|About 24 and 72 public hours|Find delivery/eligibility defects and early drop-off or packaging signals|Diagnostic only; label estimates/processing delay. Never infer final performance from realtime views alone.|
|7 matched public days|Primary planned content comparison|Counts, rates, watch/retention and effort; immature videos wait for the same age.|
|28 matched public days|Delayed distribution, returning audience and conversion follow-up|Check whether early direction persisted and whether a search-driven lesson matured differently.|
|Weekly, if work/data exists|Choose the next single useful test and investigate real failures|Short local decision note, not a new form or release blocker.|
|Every four weeks or material platform/definition change|Adopt, revise, retire or retain as inconclusive|Update a reusable rule only when evidence warrants it; leave defaults alone otherwise.|

These are review intervals, not promises to poll services or create automations. A review may reuse valid unchanged snapshots; do not require every optional metric before releasing an otherwise qualified video.

On a due review, update the project's compact current-growth pointer with the dated evidence, applicable platform/surface, current decision, main test and next review trigger. A conditional experiment is not an adopted default. An adopted rule retains its evidence level, practical effect, guardrails, valid scope and revisit/retirement condition in the existing decision record. At the next episode, apply only relevant current decisions; unknown metrics remain unknown and normal production continues within its existing permissions.

## Interpret and update

- Tag each finding: **LOCAL_VERIFIED**, **OFFICIAL_GUIDANCE**, **OBSERVATIONAL_CORRELATION**, **CREATOR_CASE**, or **TEST_HYPOTHESIS**. Include source date, retrieval date, applicability and important limitations. An algorithm explanation supports a mechanism, not a promised lift.
- Report baseline and candidate counts/rates, absolute difference and relative change. If the baseline is zero, relative lift is undefined; report the absolute change. Distinguish percentage points from percent. Do not average incompatible denominators.
- Show uncertainty appropriate to design: sparse conversion counts, confidence/credible intervals where justified, observed spread, matched-pair direction and missing data. With tiny samples, use “directional” or “inconclusive,” not “statistically proven.” Do not infer causality from before/after analytics or correlated creator success.
- **Adopt provisionally:** improvement is practically worthwhile against predeclared criteria, survives independent replication across comparable posts/time blocks, and respects quality/cost guardrails. A conclusive native randomized result can select packaging for that asset; promotion into a future-video default needs evidence beyond one asset. Record scope and revisit date; a winner on Reels is not automatically a Shorts rule.
- **Revise:** evidence is mixed, a confounder dominates, conversion and reach conflict, or the learning outcome suffers. Change one suspected cause in the next test.
- **Retire:** repeated comparable evidence shows no worthwhile benefit within the effort budget, replicated harm appears, or current official guidance/definitions invalidate the recommendation. Preserve history and the reason.
- **Inconclusive:** exposure/events are too sparse, windows are incompatible, a control is missing, or processing/access gaps prevent the question being answered. Do not silently convert unknown into failure or approval.

## Revenue is an observed business outcome

Use native eligibility and qualified-view/watch-hour definitions for monetization, not raw Shorts starts or an arbitrary follower milestone. Verify the actual account, country, program and current terms before assuming access. Keep revenue, attributable platform visits/conversions and production/compute costs separate. Calculate profit only from observed amounts and a stated attribution window; never invent RPM, customer lifetime value or expected earnings. Millions/billions of views and substantial growth are goals, not acceptance promises.

## Optional descriptive helper

`python3 video_studio/growth_metrics.py analyze SNAPSHOT.json --output NEW_REPORT.json` can calculate supported rates and conservative comparison checks. The [optional observation template](templates/growth-observation.template.json) supplies a capture shape; fill only observed fields and retain individual widget scope/cutoff. Keep raw dated evidence alongside it. The helper cannot authenticate a screenshot, recover missing reach, certify public-only window origin, prove causality, determine a winner, authorize publication or forecast revenue. The experiment template is a planning record, not automatically a valid helper input. Preserve unsupported native fields in raw evidence; never coerce a net value into a gained count to satisfy the helper.
