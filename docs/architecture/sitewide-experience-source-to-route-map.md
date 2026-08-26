# Primary Experience Source-to-Route Map

This Phase A map records the live rendering path, not a visual-only wrapper.
Each reference assignment is governed by
`docs/design-references/primary-experience-reference-map.json`.

| Route/state | Production page path | Shared shell | Truth source | Reference | Rollback |
| --- | --- | --- | --- | --- | --- |
| `/` desktop/mobile | `frontend/src/pages/Home.jsx` → `ReferenceHomeSurface` | `Layout`, `Header`, `Footer`, `EarnalismBrandLockup` | `homeSurfaces`, controlled launch, audio release adapter | `home-library-commerce-desktop.png` desktop; `responsive-reference-board.png` mobile | previous `Home` source remains behind the hidden legacy compatibility mount |
| `/library` and filters | `frontend/src/pages/Library.jsx` → `ReferenceLibrarySurface` | `Layout`, `Header`, `Footer` | `/books`, controlled launch, audio release adapter | `home-library-commerce-desktop.png` desktop; `responsive-reference-board.png` mobile | prior library markup remains a hidden compatibility mount |
| `/pricing` | `frontend/src/pages/Pricing.jsx` → `ReferenceCommerceSurface` | `Layout`, `Header`, `Footer` | existing payments offers/config APIs | `reading-pass-commerce.png` desktop; `responsive-reference-board.png` mobile | existing payment flow and handlers unchanged |
| `/book/:slug` | `frontend/src/pages/BookDetail.jsx` | `Layout`, dark reference `Header`, `Footer` | `/books/:slug`, reader manifest and `bookDetailPresentationForBook` | `reader-listener-bookdetail-desktop.png` | existing API/data path unchanged |
| `/reader/:slug` | `frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx` | `ExperienceShell`, `ExperienceHeader`, `EarnalismBrandLockup` | canonical-page and Reading Pass APIs | `reader-listener-bookdetail-desktop.png` desktop; `reader-listener-ecosystem.png` mobile | `/reader-legacy/:slug` |
| `/listener/:slug` | `frontend/src/experiences-v2/listener/ListenerExperienceV2Route.jsx` | `ExperienceShell`, `ExperienceHeader`, `EarnalismBrandLockup` | manifest release truth and Reading Pass audio lease API | `reader-listener-bookdetail-desktop.png` desktop; `reader-listener-ecosystem.png` mobile | `/listener-legacy/:slug`; disabled titles redirect to Book Detail |
| `/about` | `frontend/src/experiences-v2/about/AboutExperienceV2Route.jsx` | `ExperienceShell`, `ExperienceHeader`, `EarnalismBrandLockup` | static truthful trust-card content; zero API calls | `reader-listener-ecosystem.png` mobile; responsive extension otherwise | `/about-legacy` |

## Contract boundaries

- `EarnalismBrandLockup` is the single visible lockup for the listed public
  and standalone experience shells.
- The reference images control layout and surface roles. Server-authoritative
  release, rights, access, and commercial data control what may be rendered.
- The customer access sentence is centralized in
  `frontend/src/lib/publicAccessCopy.js`: **Read the first 3 pages free.
  Listening requires an active Reading Pass.**
- No part of this mapping enables Dracula audio, changes canonical-page access,
  exposes media URLs, or changes payment and wallet behavior.
