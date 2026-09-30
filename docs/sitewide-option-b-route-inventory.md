# Option B sitewide route inventory

Inventory of customer-facing routes and route families declared in `frontend/src/App.js`.
Admin and test harness routes are identified separately and remain outside the public design migration.

| Route / state | Component or family | Design migration scope |
| --- | --- | --- |
| `/` | Home / Option B | Reference implementation; preserve release-aware audio and commercial copy |
| `/library` | Library | Public discovery; search, query filters, language, format, release status, empty/error states |
| `/book/:slug` | BookDetail | Dynamic book detail; loading, unavailable, network failure, reader entry, conditional audio |
| `/journal` | Journal | Editorial index, filters, loading/error/empty state |
| `/journal/:slug` | JournalArticle | Editorial article and unavailable article state |
| `/about`, `/about-legacy` | About | Shared About content; legacy alias preserved |
| `/contact` | Contact | Contact form, intent query states, success/error |
| `/privacy`, `/terms`, `/copyright` | LegalPages | Legal copy and reading measure preserved |
| `/pricing` | Pricing / Reading Pass | Runtime pricing, payment entry, unavailable/test configuration states |
| `/micro-story` | MicroStoryLanding | Public campaign/editorial landing page |
| `/login`, `/signin` | Login / redirect | Authentication and continuation states; `/signin` redirects to `/login` |
| `/signup` | Signup | Authentication and account creation |
| `/account` | Account | Authenticated profile, sessions, wallet/Reading Pass status |
| `/my-library` | MyLibrary | Authenticated truthful empty state; `NA_PRODUCT_STATE` until a canonical saved-book or reading-history API exists |
| `/reader/:slug` | ReaderExperienceV2 | Immersive reader shell; preserve reading, preview and entitlement gates |
| `/reader-legacy/:slug` | ReaderLegacy | Legacy reader route and release-safe states |
| `/listener/:slug` | ListenerExperienceV2 | Immersive listening route; runtime release and authorization gates preserved |
| `/listener-legacy/:slug` | LegacyListenerRedirect | Redirects to legacy reader with listening intent; enforcement preserved |
| `/publishing`, `/publishing/*` | Redirect | Existing redirect to `/library` preserved |
| `*` | NotFound | Public recovery state |
| `/secure-reader-test` | SecureReaderHarness | Internal/test harness; excluded from customer-facing redesign |
| `/admin/login`, `/admin`, `/admin/launch-monitor` | Admin surfaces | Internal operations; excluded |
| Suspense fallback | PageFallback | Shared loading state for lazy public routes |
| Newsletter/contact form states | Component states | Existing submit behavior and error/status semantics preserved |

Search results, empty search, and filtered collection states are query-driven within `/library`; checkout outcomes and account access are handled by existing route/component flows rather than new routes in `App.js`.
