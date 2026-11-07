> Release policy: [GO_LIVE.md](GO_LIVE.md) governs. Research, variant and growth tasks are optional; one final candidate decision covers primary checks. Older wording does not add approval steps.

# Mandatory factual and graphical release qualification

This standard applies to every future episode and every release candidate. There is no episode flag, self-score, auto-approval prompt or “low risk” exception that turns a missing or failed factual/graphical check into PASS. These are the detailed evidence requirements for the existing factual and audiovisual reviews, not a requirement to buy a new service or hire a second reviewer. Tests and source research may be automated; human confirmation and listening judgments must be real. Perfection cannot be guaranteed by software.

## Automatic workflow behavior

`prepare` creates a pending strict review; complete `render`, `render-frozen` and `remix` create a fresh plan bound to the finished delivery manifest. They automatically extract the required full-resolution frames from the final landscape and captioned-portrait MP4s into `quality-evidence/`, attach media/time/file hashes and leave decisions PENDING. They never transfer approvals. `studio.py check` always invokes the strict validator in addition to the existing rights, narration, captions, listening, technical and delivery gates. `improvement.py` reports an incomplete strict review as RED_HOLD. Review history is retained when a pending review is reset.

The review is `strict-quality-review.json`, excluded from the delivery manifest to avoid a hash cycle. The plan is derived from the exact `episode.json` and `props.json`, so changing claims, scene timing, anchors or format invalidates old evidence even if somebody rebinds only the manifest. Individual frame reviews bind their required time and actual delivery MP4 hash. Referenced evidence files are checked by hash and must be inside the candidate folder.

```sh
python3 video_studio/strict_quality.py plan /absolute/candidate
python3 video_studio/strict_quality.py init /absolute/candidate
python3 video_studio/strict_quality.py capture /absolute/candidate
python3 video_studio/strict_quality.py check /absolute/candidate
```

Use `init` only for an older candidate that has no review: it refuses to overwrite. New standard renders initialize and capture automatically. An extraction failure cannot mark the set complete; preserve and inspect a partial set before an explicitly scoped retry. Never overwrite existing evidence. Captured images and complete watch logs are evidence for review, not machine-issued factual or aesthetic approval. Work from the user-selected project; the same tools are bundled under the installed skill's `software/`. Never modify prior episode masters to make them pass a new standard.

## Before narration: verify every claim

Create a source ledger for each spoken sentence. Read authoritative primary sources; search snippets or plausible recall are insufficient. Record the exact source URL, retrieval date, hashed source notes/capture, supported scope and verification reason. Classify questions, metaphors and promotional language explicitly rather than presenting them as measured facts. Check averages versus instantaneous values, units, denominators, conditions, exceptions, causal mechanisms, uncertainty and date sensitivity. Corroborate surprising or consequential claims with an independent authoritative source; resolve contradictions before scripting or remove/qualify the claim.

Inventory the visual claims separately for every scene: labels, fractions/percentages, diagrams, arrows, axes, color meanings, spatial relationships, orientation and model assumptions. A sourced script does not make an inaccurate graphic correct. Test the actual topic model, numerical boundaries and all displayed states; inspect both increasing and decreasing quantities and the edges of conditional labels. Do not relabel the Moon renderer to make a different topic.

Each source and claim needs a PASS finding with real evidence. The factual reviewer confirms the inventory is complete and records no unresolved findings. A URL or a `primary_or_authoritative` field is not itself proof of truth; the reviewer must read and assess the evidence. Never manufacture approval fields.

## After rendering: inspect animation over time

Review both independently composed formats. The version-2 frame plan includes every scene's entry, hold and exit, before/during/after samples around every actual narration anchor, and the brand ending's first, middle and final frames in both formats. Ending timestamps follow the renderer's rounded frame boundary, rather than the unquantized speech duration. This catches intermediate-state overlaps that a static quarter hold missed. Inspect actual rendered frames, not only source code or a storyboard. Bind each frame reference to the intended time and current landscape/captioned-portrait file.

