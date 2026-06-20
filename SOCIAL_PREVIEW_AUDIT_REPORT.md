# Social Preview Audit Report

Status: `PASS` locally.

Command:

```bash
npm run launch:social-preview-audit
npm run launch:social-preview-audit:prod
```

Output:

- `output/launch/social_preview_audit.json`
- `output/launch/social_preview_audit.md`

## Routes Audited

Local static snapshots audit:

| Route | Status | Evidence |
| --- | --- | --- |
| `/` | PASS | OG and Twitter tags are Dracula-first. |
| `/book/dracula` | PASS | OG and Twitter tags are Dracula-specific with approved Earnalism image. |
| `/library` | PASS | OG and Twitter tags state Dracula is the only live controlled reading release. |

Production audit after deploy:

| Route | Required raw HTML policy |
| --- | --- |
| `/` | Dracula-first homepage metadata; no broad live-catalog claim. |
| `/book/dracula` | Canonical `/book/dracula`, OG/Twitter tags, Book JSON-LD, no audiobook/listen-now claim. |
| `/library` | Dracula-only controlled release metadata. |
| `/reader/dracula` | `noindex,follow`, canonical `/book/dracula`, no audiobook/listen-now claim. |

The production command fails if any route is missing `og:title`, `og:description`, `og:image`, `og:url`, `twitter:card`, `twitter:title`, `twitter:description`, or `twitter:image`.

## Safety

- No social platform APIs were called.
- No ads were launched.
- No social posts were sent.
- No fake previews, ratings, reviews, or audiobook claims were added.
- Pre-deploy production failures remain a HOLD/WARN until the PR is deployed and rerun against `https://theearnalism.com`.
