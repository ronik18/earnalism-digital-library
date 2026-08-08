# Footer Compact V1 Implementation Prompt

Act as Earnalism's senior product designer, conversion strategist, accessibility reviewer, and frontend engineer. Redesign the public site footer so it feels like a refined library colophon: premium, calm, compact, useful, and visually continuous with the dark Reading Circle section above it.

## Problem to solve

The live footer currently consumes about 453 px on desktop and 788 px on mobile. It adds a large external top margin, spreads a small amount of content across oversized vertical padding, and separates legal copy into multiple roomy rows. The result feels detached from the preceding page and wastes high-value end-of-page space.

## Design direction

- Remove the external top margin so the footer begins immediately after the preceding section.
- Keep the warm ivory editorial palette, but add a restrained burgundy-to-gold hairline to create a deliberate transition from the Reading Circle.
- Treat the footer as a compact library colophon with three jobs: reinforce the brand promise, provide fast navigation, and offer one low-pressure contact action.
- Use the approved Earnalism wordmark, concise release-truth copy, spacious but efficient typography, and subtle borders rather than large decorative areas.
- Consolidate copyright and content-protection copy into one compact legal rail.
- Keep every interactive target at least 44 px high on touch layouts, preserve visible focus states, and avoid horizontal overflow.

## Marketing and content strategy

- Lead with trust: reader-ready classics remain visible; listening rooms are represented only when evidence-approved.
- Use a calm, specific contact prompt for rights, partnerships, and title suggestions.
- Avoid urgency, invented availability claims, newsletter duplication, aggressive sales language, or any audio-release implication.
- Preserve the canonical public email: `sales@reoenterprise.org`.

## Acceptance criteria

- Desktop footer height is no more than 300 px at a standard wide viewport.
- Mobile footer height is no more than 560 px at a 390 px CSS viewport.
- The previous `mt-24 sm:mt-32` gap is removed.
- Library, Journal, About, Contact, and Sign In remain available.
- Copyright and content-protection messaging remain present.
- WCAG AA contrast, keyboard focus, semantic navigation, and 44 px touch targets are preserved.
- No audiobook gate, catalog truth, routes, tracking, or backend behavior changes.
- Focused tests, production build, responsive browser checks, and production canary all pass before declaring the redesign live.
