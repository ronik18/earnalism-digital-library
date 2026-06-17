# Social Automation Safety And Environment Guide

Earnalism does not currently need a full social autoposting system in the app. Keep the first growth campaign lightweight: generate drafts, approve manually, then post or schedule through official platform tools.

## Safety Principles

- Use official platform APIs or OAuth tokens only.
- Do not store or script social passwords.
- Do not bypass rate limits, captchas, or platform anti-spam protections.
- Store secrets only in environment variables, GitHub Actions secrets, or the platform's approved secret manager.
- Require manual approval before publishing unless an official API posting integration already exists.
- Keep a human review step for compliance, claims, pricing, and brand tone.
- Do not use fake testimonials, fake urgency, fake income claims, or guaranteed growth promises.

## Recommended Secret Names

Use only the keys that match platforms you actively integrate:

```bash
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ORG_URN=
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
META_APP_ID=
META_APP_SECRET=
META_PAGE_ID=
INSTAGRAM_BUSINESS_ACCOUNT_ID=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_CHANNEL_ID=
```

## Manual Approval Workflow

1. Draft posts from `docs/marketing/social-campaign-pack.md`.
2. Add UTM links for the campaign, channel, creative, and date.
3. Review for accuracy: no guaranteed revenue claim, no misleading promise, no real payment simulation.
4. Schedule through native tools such as LinkedIn Pages, Meta Business Suite, YouTube Studio, or approved API clients.
5. Track the published URL, UTM, date, platform, and creative in the growth dashboard.

## Automation Boundary

Allowed:

- Generate post drafts.
- Generate captions and thumbnails.
- Create scheduled-post CSVs for manual import.
- Run link checks and UTM validation.
- Notify the team when a post is ready for review.

Not allowed without explicit official API integration:

- Browser-based password login automation.
- Mass posting to groups or comments.
- Auto-DMs.
- Automated scraping of contacts.
- Reposting the same message repeatedly across communities.

## Suggested Draft Metadata

For every campaign asset, track:

- `campaign`: `100_day_growth`
- `phase`: foundation, awareness, education, conversion, retention
- `channel`: linkedin, x, instagram, facebook, youtube, whatsapp, email
- `asset_type`: site_tour, carousel, short_video, quote, feature_demo, newsletter
- `owner`: reviewer/publisher
- `status`: draft, reviewed, scheduled, published, archived
- `utm_url`: final tracked URL
