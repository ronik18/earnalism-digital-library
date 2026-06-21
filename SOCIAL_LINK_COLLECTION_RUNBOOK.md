# Social Link Collection Runbook

Status: `OWNER_UPLOAD_REQUIRED`

Footer social icons must render only after the owner creates real public social profiles and configures verified http/https URLs. This PR does not create profiles, post content, upload media, call social APIs, or set environment variables.

## Environment Variables

Set only verified public profile URLs:

- `REACT_APP_INSTAGRAM_URL`
- `REACT_APP_YOUTUBE_URL`
- `REACT_APP_FACEBOOK_URL`
- `REACT_APP_LINKEDIN_URL`
- `REACT_APP_X_URL`
- `REACT_APP_WHATSAPP_CHANNEL_URL`
- `REACT_APP_TELEGRAM_CHANNEL_URL`

## Validation

Run:

```bash
npm run social:links:validate
```

The validator rejects:

- empty URLs
- `#`
- `javascript:` URLs
- non-http/non-https URLs
- private/admin/auth URLs
- placeholder usernames
- mismatched platform domains
- localhost/private profile URLs

It writes:

- `output/social-brand-kit/latest/social_links_validation.json`
- `output/social-brand-kit/latest/social_links_validation.md`

No network call or social API call is made by default.

## Footer Behavior

The existing footer social component renders nothing when no valid URL is configured. It must not render fake links, empty links, `href="#"`, `javascript:` links, or mailto social links.

## Owner Checklist

1. Create or claim the real social profile.
2. Upload the approved avatar/banner manually.
3. Paste the approved copy from `SOCIAL_PROFILE_COPYBOOK.md`.
4. Set profile website to `https://theearnalism.com/book/dracula`.
5. Capture a screenshot of the live profile.
6. Set the matching environment variable.
7. Run `npm run social:links:validate`.
8. Rebuild/deploy only after validation passes.

## Advertising Hold

Do not start paid ads until:

- every intended profile URL is verified
- owner upload screenshots exist
- real-user UX video audit passes
- social preview audit passes
- release post-production canary passes
