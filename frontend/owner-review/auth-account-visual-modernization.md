# Earnalism authentication and account modernization — owner review

## Scope reviewed

- `/login` — email/password and existing Google entry point, unchanged behavior.
- `/signup` — existing account registration, unchanged behavior.
- `/account` — existing Reading Pass balance, recent activity, signed-in devices, sign-out, and revoke-device action.

No customer Forgot Password or Reset Password route exists in the current router, so no password-recovery flow was added.

## Visual direction

The shared public header/footer and canonical Earnalism lockup remain in place. The authentication shell now uses a calm two-column reading-room layout on desktop and a compact lockup-first card on mobile. Account uses a clearly separated balance panel, continuation panel, device-management panel, and activity panel while retaining every existing data surface and action.

## Locked customer copy

> Read the first 3 pages free. Listening requires an active Reading Pass.

The obsolete Chapter-1 and free-audio wording is not used in these customer-authentication/account surfaces.

## Responsive owner review

| Viewport | Review focus |
| --- | --- |
| Desktop, 1440px | Canonical logo, header/footer continuity, calm two-column auth composition, readable account hierarchy. |
| Tablet, 768px | Single-column auth form, non-overflowing account panels, durable focus treatment. |
| Mobile, 390px | Lockup visibility, 44px controls, stacked account header/actions, scrollable transaction table without clipped page content. |

## Contract preservation

- No changes to authentication API calls, credentials/OTP handling, Google flow, token storage, redirects, wallet/ledger accounting, Reading Pass authorization, database schema, Reader, or Listener.
- Device revocation and sign-out retain their existing confirmation, API call, state update, redirect, and toast behavior.
- Automated responsive screenshots are produced under the ignored UAT evidence path for PR review; they contain no account or credential data.
