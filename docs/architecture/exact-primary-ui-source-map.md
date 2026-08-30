# Exact primary UI source map

This map binds the owner-approved primary reference regions to the current
production-rendered implementation. Deterministic Reader and Listener fixture
states are compiled only with `REACT_APP_ENABLE_VISUAL_FIXTURES=1`; they never
enable production access or media playback.

| Route / reference state | Page component | Shared component / CSS | Fixture and truth adapter | Focused validation | Rollback checkpoint |
| --- | --- | --- | --- | --- | --- |
| `/` Home desktop and mobile | `frontend/src/components/ReferencePublicPages.jsx` (`ReferenceHomeSurface`) | `frontend/src/components/ReferencePublicPages.css`, `frontend/src/components/Header.css` | `frontend/src/lib/publicAccessCopy.js` | `Home.test.jsx`, `measure_primary_visual_structure.mjs` Home states | `e398e2f68` |
| `/library` desktop and mobile | `ReferenceLibrarySurface` | `ReferencePublicPages.css` | catalog API with release-safe fallback | `Library.test.jsx`, Library direct states | `78c514a74` |
| `/library` mobile filters | `ReferenceLibrarySurface` | `ReferencePublicPages.css` | existing filter state only | `ReferencePublicPages.test.jsx`, filter direct state | `78c514a74` |
| `/pricing` Reading Pass desktop/mobile | `ReferenceCommerceSurface` | `ReferencePublicPages.css`, `Header.css` | configured offers; local-only offer fixture for visual measurement; `publicAccessCopy.js` | `Pricing.test.jsx`, Commerce direct states | `a8fcb9d87` |
| mobile primary navigation | `frontend/src/components/Header.jsx` | `Header.css` | current public navigation map | `Header.navigation.test.js`, navigation direct state | `418456930` |
| `/book/:slug` desktop/mobile | `frontend/src/pages/BookDetail.jsx` | `BookDetailReference.css`, `Header.css` | `bookDetailPresentation.js` and controlled release metadata | `bookDetailPresentation.test.js`, Book Detail direct state | `cfe934268` |
| `/reader/:slug?visual-fixture=1` desktop/mobile | `experiences-v2/reader/ReaderExperienceV2Route.jsx`, `ReaderExperienceV2.jsx` | `reader-v2.css`, `experiences-v2.css` | `READER_V2_FIXTURE`; `readerPageAccess`; production remains server-authorized | `Reader.releaseTruth.test.js`, `Reader.mobileUx.test.js` | `57fcf357a` |
| `/listener/:slug?visual-fixture=1` desktop/mobile | `experiences-v2/listener/ListenerExperienceV2Route.jsx`, `ListenerExperienceV2.jsx` | `listener-v2.css`, `experiences-v2.css` | `listenerReleasePresentation`; visual fixture has no media URL; production remains pass-authorized from second zero | `listener-zero-free-audio.test.jsx`, `rla-v2.contract.test.js` | `57fcf357a` |
| `/about` mobile | `experiences-v2/about/AboutExperienceV2.jsx` | `about-v2.css`, `experiences-v2.css` | static truthful trust cards | About mobile direct state | `082f30913` |
| `/my-library` mobile | `frontend/src/pages/MyLibrary.jsx` | `MyLibrary.css`, `experiences-v2.css` | existing account context only; designed empty state while no saved-book API exists | account copy test and local fixture capture | `ddd6cb9c0` |
| `/account` Profile mobile | `frontend/src/pages/Account.jsx` | `styles/auth-account.css`, `experiences-v2.css` | existing `AuthContext` profile, Reading Pass, activity, and device fields | `authAccountTextRules.test.js`, sanitized fixture capture | pre-existing account approval |

Canonical logo: `frontend/src/components/EarnalismBrandLockup.jsx`; locked font
families: `frontend/public/index.html`, `frontend/src/App.js`,
`frontend/src/index.css`, and `frontend/src/design-system/tokens.css`.
