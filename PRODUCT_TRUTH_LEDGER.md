# Product Truth Ledger

Last updated: 2026-06-21

This ledger is the current-branch product truth for The Earnalism. It is intentionally conservative: reports from draft or unmerged PR branches are evidence to review, not public-product claims.

## Executive Summary

The Earnalism is currently a Dracula-first controlled digital reading room. Dracula by Bram Stoker is the only currently approved core public reading release on this branch. The product-wide launch posture remains HOLD for broad branding or advertising until the remaining production, evidence, social, accessibility, and approval blockers are closed.

Dracula's controlled publication evidence is strong, but it is narrow. A 9.9 score in Dracula-specific scorecards applies to the Dracula controlled reading candidate only. It must not be reused as a 9.9+ or 10/10 product-wide launch claim.

## Current Public Product State

- Dracula is the only currently approved core public reading release.
- Dracula reader access is limited to the approved core reading experience.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks are not public/live.
- Demo, fashion, ecommerce, and template content are governed by removal/noindex/410 policy and must not return as public catalog content.
- Social brand kit material on this branch is manual-setup evidence only. It is not proof that public social profiles, social posts, paid ads, or campaigns are live.
- Draft or unmerged PR reports must not be treated as live product state.

## Allowed Public Claims Today

- The Earnalism is a quiet digital reading room beginning with Dracula by Bram Stoker.
- Dracula is the first controlled approved reading release.
- Chapter 1 of Dracula can be previewed for free when the live route and backend catalog truth canaries pass.
- Reading-time packs are available as Dracula-first reading-time UX, subject to payment/wallet verification.
- Dracula source and rights evidence are based on Project Gutenberg eBook #345 and current-branch approval artifacts.
- Dracula audiobook is not available yet.
- Bengali Gothic and other classics are moving through a rights-safe pipeline.
- Kshudhita Pashan can be described as pipeline-only, source/rights/QA-gated, and not publicly readable.

## Blocked Public Claims

- Do not claim a broad live catalog or that every book is currently readable.
- Do not claim audiobooks are live, full audiobooks are available, or "Listen Now" is available.
- Do not claim Dracula audio is available.
- Do not claim Kshudhita Pashan is publicly readable, previewable, listenable, or available to start.
- Do not claim the product is 10/10, 9.9+/10 launch-ready, WCAG compliant, blind-user tested, or a fully accessible audiobook platform.
- Do not claim human narration, "no AI touch", or final audiobook quality unless the relevant human-recorded or reviewed evidence exists on the current branch.
- Do not claim paid ads, social profile publication, social posting, email campaigns, or influencer/press launch is live.
- Do not claim draft PR evidence or PR-branch-only assets are merged, deployed, live, or public.

Draft PR evidence must not become public-product claims.

## Dracula Status

Dracula is the only currently approved core public reading release.

Current evidence supports:

- Work: Dracula by Bram Stoker.
- Source: Project Gutenberg eBook #345.
- Rights tier: Tier A in the Dracula source/rights report.
- Verification status: approved in the Dracula source/rights report.
- QA status: QA_PASSED for the controlled reading candidate.
- Chapter evidence: 27 meaningful chapters in the controlled artifact pack.
- Reader state: enabled for Dracula only.
- Preview state: Chapter 1 free preview is allowed.
- Audio state: disabled and not required for this controlled reading launch.

Dracula-specific 9.9 scorecards are scoped to the controlled Dracula reading candidate. They are not product-wide launch readiness scores.

## Kshudhita Pashan Status

Kshudhita Pashan remains pipeline-only.

Allowed internal/product wording:

- pipeline-only
- coming through source, rights, text QA, pronunciation, and listening QA
- Notify Me / Reading Circle interest

Blocked wording and UI:

- Start Reading
- Read Preview
- Listen Now
- full audiobook
- public audio preview
- public reader access

