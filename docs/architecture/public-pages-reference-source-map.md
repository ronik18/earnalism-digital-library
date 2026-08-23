# Public-page reference implementation map

The routes below use the existing React application, existing public API
endpoints, and existing controlled-release helpers. No backend or database
contract changes are part of this visual implementation.

| Route | Production rendering path | Design responsibilities |
| --- | --- | --- |
| `/` | `frontend/src/App.js` -> `frontend/src/pages/Home.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `frontend/src/components/ReferencePublicPages.css` | Library-room hero, two primary CTAs, feature rail, catalog shelf, Reading Pass explanation, approved listening rail, reader trust. |
| `/library` | `frontend/src/App.js` -> `frontend/src/pages/Library.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `frontend/src/components/ReferencePublicPages.css` | Ivory catalog layout, URL-backed search/sort/filters, responsive filter drawer, live/coming-soon/approved-audio shelves. |
| `/pricing` | `frontend/src/App.js` -> `frontend/src/pages/Pricing.jsx` -> `frontend/src/components/ReferencePublicPages.jsx` -> `frontend/src/components/ReferencePublicPages.css` | Dark Reading Pass hero, configured offer comparison, institutional and publisher routes, optional gift surface, payment/privacy trust and final CTA. |

Shared route chrome is provided by `frontend/src/components/Layout.jsx` and
`frontend/src/components/Header.jsx`. The automatic first-visit tour is now
opt-in through `?tour=1`, preventing it from obscuring the public reference
surfaces.

Release-sensitive rendering remains in the existing helpers:
`frontend/src/lib/audioReleaseSafety.js` and
`frontend/src/lib/controlledLaunch.js`.