Mandatory checks in each format cover:

- Topic-model accuracy and consistency between representations.
- Disk/object/label clearance, units, readable hierarchy and mobile label sizes.
- Captions separate from essential graphics, source/assumption notices and controls.
- Temporal continuity, clipping, transitions, phase/state predicates and visual callbacks.
- Exact full website-header logo-and-text watermark identity and aspect ratio, readable quiet placement, and full rectangular clearance from content and platform overlays. Preserve the approved end ident.
- Source access below the player and brief essential model/orientation context in relevant scenes; no persistent source footer or decorative progress strip.
- Fullscreen fit, reopening and seeking, caption loading/gaps, and Replay after the real ending.

The checklist needs evidence from meaningful topic-specific tests and actual viewing. Play the full final landscape and captioned Shorts, including the brand ending, without skipping. Record device, duration and current media hash. Required frame coverage and full-playback logs complement one another; neither replaces a listening review. Narrow desktop fixtures are not physical-phone tests. Preserve intentional silences and selected audio during visual fixes; altered audio needs fresh alignment and captions.

A graphical reviewer confirms both format reviews are complete, all required samples/checks passed and no findings remain. FAIL, PENDING, missing cases, blank evidence, stale hashes, incomplete playback and unresolved findings all block release. A machine can validate coverage and bindings; it cannot certify aesthetic excellence, human understanding or factual truth from a checkbox.

## Improve without drifting

For each demonstrated defect, preserve its timecode/frame and source hashes, fix the root cause, add a meaningful regression, exercise the fix on actual media, and update the installed software and focused guidance. Prefer one coherent correction over repeated speculative variants. Keep frozen source media and previous findings. An approval tied to an old edition never approves a revision. Finish with the existing strict release gate and the actual website/storage integration checks; a local player is private review, not GO LIVE.

Live explanatory overlays require independent synchronization checks before, during and after each visual transition. HTML reading keys are outside rendered MP4s: clear a quarter/half comparison when the disk starts changing, not only at the next spoken anchor. Test contiguous time ranges and exact transition boundaries; final-frame extraction alone cannot establish this.

Moving objects must clear labels along their complete swept path, including source-view labels outside the destination card. Test every animation frame against reserved label rectangles, then inspect actual before/during/after frames in each independently composed format. A collision-free final hold does not clear a transition.

Narrow landscape review must offer synchronized, legible companion label cards outside both the raster picture and caption rail. Limit the comparison to two essential cards; move sunlight/transition context into a short secondary line. Preserve actual scene/anchor timing, hide observer labels before the view arrives, clear comparisons during transitions, and update only when the displayed state changes to avoid flicker. Test narrow widths and fullscreen; this companion does not certify embedded MP4 labels at physical-phone size.

Version-2 plans deliberately invalidate older plan bindings. The current seven-scene Moon edition requires 102 samples including six ending samples; future episode counts derive from their own scenes and anchors. An old 96-frame review is not silently upgraded or approved. Keep historical media and sidecars intact; create and capture a new pending review through the normal candidate workflow before qualification.

Audience-led graphical qualification also requires `packaging_truth_and_readability` and `opening_visual_payoff` in both format checklists. Inspect the actual chosen covers and small readbacks against selected title promises, plus meaningful first-frame subject, early consequential visual event and payoff timing. Schema/image checks cannot supply those judgments. These additional checklist keys invalidate older review bindings even though the current Moon plan still has 102 frame samples. Audience and packaging delivery inputs remain manifest-bound; mutable publication observations stay outside that manifest.

New audience-plan v2 candidates add actual first-subject and before/during/after early-payoff checkpoints in both formats. Their count derives from the episode plan; the historical Moon 102-frame plan is not a permanent limit. Object-label clearance, scene question/answer continuity, cognitive reading load and title/payoff alignment are explicit human graphical checks. Declared reading/reveal times must fit the actual audio-derived scene durations; never silently stretch accepted speech. New learning qualification uses current topic-specific study questions and critical-explanation checks rather than a universal quarter-Moon case.
