# Quiet Heritage public-page implementation map

The routes below use the existing React application, existing public API
endpoints, and existing controlled-release helpers. No backend or database
contract changes are part of this visual implementation.

| Route | Production rendering path | Design responsibilities |
| --- | --- | --- |
| `/` | `frontend/src/App.js` -> `frontend/src/pages/Home.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `ReferencePublicPages.css` + `styles/quiet-heritage.css` | Still-life hero (not the reference board), two release-safe CTAs, feature rail, catalog shelf, Reading Pass explanation, approved listening rail, reader trust. |
| `/library` | `frontend/src/App.js` -> `frontend/src/pages/Library.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `ReferencePublicPages.css` + `styles/quiet-heritage.css` | Light-beige editorial catalog, URL-backed search/sort/filters, responsive filter drawer, live/coming-soon/approved-audio shelves. |
| `/pricing` | `frontend/src/App.js` -> `frontend/src/pages/Pricing.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `ReferencePublicPages.css` + `styles/quiet-heritage.css` | Burgundy Reading Pass hero, configured offer comparison, institutional and publisher routes, optional gift surface, payment/privacy trust and final CTA. |

Shared route chrome is provided by `frontend/src/components/Layout.jsx` and
`frontend/src/components/Header.jsx`. Quiet Heritage does not style the
header; its compatibility remains a separately tracked concern. The automatic first-visit tour is now
opt-in through `?tour=1`, preventing it from obscuring the public reference
surfaces.

Release-sensitive rendering remains in the existing helpers:
`frontend/src/lib/audioReleaseSafety.js` and
`frontend/src/lib/controlledLaunch.js`.

The customer Account uses real activity, Reading Pass, and device data. Because
there is no supported saved-title/resume contract, its primary continuation
action is the Library rather than a hardcoded book route.
