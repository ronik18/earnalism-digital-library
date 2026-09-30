# Historical unavailable-title raw HTML recovery — 2026-09-30

Base: approved main `0eabe7685941488b3f7d584359afbc47334811e2`, preserving PR #476's UI/route changes and the workflow fixes through PR #485.

## Verified behavior and intended preservation

Production run 36760854536 deployed the approved PR #476 revision successfully; its removed-route canary passed but the static SEO canary failed. An independent complete raw-HTML check at 2026-09-30T20:04:08.203532+00:00 passed all 19 other checked routes and reproduced failures for `/book/dracula` and `/reader/dracula`: HTTP 200 plus the generic Home snapshot's released-edition access copy. Additional Selfish Giant Reader/Listener responses reproduce that generic snapshot; two other bounded requests timed out and are not relabelled as semantic observations.

PR #476 and its existing direct-route/component tests explicitly approve meaningful historical unavailable-title pages, with no title data fetches, reading session or audio. Their HTTP 200 continuity is correct. Preserve the approved UI and route mappings, source/manuscript, protected `451 RELEASE_RIGHTS_DENIED` boundary, current commerce and all accepted release authority. Correct the raw pre-hydration snapshot rather than reverting approved continuity or pretending that the historical route released an edition.

## Narrow correction and guards

Generate six public-safe Book/Reader/Listener snapshots for Dracula and The Selfish Giant, classified RELEASE_HELD and noindex/nofollow. They expose only title identity, the existing truthful unavailable copy, Library recovery and title inquiry links. Add exact and trailing-slash snapshot rewrites before the retained original app fallbacks. Unknown title routes retain their dynamic 404 policy; existing released snapshots are unchanged.

Both the build verifier and production raw-HTML canary require the historical title's exact identity/canonical, noindex/nofollow, unavailable access copy and recovery-only links, rejecting released-edition/preview/Home copy, Book/Audiobook publication data, raw audio, players and access controls. Activation of either title also requires its unavailable-route policy to be reconciled; this repair grants no rights or publication authorization.

Local checks: 16 canary/generator/negative-tampering tests and 27 existing frontend direct-route/unavailable/release tests passed. The actual generator builds 43 snapshots (37 existing plus six held recovery pages); its verifier and independent Python HTML inspection agree. Mandatory normal regression CI now executes these tests. YAML/shell/Python/JSON/module syntax and patch integrity were checked. No product JSX, artwork, title package, launch allowlist or accepted decision bytes changed.

Next: require fresh exact-head CI and protected merge, deploy only merged main through the normal frontend pipeline, then inspect full production route/static-SEO/regression canaries. Keep #380 open until its independent live manuscript/release/authenticated acceptance conditions are actually supported. #385 remains owner-deferred, NOT_RUN physical UAT; #477 remains held by genuine package/component/source facts and requires an executed worker assessment.

Next exact command: `gh pr checks <unavailable-snapshot-pr> --repo ronik18/earnalism-digital-library --watch --fail-fast`.


## 2026-09-30 — Executed catalogue assessment and report preservation

PR #485 passed actual hosted UID/bootstrap and receipt tests plus complete regression. Run 36773761003 executed the 20-title worker assessment and passed source/batch-bound completed receipt validation; the physical canonical checkout fixes command startup. The worker proposed checksum-only repairs for five still-held packages (the-art-of-money-getting, bn-031, bn-035, bn-036, bn-041). The controller correctly blocked private generated JSON outputs at the unchanged changed-file scope gate, so focused/full validation and publication did not run. These proposals are not accepted releases and no completed-catalogue claim follows.

Retain known canonical and alternate worker generated JSON directories, plus the exact title-package proposal diff, outside Git as an uploaded artifact before restoring only known historical report snapshots. Reject symlinks, non-report files and tracked alternate source without moving it. Keep package changes in the checkout and preserve the existing scope, immutable accepted decision, rights, territory, audio and full regression gates. Use the controller-provisioned setup-python interpreter for model tests; login PATH selected system Python without dependencies. Three real-Git report-preservation fixtures pass. Rebind both existing exact-source workflow authorities after the intentional Vercel rewrite change; this is source provenance, not visual approval. Seven accepted live and 224 held remain the release truth.

Source fingerprint for the updated Vercel route mappings: `94282c9df97458a814478a2dad75af9a5ad7cfc6734a5ae7de88f012226c72ef`. Fresh exact-head source-bound visual workflow checks remain mandatory.

Next exact command: `gh pr checks <report-preservation-pr> --repo ronik18/earnalism-digital-library --watch --fail-fast`.


## 2026-09-30 — Fresh full-regression snapshot assertion reconciliation

PR #486 hosted permission/archive fixtures and the mandatory snapshot fixtures passed. Full regression run 36776970714 found one latent released-Dracula SEO assertion because that snapshot now exists as the approved unavailable page; 122 other regression tests passed and four were skipped. Retain the positive released-book SEO/schema/canonical checks using accepted A Ghost Story and add unavailable/noindex/no-content assertions for all six historical routes. Do not re-release Dracula, remove its safe page, or disable the regression module. A fresh CRA build is the generator's real production input; reusing an already populated local snapshot root is not fresh build evidence. Require all checks again on the corrected exact head.


## 2026-09-30 — Deployed historical-page repair and worker report ownership

