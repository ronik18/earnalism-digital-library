# Editorial, support, error-route, and static-SEO route map

This map is the implementation authority for the Editorial/Support phase. It
records the current React route table and the matching Vercel route policy as
of the `origin/main` base used for this PR. It deliberately excludes the
completed primary and Auth/Account visual surfaces from the implementation
scope.

## Public route family

| Route | Classification | Production source | Shell and branding | Static HTML and robots | This phase |
| --- | --- | --- | --- | --- | --- |
| `/journal` | `PUBLIC_INDEXABLE` | `src/pages/Journal.jsx` | `PublicPageFrame`, canonical lockup, editorial surface | Route-specific, indexable | Premium journal index and deterministic article contract |
| `/journal/:slug` | `PUBLIC_INDEXABLE` when published; `NOT_FOUND` otherwise | `src/pages/JournalArticle.jsx` | `PublicPageFrame`, canonical lockup, long-form editorial surface | Route-specific for verified public articles | Long-form reading layout and safe missing state |
| `/contact` | `PUBLIC_INDEXABLE` | `src/pages/Contact.jsx` | `PublicPageFrame`, canonical lockup, form shell | Route-specific, indexable | Accessible support form; existing API unchanged |
| `/micro-story` | `PUBLIC_INDEXABLE` | `src/pages/MicroStoryLanding.jsx` | `PublicPageFrame`, canonical lockup | Route-specific, indexable | `ACTIVE_CAMPAIGN`; preserve reader invitation and current UTM path |
| `/about` | `PUBLIC_INDEXABLE` | `experiences-v2/about/AboutExperienceV2Route.jsx` | Intentional standalone experience | Route-specific, indexable | Static SEO only; visual implementation out of scope |
| `/book/:slug` | `PUBLIC_INDEXABLE` for approved books | `src/pages/BookDetail.jsx` | Shared customer shell | Route-specific from public-safe controlled contract | Static SEO only; visual implementation out of scope |
| `/library`, `/pricing`, `/` | `PUBLIC_INDEXABLE` | Existing primary pages | Existing approved primary shells | Route-specific, indexable | Contract preservation only |
| `/login`, `/signup` | `PUBLIC_NOINDEX` | Existing approved auth pages | Existing auth shell | Safe route-specific noindex snapshot | No visual implementation |
| `/account` | `AUTHENTICATED_PRIVATE` | Existing approved account page | Existing account shell | Safe route-specific noindex snapshot | No visual implementation |
| `/reader/:slug`, `/listener/:slug` | `AUTHENTICATED_PRIVATE` | Existing standalone experiences | Intentional standalone shells | Safe noindex snapshots; no protected content | Static SEO only; preserve access gates |

## Error, internal, and rollback routes

| Route | Classification | Current policy | This phase |
| --- | --- | --- | --- |
| unknown URL | `NOT_FOUND` | `frontend/api/not-found.js` returns `404`, `X-Robots-Tag: noindex, nofollow, noarchive` | Branded 404 handler; no SPA 200 fallback |
| retired WordPress/commerce/demo families | `TOMBSTONED` | `frontend/api/removed-content.js` returns `410` for recognized retired paths | Branded 410 handler; preserve current rewrites and noindex |
| `/secure-reader-test` | `INTERNAL_TEST` | Vercel routes it to the 404 handler | Removed from production routing without deleting its local test harness |
| `/admin`, `/admin/login`, `/admin/launch-monitor` | `ADMIN_INTERNAL` | Existing client routes, authenticated server APIs | No consumer redesign; must stay noindex and out of the sitemap |
| `/about-legacy`, `/reader-legacy/:slug`, `/listener-legacy/:slug` | `LEGACY_ROLLBACK` | Existing rollback implementation/redirect | No public navigation or sitemap; retain for rollback until an owner-approved retirement PR |
| `/signin`, `/publishing`, `/publishing/*` | `REDIRECT` | Existing React redirects | Preserve destination and avoid loops |

## Route-policy notes

- No Terms, Privacy, or Refund route exists in the current customer route table;
  this phase does not fabricate legal content or routes.
- The public Journal set is sourced from the checked-in, public-safe editorial
  contract. The route-specific snapshots contain only title, excerpt, author,
  category, date, and cover metadata.
- Book, Reader, and Listener snapshot coverage is sourced from the approved
  public controlled-publication contract. Reader/Listener snapshots are
  `noindex` and never include protected pages or media URLs.
- The retirement owner is the Earnalism product owner. Retire rollback routes
  only in a later owner-approved cleanup after production rollback confidence
  is no longer required.
