# MARKETING_LANDING Discovery

Generated: 2026-07-08T11:26:02Z

## Scope

MARKETING_LANDING is discovery-active only. No marketing source, deployment, release gate, paid audio, paid Listen, publication, or production metadata state was changed.

SETTINGS is frozen as owner-approved for phase progression. HOME, LIBRARY, BOOK_DETAIL, READER, AUDIOBOOK_PLAYER, and BRAND_HEADER_LOGO remain frozen in their approved scopes.

## Files And Routes Inspected

- `frontend/src/App.js`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/MicroStoryLanding.jsx`
- `frontend/src/pages/Pricing.jsx`
- `frontend/src/pages/About.jsx`
- `frontend/src/pages/Contact.jsx`
- `frontend/src/pages/Journal.jsx`
- `frontend/src/pages/Account.jsx`
- `frontend/src/components/Header.jsx`
- `frontend/src/components/Footer.jsx`
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`
- `frontend/src/components/ComingSoonBoard.jsx`
- `frontend/src/components/ShelfTwoSlideshow.jsx`
- `frontend/src/components/JsonLd.jsx`
- `frontend/src/hooks/useSEO.js`
- `frontend/src/lib/controlledLaunch.js`
- `frontend/src/lib/funnelAnalytics.js`
- `frontend/src/launch-drafts/dracula/DraculaLandingDraft.jsx`

Routes identified:

- `/`
- `/micro-story`
- `/pricing`
- `/about`
- `/contact`
- `/journal`
- `/journal/:slug`
- `/account`
- `/library`
- `/book/:slug`

## Current Marketing Surfaces

- Home is the primary live marketing landing surface. It is already release-truth-aware: Bengali classics are described as reader-only where audio is gated, English classics are reader-ready, and approved listening appears only after production evidence.
- Micro-story landing is a campaign-style acquisition route for low-risk reading-time conversion. It does not mention audio.
- Pricing is a reading-time conversion route centered on Dracula and wallet-backed reading minutes. It does not sell audiobook access.
- About remains Dracula-first in title/copy and is likely stale relative to the newer Bengali/English balanced brand direction.
- Contact is support and press oriented, not a conversion landing route.
- Journal is editorial content and can support trust proof, but should not be treated as an audio launch page.
- Header CTA is `Enter Library`. Footer copy is release-truth-safe.
- Approved Audiobook Spotlight is safely manifest-gated and returns null unless shared release-state evidence approves controls.

## Release-Truth Findings

PASS:

- Home explicitly says no unapproved audiobook controls and no hidden audio overclaim.
- Newsletter copy says no audiobook or paid campaign is live from that form.
- ComingSoonBoard frames approved audiobooks as release-gated and exposes no Listen CTA for blocked titles.
- ApprovedAudiobookSpotlight fetches the reader manifest and then calls `audiobookReleaseState`; it fails closed when evidence is missing.
- JsonLd usage found only on Book Detail and Journal Article; no marketing route emits AudioObject.
- Pricing sells reading time, not audiobook access.
- Micro-story route sells a reading-time entry point, not an audiobook.

Risks to address before MARKETING_LANDING owner review:

- `useSEO.js` default description still says the library is "beginning with Dracula", which can leak stale Dracula-first framing into pages without custom SEO.
- `About.jsx` title and copy are explicitly Dracula-first and may conflict with the approved premium bilingual brand direction.
- `controlledLaunch.js` Dracula fallback description says "an audiobook experience in private review"; this is internal-truth-adjacent but should be tightened if surfaced on public marketing/detail paths.
- Pricing and account copy are strongly Dracula-centered. That may be acceptable for controlled reading monetization, but the MARKETING_LANDING implementation should avoid letting Dracula dominate the brand landing surface.
- Owner confirmed `sales@reoenterprise.org` is the canonical public contact email. Public contact, footer, pricing, and social mailto references must use `.org`; `.in` is a trust risk.
- `ShelfTwoSlideshow.jsx` has a `Notify Me` button that prevents default and does not submit interest. This may be acceptable as visual pipeline copy, but implementation should either make it real or label it as not collecting signups.
- Home still contains an `ApprovedAudiobookSpotlight`; it is gated correctly, but MARKETING_LANDING smoke should keep proving no default A Ghost Story probe and no unapproved audio CTA.

