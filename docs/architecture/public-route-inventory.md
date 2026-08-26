# Earnalism public-route inventory

Audit date: 2026-08-26. This inventory is the implementation boundary for the
public-surface synchronization lane. Routes are taken from `frontend/src/App.js`,
the primary navigation, query destinations, static SEO definitions, and the
current production route audit.

| Public URL | Classification | Rendering source | Final family | SEO / truth notes |
| --- | --- | --- | --- | --- |
| `/` | Indexable discovery | `pages/Home.jsx`, home components | warm editorial discovery | Preview label uses the shared contract; audio rail remains truth-gated. |
| `/library` | Indexable discovery | `pages/Library.jsx`, `BookCard.jsx` | warm editorial browse | Bengali, English, and audiobook discovery are query states. |
| `/library?language=bn&availability=reader-ready` | Indexable query destination | `pages/Library.jsx` | Bengali Classics browse | No separate route is invented. |
| `/library?language=en` | Indexable query destination | `pages/Library.jsx` | English Classics browse | No separate route is invented. |
| `/library?availability=approved-audiobook` | Indexable query destination | `pages/Library.jsx` | approved-audio browse | Cards follow canonical audio approval only. |
| `/pricing` | Indexable commerce | `pages/Pricing.jsx`, `ReadingPass/*` | warm commerce | No payment or wallet behavior changes. |
| `/book/:slug` | Indexable book detail | `pages/BookDetail.jsx` | dark/light book detail | Read/listen actions remain release-truth derived. |
| `/reader/:slug` | Public noindex experience | `experiences-v2/reader/*` | dark reading room | Canonical-page authorization stays server authoritative. |
| `/listener/:slug` | Public noindex experience | `experiences-v2/listener/*` | dark listening room | No player or CTA without canonical audio approval. |
| `/about` | Indexable brand | `experiences-v2/about/*` | standalone dark trust page | Zero data API calls. |
| `/journal` | Indexable editorial | `pages/Journal.jsx` | warm editorial | Existing article API and metadata retained. |
| `/journal/:slug` | Indexable editorial article | `pages/JournalArticle.jsx` | warm editorial | Missing articles remain noindex. |
| `/contact` | Indexable support | `pages/Contact.jsx` | warm editorial support | Existing form endpoint and fields retained. |
| `/login`, `/signup`, `/signin` | Public noindex auth | `pages/Login.jsx`, `pages/Signup.jsx` | premium auth | Auth APIs, OAuth and token storage unchanged. |
| `/account` | Authenticated customer | `pages/Account.jsx` | premium account | Existing profile, pass, activity and device APIs only. |
| `/micro-story` | Public campaign | `pages/MicroStoryLanding.jsx` | warm editorial campaign | Existing campaign intent retained. |
| `/about-legacy`, `/reader-legacy/:slug`, `/listener-legacy/:slug` | Legacy rollback | legacy About/Reader + redirect | contained rollback | No public navigation expansion; no loop. |
| `/publishing`, `/publishing/*` | Redirect | `App.js` | redirect | Redirects to Library. |
| unknown URL | Not found | `pages/NotFound.jsx` | branded noindex fallback | Client router fallback; no dedicated server 410 route exists. |

There are no current public Terms, Privacy, Refund, forgot-password,
reset-password, register alias, dedicated 410, or separate category-route
implementations in the router. This lane does not invent routes or policy
content that the application does not currently support.

Admin and internal routes (`/admin/*`, `/secure-reader-test`) are not customer
public-surface redesign targets. `Reader`, `Listener`, and `About` are already
standalone V2 experiences and remain independently fail-closed.
