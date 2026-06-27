# Signed User UX Before/After Report

Status: `AWAITING_FIRST_OWNER_RECORDING`

The requested before/after comparison is intentionally evidence-gated. This PR adds the recorder and report generation system. The first production signed-user recording must be run by the owner before claiming concrete before scores, applying UX changes from findings, and rerunning the after audit.

## Before Recording

- Command: `npm run ux:journey-record:prod`
- Owner action: sign in manually in the opened browser, then press Enter in the terminal.
- Expected output: `output/ux-journey-recordings/<timestamp>/`
- Live payment execution: `SKIPPED_BY_DESIGN`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Audiobook production: `PRODUCTION_BLOCKED`

## Enhancement Phase

Safe enhancements may be implemented only after the first recording identifies evidence-backed issues. Allowed categories:

- Smoother route transitions
- Skeleton/loading states
- Premium empty/error states
- Reader typography/spacing
- Library card hierarchy
- CTA placement
- Mobile refinements
- Social link polish
- Notify Me / Reading Circle clarity
- Wallet usage audit visibility
- Journal navigation
- Site-tour copy/focus
- Hero readability

Blocked categories:

- Public audiobook release
- Live payment execution
- New book publication
- Third-party analytics pixels
- Broad rewrites without evidence

## After Recording

After approved fixes, rerun:

`npm run ux:journey-record:prod`

The final before/after score should compare:

- route timings
- screenshots
- video observations
- console/network findings
- public-claims scan result
- conversion-path friction
- reader comfort
- wallet/payment clarity
- admin boundary behavior