## Conversion Findings

Primary current CTAs:

- Home hero: `Start Reading` to `/library`.
- Home secondary: `Browse Library`.
- Home reading path: `See Reading Passes` to `/pricing`.
- Newsletter: `Join the Reading Circle`.
- Header: `Enter Library`.
- Micro-story: `Start with ₹49`.
- Pricing: `Buy reading time` or `Run test purchase` depending payment config.

Conversion risks:

- The landing system has several CTAs with different goals: library entry, pricing, newsletter, micro-story, and Dracula continuation. MARKETING_LANDING implementation should choose a clearer hierarchy.
- Reading-time conversion is calm and truthful, but still anchored to Dracula. The next implementation should balance Bengali and English representation without false audiobook claims.
- Trust proof is copy-heavy. A future landing pass should make release-truth safeguards scannable without becoming defensive.
- Mobile CTA density should be checked because Home, Pricing, and Micro-story all use stacked CTA/panel layouts.
- Journal and About can reinforce trust but should not overpromise launch breadth or audio availability.

## SEO And Structured Data Findings

- `useSEO` is the shared metadata hook for marketing pages.
- Default SEO description is stale and Dracula-first.
- Home has custom balanced SEO.
- Micro-story, Pricing, About, Contact, and Journal have route-specific SEO.
- No marketing route was found emitting AudioObject structured data.
- Book Detail JsonLd remains Book-only under the current implementation.

SEO risks:

- Default SEO and About SEO should be updated in the implementation phase to avoid Dracula-first brand dominance.
- Marketing pages should not claim audiobooks unless production route, manifest, endpoint, player, and browser evidence pass.
- If the next landing page introduces structured data, it should stay WebSite/Organization/WebPage only unless audio evidence supports anything more specific.

## Release-Gate Risk Table

| Surface | Current risk | Required implementation stance |
| --- | --- | --- |
| Home | Approved spotlight must stay manifest-gated | Keep fail-closed, no default audio probe |
| Micro-story | Campaign route could become salesy | Keep reading-time-only, no audiobook claim |
| Pricing | Dracula-centric reading conversion | Keep reading-time truth, no audiobook sale |
| About | Dracula-first stale positioning | Rebalance brand story toward Bengali + English |
| Footer/Header | Safe library CTAs | Preserve brand-header approval and no audio claims |
| JsonLd/useSEO | Default SEO stale | Update copy without adding AudioObject |
| Controlled launch fallback | "audiobook private review" can sound marketable if surfaced | Tighten copy to audio-hidden/release-gated wording |
| Approved Audiobook Spotlight | Safe with manifest gate | Keep as evidence-gated only |

## Marketing Landing Target

- Premium literary landing experience.
- Calm conversion, not aggressive sales pressure.
- Release-truth-safe audiobook claims.
- Reader-first titles presented as premium.
- Balanced Bengali and English representation.
- No Dracula-first brand dominance.
- No unapproved Listen CTA.
- No paid Listen claim unless production proof passes.
- Strong SEO without false audio claims.
- Mobile-safe layout.
- No launch-wide 10/10 claim.

## Recommended Implementation Plan

1. Define whether MARKETING_LANDING means Home-only polish or a distinct campaign page. Prefer Home plus shared marketing-copy cleanup unless the owner wants a new route.
2. Rebalance About and default SEO copy away from Dracula-first language.
3. Audit Home, Pricing, Micro-story, About, Header, Footer, and Journal for audiobook words and convert any unsupported claims to reader-first or release-gated language.
4. Decide a single primary conversion hierarchy: library first, reading-time second, newsletter third.
5. Add MARKETING_LANDING visual smoke support covering Home, Micro-story, Pricing, About, and Contact.
6. Generate owner packet and screenshots only after implementation.

## Blockers

- Implementation is not started.
- Full preview/production validation remains not proven.
- Paid Listen campaigns remain blocked.
- `paid_tts.lock` remains active and no paid audio work is authorized.

## Next Exact Command

```bash
cd /private/tmp/earnalism-parallel-prelaunch && sed -n '1,260p' internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/MARKETING_LANDING_discovery.md
```
