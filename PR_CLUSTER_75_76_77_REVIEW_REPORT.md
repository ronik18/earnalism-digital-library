# PR Cluster 75/76/77 Review Report

Status: `CLUSTER_REVIEW_READY_WITH_ORDERED_MERGE`

Reviewed PRs:

- #75 `Record Golden Hour Library hero provenance and scorecard evidence`
- #76 `Add repo cleanup inventory and quarantine duplicates`
- #77 `Add signed-user journey recorder and receipt audit`

## Executive Summary

The three PRs are compatible as a release-quality cluster after updating #75 to current `origin/main`. Together they improve homepage evidence, repository hygiene, signed-user journey regression coverage, and payment receipt truth without changing product behavior, payment behavior, public-audio state, or admin access rules.

Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED` and audiobook production remains `PRODUCTION_BLOCKED`.

## PR #75 Review

Decision: `READY_AFTER_REBASE`

Scope:

- Report/provenance-only.
- Documents Golden Hour Library hero source evidence, owner-provided rights status, optimized local WebP derivative, no hotlinking, and public provenance policy.
- Does not change runtime product behavior, payment behavior, audio behavior, or publication state.

Enhancement applied:

- Rebased #75 onto current `origin/main`.
- Resolved the only conflict in `HOMEPAGE_HERO_LIBRARY_THEME_REVIEW.md` by preserving current main's later hero overlay/cover refinements and adding the provenance/license evidence from #75.

Evidence quality:

- Scores remain explicitly tied to screenshot evidence and post-deploy review language.
- Public guardrails remain documented: no public audio, no Listen Now CTA, no AudioObject metadata, no Kshudhita public CTA, no payment behavior change.

Remaining caution:

- Because #75 is report-only, it should merge first to avoid reintroducing stale report conflicts.

## PR #76 Review

Decision: `READY_WITH_REVIEWED_QUARANTINE_SCOPE`

Scope:

- Adds inventory, cleanup reports, risk register, performance/refactor reports, and repo health scorecard.
- Moves only Mac-style duplicate files with counterpart paths into committed quarantine under `archive/unused-candidates/2026-06-27/`.
- Adds `scripts/repo_cleanup_inventory.py`.

Quarantine safety:

- No production runtime files are removed.
- No payment, public-audio, admin, reader, SEO, launch evidence, or current regression guard files are removed from active paths.
- The quarantine manifest preserves original paths, quarantine paths, counterpart paths, file sizes, hashes, and restore guidance.
- Quarantine is committed evidence, not gitignored, so reports/manifests remain visible.

Important nuance:

- Some quarantined duplicates differ from their active counterparts, but their filenames use duplicate suffixes such as ` 2`/` 3`, have zero detected references, and active counterparts remain in place. This is acceptable as quarantine, not deletion.
- Ambiguous files remain `REVIEW_REQUIRED`; #76 intentionally does not quarantine launch-critical or uncertain files.

Remaining caution:

- #76 is large due to committed archive content. Merge after #75 so the report-only hero evidence lands first, then verify CI on the cleanup branch before merging.

## PR #77 Review

Decision: `READY_AFTER_CLUSTER_COMPATIBILITY_CHECK`

Scope:

- Adds `scripts/record_signed_user_journey.mjs`.
- Adds CI-safe smoke journey and owner-operated full video journey.
- Wires `npm run regression:ci` to run the smoke journey before the normal regression suite.
- Adds signed-user UX reports and payment receipt/invoice audit documents.
- Adds gitignore rules for large video/trace outputs.

Signed-user journey safety:

- CI-safe smoke does not use owner credentials.
- Manual full-video recorder starts recording only after owner confirms manual sign-in.
- Storage state is in memory only for owner runs and is not written to disk.
- Live Razorpay payment execution is skipped by design.
- Reports redact payment-like, token-like, email-like, card-like, and secret-like strings.
- Video and trace artifacts remain gitignored.

Receipt/invoice truth:

- Current flow is documented as Razorpay Orders + Checkout + server verify/webhook + Earnalism wallet ledger.
- Earnalism-owned receipt email is documented as `NOT_IMPLEMENTED_IN_REPO`.
- Razorpay dashboard receipt settings remain `OWNER_DASHBOARD_VERIFICATION_REQUIRED`.
- Razorpay Invoice API is documented as `NOT_USED_IN_REPO`.
- GST/tax invoice generation is not claimed.
- Sample receipt is marked `SAMPLE_ONLY_NOT_TAX_INVOICE` and uses redacted references only.

Remaining caution:

- Full owner video should be run before major UX/payment/reader releases and post-deploy verification, not every docs-only PR.

## Cross-PR Conflict Analysis

Direct file overlap after #75 rebase: none.

Initial conflict found:

- #75 originally conflicted with current `main` in `HOMEPAGE_HERO_LIBRARY_THEME_REVIEW.md` because main had later hero overlay/cover polish notes.
- Fixed by rebasing #75 and preserving both the newer main refinements and #75 provenance evidence.

Compatibility checks:

- #76 does not quarantine any #75 files.
- #76 does not quarantine any #77 files.
- #77 does not rely on files quarantined by #76.
- #77 package scripts remain compatible with #76.
- #77 `.gitignore` additions for journey media do not hide #76 evidence reports or quarantine manifests.
- All three preserve Dracula reading-only launch truth.

## Merge Order Recommendation

Recommended order:

1. Merge #75 first.
2. Merge #76 second.
3. Merge #77 third.

Reasoning:

- #75 is now report-only and rebased to latest main.
- #76 is broader and should land after report-only evidence to minimize future report conflicts.
- #77 should land last because it adds regression:ci journey smoke coverage and can validate the merged state after cleanup.

## Remaining Risks

- #76 keeps a large committed archive. This is intentional evidence-preserving quarantine, but reviewers should accept the repository-size tradeoff.
- #77 CI smoke has no seeded signed-in test-user state yet; it treats account/admin as auth-boundary checks unless `EARNALISM_JOURNEY_TEST_STORAGE_STATE` is supplied.
- Owner dashboard verification is still required for Razorpay automated receipt emails and any GST/tax invoice behavior.

## Final Recommendation

Safe to merge in the recommended order if the final validation suite passes on each PR and the combined local cluster remains green.

Do not merge if any validation fails, if public audio becomes reachable, if payment behavior changes, if admin protection weakens, or if #76 is changed to quarantine ambiguous files instead of duplicate-only candidates.
