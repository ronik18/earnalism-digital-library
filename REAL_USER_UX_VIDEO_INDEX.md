# Real-User UX Video Index

Date: 2026-06-20

## How To Generate The Videos

```bash
npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=chromium
```

Open traces with `npx playwright show-trace` using the trace path printed in the command output.

## Expected Video Evidence

Playwright stores video attachments in:

`output/real-user-ux/playwright-artifacts/`

The JSON run summary is written to:

`output/real-user-ux/playwright-results.json`

Expected journeys:

| Journey | Evidence expectation |
| --- | --- |
| Homepage desktop | Video, trace, screenshot |
| Homepage mobile | Video, trace, screenshot |
| Carousel / featured Dracula section | Video, trace, screenshot |
| Library desktop | Video, trace, screenshot |
| Library mobile | Video, trace, screenshot |
| Dracula book page | Video, trace, screenshot |
| Dracula reader page | Video, trace, screenshot |
| Pricing page | Video, trace, screenshot |
| Journal and contact pages | Video, trace, screenshots |
| Removed demo route canary | Video, trace, screenshot |

## Storage Policy

Videos are generated as local audit artifacts and are not committed to Git.

## Latest Local Run

- Browser videos captured: 10
- Traces captured: 11
- Screenshots captured: 11
- Playwright status: PASS, 11/11

The backend catalog truth test is API-only and therefore has a trace but no browser video.