Draft or branch-only Bengali audiobook/model-bakeoff evidence does not make Kshudhita Pashan public, approved, readable, or listenable.

## Audiobook Status

Audiobooks are not public/live.

Current-branch reports identify audiobook ambition and governance work, but not public audiobook approval. The current branch also acknowledges existing or historical audio assets with unknown rights/QA state. Those assets must not become public claims.

Required before public audiobook claims:

- approved source and rights metadata for the specific book and edition
- approved voice/provider governance
- generated or uploaded audio evidence
- listening QA and synchronization evidence
- no public URL exposure before release approval
- owner approval for public audio release

Dracula audio remains disabled. Kshudhita Pashan audio remains blocked/pipeline-only.

## Accessible Audiobook Ambition

Accessible audiobook support is an internal ambition and product direction. It can be discussed as a goal, plan, or pipeline requirement.

Blocked public accessibility claims until supported by current-branch evidence:

- blind-user tested
- WCAG compliant
- fully accessible audiobook platform
- screen-reader certified
- accessibility audited
- compliant audiobook experience

Accessibility work should remain evidence-led, with human review and assistive-technology test results before public claims.

## Payment/Wallet Status

Current payment UX is Dracula-first reading-time UX. The pricing page names and copy are intended to frame reading time as a calm, non-subscription reading-room purchase.

Current evidence supports test/smoke posture only unless a separate production payment verification exists:

- payment smoke reports are test-mode/mock-safe checks
- no live Razorpay charge was run for this ledger
- no wallet production mutation was performed for this ledger
- no payment provider behavior was changed for this ledger

Public copy may say secure payment by Razorpay only where existing payment integration and smoke checks support it. It must not claim live-money production success unless that exact evidence exists.

## SEO/Public Surface Status

Current SEO posture is Dracula-first and controlled:

- homepage and library copy must not imply a broad live catalog
- Dracula book SEO can be promoted as the approved public reading page when raw/static checks pass
- reader routes should remain noindex and canonicalize to the Dracula book page where configured
- unapproved reader/book routes must not be included in sitemap as public releases
- removed demo/ecommerce/fashion routes must remain out of sitemap and return 410/404 with noindex handling

Production post-deploy SEO/social/canary checks are still required before broad advertising claims.

## Source/Rights Evidence Status

Dracula has current-branch source and rights evidence:

- `DRACULA_SOURCE_RIGHTS_REPORT.md`
- `DRACULA_CONTROLLED_ARTIFACT_PACK_REPORT.md`
- `data/controlled_publications/dracula/approval_evidence.json`
- `data/controlled_publications/dracula/source_evidence.json`

The broader catalog and first-batch automation still require item-by-item rights/source evidence. No Tier B or Tier C item may be treated as globally publishable.

## Social/Brand Asset Status

The current branch includes social brand-kit evidence, but that evidence is not a live social launch.

Current status:

- manual social setup required
- owner upload required
- social URLs must be configured as real http/https URLs before rendering
- paid ads remain held
- no social posts, profile edits, uploads, emails, or campaigns were performed by this ledger

Branding and ads should remain HOLD until owner proof, production canaries, real-user UX review, and post-deploy readiness checks pass.

## Current Launch Score With Evidence

Product-wide launch readiness: 8.0/10 HOLD, based on current launch readiness and final go/no-go reports.

Dracula controlled reading candidate: 9.9/10 in Dracula-specific scorecards only.

Social brand kit: current-branch evidence supports manual setup readiness, not paid ads or live social publication.

The product must not claim 9.7+/10 or 10/10 launch readiness until all broad launch evidence exists on the current branch and required production canaries pass.

## Remaining Blockers Before 9.7+/10 Launch Readiness

