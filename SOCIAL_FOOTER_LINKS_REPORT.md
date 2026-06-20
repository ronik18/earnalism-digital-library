# Social Footer Links Report

Status: `READY_FOR_PR_REVIEW`

## Supported Channels

The footer social row supports these configured channels:

| Channel | Environment variable | Renders when configured |
| --- | --- | --- |
| Instagram | `REACT_APP_INSTAGRAM_URL` | yes |
| YouTube | `REACT_APP_YOUTUBE_URL` | yes |
| Facebook | `REACT_APP_FACEBOOK_URL` | yes |
| LinkedIn | `REACT_APP_LINKEDIN_URL` | yes |
| X | `REACT_APP_X_URL` | yes |
| WhatsApp Channel | `REACT_APP_WHATSAPP_CHANNEL_URL` | yes |
| Telegram Channel | `REACT_APP_TELEGRAM_CHANNEL_URL` | yes |

## No Fake Links

- Missing URLs do not render.
- Empty URLs do not render.
- `#` URLs do not render.
- Non-http URLs such as `javascript:` and `mailto:` do not render.
- Disabled links do not render.
- No placeholder accounts, fake follower claims, fake partnerships, or fake social proof were added.

## Footer Placement

The footer brand copy is Dracula-first:

> A quiet digital reading room beginning with Dracula by Bram Stoker. Bengali Gothic and other classics are moving through the rights-safe pipeline.

The social block renders directly below the footer contact email address:

1. `sales@reoenterprise.org`
2. `Follow The Earnalism`
3. Configured social icon links

If no valid social URLs are configured, the entire social block returns `null` and leaves no empty icon row.

## Accessibility

- Each icon-only link has an `aria-label`.
- Each icon has hidden text for screen readers.
- Links are keyboard navigable.
- Focus-visible styling uses the existing gold brand ring.
- Tap targets are 44 by 44 pixels.

## Security

- Social links open in a new tab with `target="_blank"`.
- External links use `rel="noopener noreferrer"`.
- URL validation allows only `http:` and `https:`.
- No external APIs are called.
- No emails, social posts, ads, or provider actions are triggered.

## Static SEO Snapshot Compatibility

PR #40 static SEO snapshots are now on `main`. This PR preserves `frontend/package.json` `postbuild`, so the normal frontend build regenerates snapshots and footer social links appear only when valid `REACT_APP_*` social URLs are configured.

## Manual Review Checklist

- Configure one real URL, rebuild, and confirm only that icon appears.
- Configure multiple real URLs and confirm order: Instagram, YouTube, Facebook, LinkedIn, X, WhatsApp, Telegram.
- Confirm mobile footer layout remains centered and tap-friendly.
- Confirm Dracula remains the only live approved reading title.
- Confirm Kshudhita Pashan remains pipeline-only.
