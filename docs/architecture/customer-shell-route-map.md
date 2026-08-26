# Customer-shell route map

This frontend-only modernization owns visible customer-shell composition, not
authorization, catalogue truth, payments, or the standalone v2 experiences.

| URL | Classification | Current → final shell path | Logo authority | Tests | Static SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | Public indexable | `Layout` shared header/footer; Home composition unchanged | `EarnalismBrandLockup` in header/footer | Header/footer matrix | Existing snapshot |
| `/library` | Public indexable | `Layout` shared header/footer; composition unchanged | `EarnalismBrandLockup` | Header matrix | Existing snapshot |
| `/pricing` | Public indexable | `Layout` shared header/footer; composition unchanged | `EarnalismBrandLockup` | Header matrix | Existing snapshot |
| `/login` | Public noindex | `Layout` + `AuthPageShell` | `EarnalismBrandLockup` | Login/auth shell | Client SEO noindex |
| `/signup` | Public noindex | `Layout` + `AuthPageShell` | `EarnalismBrandLockup` | Signup/auth shell | Client SEO noindex |
| `/account` | Authenticated customer | `Layout` customer account presentation | Shared header/footer | Account tests | Client SEO noindex |
| `/contact` | Public indexable | `Layout` editorial/public shell | Shared header/footer | Contact tests | Client SEO |
| `/journal`, `/journal/:slug` | Public indexable | `Layout` editorial/public shell | Shared header/footer | Journal/article tests | Client SEO + existing sitemap |
| `/about-legacy` | Legacy rollback | Existing legacy page inside `Layout` | Shared header/footer | Header matrix | No public navigation change |
| unknown route | Not found | `Layout` + `NotFound` | Shared header/footer | NotFound tests | Client SEO noindex |

No terms, privacy, refund, forgot-password, reset-password, or dedicated 410
route exists in the current route table. `Reader`, `Listener`, and `About` v2
remain standalone and are intentionally outside this PR; their logo adoption is
a later integration item.