- Production post-deploy canaries must pass in the right order.
- Production raw HTML SEO/social preview checks must pass after deploy.
- Real-user UX video audit evidence must exist and pass if used for branding.
- Owner approval must exist for brand use and paid ads.
- Public social profile URLs and screenshots must be verified if social claims are made.
- No draft PR evidence may be promoted into public claims.
- PR #44 and PR #45 must not be used for public audiobook claims while Draft/conflicting.
- Full accessibility claims require actual accessibility evidence.
- Public audiobook claims require release-gate approval and listening QA.
- Payment/wallet production claims require explicit live production verification.

## Evidence Map: claim -> supporting file/report

| Claim | Supporting evidence on current branch |
| --- | --- |
| Dracula is the only currently approved core public reading release. | `DRACULA_SOURCE_RIGHTS_REPORT.md`, `DRACULA_CONTROLLED_ARTIFACT_PACK_REPORT.md`, `CONTROLLED_PUBLICATION_PRECHECK.md`, `data/controlled_launch.json` |
| Dracula has 27 chapters in the controlled artifact pack. | `DRACULA_CONTROLLED_ARTIFACT_PACK_REPORT.md`, `data/controlled_publications/dracula/reader_manifest.json` |
| Dracula audio is disabled. | `DRACULA_CONTROLLED_ARTIFACT_PACK_REPORT.md`, `AUDIOBOOK_READINESS_REPORT.md`, `data/controlled_launch.json` |
| Kshudhita Pashan remains pipeline-only. | `frontend/src/lib/controlledLaunch.js`, `frontend/src/pages/Home.jsx`, `frontend/src/pages/Library.jsx`, `MERGE_STACK_READINESS_REPORT.md` |
| Broad product launch remains HOLD. | `FINAL_GO_NO_GO_DECISION.md`, `LAUNCH_READINESS_REPORT.md` |
| Demo ecommerce/fashion URLs must not return as public content. | `CATALOG_GOVERNANCE.md`, `regression/modules/13-public-content-governance.test.js` |
| Social brand kit is manual setup only, not paid ads. | `SOCIAL_PROFILE_REVAMP_REPORT.md`, `BRANDING_ADVERTISEMENT_GO_NO_GO.md`, `FINAL_GO_NO_GO_DECISION.md` |
| Audiobooks are blocked until explicit release approval. | `AUDIOBOOK_READINESS_REPORT.md`, `GUARDRAILS.md` |
| Accessibility claims are blocked without evidence. | This ledger; no current-branch evidence proving blind-user testing, WCAG compliance, or a fully accessible audiobook platform was found. |

## Owner Approval Checklist

- [ ] Owner approves Dracula-only live reading claims.
- [ ] Owner approves public social profile copy and visuals.
- [ ] Owner provides verified live social profile URLs.
- [ ] Owner approves brand use after real-user UX/video review.
- [ ] Owner approves paid ads after production canaries and UX evidence pass.
- [ ] Owner approves any future audiobook release after release-gate and listening QA pass.
- [ ] Owner approves any accessibility claim only after evidence exists.
- [ ] Owner confirms no draft PR evidence is being used as public truth.

## Merge Dependency Notes From PR #42-#46 Audit

`MERGE_STACK_READINESS_REPORT.md` exists locally and was incorporated as an audit artifact. It is not itself proof that those PRs are merged.

Current merge-stack audit summary:

- PR #42 `codex/premium-site-tour-video-package`: site-tour/video evidence branch; not public launch truth unless merged and validated on the current branch.
- PR #43 `codex/audiobook-regeneration-governance`: audiobook governance branch; recommended before model bakeoff branches if merged.
- PR #44 `codex/bengali-audiobook-model-bakeoff`: Draft in the audit; do not use for public launch claims.
- PR #45 `codex/english-audiobook-model-bakeoff`: Draft in the audit; do not use for public launch claims.
- PR #46 `codex/premium-social-brand-kit`: current working branch includes social brand-kit evidence, but it remains manual setup only and not ads-ready.

Recommended merge order from the audit was #43, #46, #42, then #44/#45 only after Draft/conflict resolution. This ledger does not merge, deploy, publish, or activate any of those PRs.
