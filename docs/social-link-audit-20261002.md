# Earnalism social-link and header audit — 2 October 2026

## Scope and result

All customer-facing profile actions resolve through `config/socialLinks.js`: the shared footer on public pages, mobile header menu (including the immersive Reader/Listener shell), and Contact page. Book Detail and Journal Article use the shared `ShareButtons` component. A source-wide URL search found no additional independent customer-facing social-profile definitions or placeholder social links.

Production `/api/settings/public` returned blank social overrides; the six canonical defaults apply. Anonymous GETs to all five social profiles returned HTTP 200 and provider-page titles naming Earnalism. Facebook's numeric profile redirects to its named Earnalism profile. The configured YouTube channel's full response title confirms the Earnalism channel. Exact URLs, final URLs, timestamps and response hashes are recorded in `social-link-audit-20261002.json`.

This establishes destination identity and reachability; it does not independently establish account ownership or simulate a logged-in follow/share action. Email address syntax is valid; message delivery was not tested. No social post, message, follow, like or customer mutation was performed.

## Shared destinations

| Platform | Canonical destination | Verification |
| --- | --- | --- |
| LinkedIn | https://www.linkedin.com/company/earnalism-a-reo-enterprise-venture/ | 200, Earnalism page title |
| Facebook | https://www.facebook.com/profile.php?id=61591315384768 | 200, redirects to Earnalism named profile |
| Instagram | https://www.instagram.com/theearnalism/ | 200, Earnalism handle/title |
| X | https://x.com/earnalism | 200, Earnalism profile/title |
| YouTube | https://www.youtube.com/channel/UCw-UnAXdRzqij8_B2TlgQjQ | 200, Earnalism channel/title |
| Email | mailto:sales@reoenterprise.org | Valid mailto; no email sent |

## Repairs

- Profile overrides must match their platform; platform homepages, share intents, URL credentials and wrong-domain overrides fall back to the existing canonical destination. No new handle is invented.
- Share URLs use the public apex canonical pathname, excluding tracking parameters, credentials and fragments. Book/article identity is retained. Copy-link uses the same safe URL.
- X sharing uses `https://x.com/intent/tweet`, as published by https://publish.x.com/; WhatsApp, Facebook and LinkedIn retain their platform share endpoints. Share intents are distinct from profile destinations.
- Header lockup size has one viewport contract, shared by all route shells. Removed competing homepage header CSS and earlier lockup-width overrides. Official asset bytes, aspect ratio and navigation routes are unchanged.
- Desktop lockup: 300px / 104px header. Tablet: 280px / 96px header. Mobile: up to 240px / 80px header, constrained to 224px at 360px to preserve 44px search/menu targets.

## Visual evidence

Anonymous production BEFORE: `/tmp/earnalism-header-social-before/report.json`, 18 route/viewport captures. Local deterministic AFTER: `/tmp/earnalism-logo-social-after-final/summary.json`, canonical header matrix harness: 108/108 states across 18 route families and 1440/1280/1024/768/390/360px; zero header/page overflow, runtime/console/request failures. Reader/Listener use an isolated fixture build; the production build flag remains disabled. The first mobile review prompted a correction from 224px to 240px at 390px, retaining 224px on narrow 360px devices. The shared root height token also matches the enlarged masthead so sticky content is positioned below it. No logo crop or transform scaling is used.

These local screenshot paths are execution evidence; the existing protected owner-review workflow publishes exact-head durable artifacts after the integration commit. No visual approval is inferred from the screenshots.
