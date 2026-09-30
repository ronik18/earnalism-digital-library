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