PR #486 merged at cae4d7c8105d14e831e62152403003a8cdad5016 after exact-head protected regression, container, coordination, Auth/Account and editorial checks. The three-browser review and independently downloaded envelope subsequently passed for candidate da340e6f53a6c2e614fb3de0f4f16800c68ead45 (same tree 61e27f91311343ee0a8f0e82f694fb0dcaab00ff). Main regression, actual Vercel deployment (earnalism-oujgqhwpx-sales-8498s-projects.vercel.app, apex alias) and all production route/static-SEO/module canaries passed. Approved product JSX, artwork, manuscript, launch and accepted-decision bytes are unchanged.

Actual campaign 36780560381 executed model commands and 109 applicable tests but correctly failed its incomplete STARTED receipt: default report generation could not overwrite controller-restored files, and three Enchanted April checks depended on /private/tmp/pg16389.txt. Use the explicit private _worker report directory, already covered by the archive guard; do not grant broader permissions or rewrite the approved historical reports. The repository retains the exact official source archive with the required d2d5a31f295361fb742f44729d3de6082cd7bff742a0484cd178731d66ef8370 hash. Use that input for Enchanted April tooling and require all three existing source/cover/private/audio/determinism assertions in normal regression and campaign validation. Those three tests and nine receipt/archive tests pass locally. The new actual-UID read-only-report/worker-owned-output/controller-recovery fixture must pass hosted CI; local UID transition is unavailable. No test is disabled, no new legal/approval fact is invented and no publication follows from dry-run repair plans.


## 2026-09-30 — Prioritize available checksum repairs in a bounded assessment

The last actual worker inspected five external approval/QA holds and changed no package; the earlier completed 20-candidate assessment had already identified five checksum-only proposals. The existing broad deterministic category sorted fewer-blocker approval holds ahead of mechanically repairable exact retained-hash mismatches. Rank exact checksum mismatches first without changing any blocker, accepted record, source or approval field. The five-title limit controls modifications, not an instruction to stop assessing at five held titles. Four tests execute the real selector and retain the 20/5 bounds, live exclusions, stable order and missing-package holds. Require fresh normal CI on the final PR487 head; no no-progress or release conclusion is claimed from this candidate.

## Verified catalogue execution and controller publication boundary

PR #487 merged at 68501c936edf69b5492f662c6a46e89dc12e53d1 after exact-head hosted regression/container/coordination checks passed; merged-main regression also passed. Frontend deployment was correctly skipped for no frontend changes. The existing PR #486 deployed source and production canary evidence remain applicable to unchanged UI.

The next campaign 36785743093 completed a real 20-candidate assessment and all focused/full worker gates, preserving candidate b016ca0b2edfaa25fb5c52b656043a5b21bde431. Artifact 11129479800 SHA-256 eaa40f13fd4c6f082b572b36dee2275b05524cdb2586a814de9da783bd0208ca was independently verified. Proposed blockers are 912 (down seven); 224 titles remain held and seven accepted. No new release or rights decision. PR #488 preserves that proposal and adds a final source-identity guard plus an explicit policy-bound bridge PR handoff. Six new controller evidence fixtures pass locally; fresh exact-head hosted CI and protected merge are still required. #380 release/authenticated acceptance and #477 genuine source/rights/cover/decision gaps remain open. #385 remains owner-deferred NOT_RUN; #347 stays completed.

Controller handoff review additionally exports the actual candidate SHA in its creation step and exercises all three actual PR shell paths with isolated mock GitHub responses. Nine controller fixtures pass locally; normal fresh exact-head CI is mandatory.

## Verified second bounded catalogue pass — 2026-09-30

Campaign 36789262625 succeeded on source main 4905cf7f8fb1c22d28e37e193a436650f01c79ba. The actual receipt records 20 examined titles; worker/controller focused and full regression, exact final source guard, known smoke-report retention and policy-bound bridge handoff all passed. Five additional held titles have exact existing-byte checksum repairs: book-0deb35c750, book-2b9853ec52, book-2ddbed8293, book-2e468c4990, the-student. Candidate a027b349da465f83e574eb99ef270493c119d76c contains only six checksum manifests; proposal blockers 912 to 907, with 224 held, seven accepted and no new rights decision/publication/audio. All three private/controller/handoff artifact digests and the controller/proposal diff identity were independently verified. This is a validated pending candidate, not a merged result or evidence exhaustion. Fresh normal exact-head checks and protected merge remain required. Approved UI, manuscript, source/approval bytes, accepted records and launch controls are unchanged.

## Verified third bounded catalogue pass — 2026-09-30

Campaign 36791115145 succeeded with 20 examined candidates and complete receipt/release/scope/focused/full-regression/final-source/evidence-retention gates. Exact existing-byte checksum repairs for carmilla, eyesore-chokher-bali, hound-of-the-baskervilles, hungry-stones, woman-in-white reduce proposal blockers 907 to 902. Candidate 3a9286e6b6ce2e3e363219f1dc28f49144ebf7a2 changes only ten checksum manifests; 224 held, seven accepted, no new decision/publication/audio, and all approved product/source/approval/registry/launch bytes are unchanged. All three artifact digests and exact controller/proposal diff identity were verified independently. Fresh normal candidate checks and protected merge remain required. Three other chapter files (Scientific Management chapter-004, The Suicide Club chapter-001, Ward No. 6 chapter-001) are absent from the committed tree and no path history was found; their exact recorded hashes are retained in the decision record. Do not bless missing chapters by changing checksums, stripping inventory entries or inserting placeholders.
