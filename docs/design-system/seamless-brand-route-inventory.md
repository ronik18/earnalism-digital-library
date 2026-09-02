# Seamless brand route inventory

`seamless-brand-route-inventory.json` is the machine authority. This companion
table identifies the 19 current customer-shell review routes, their shell
owner, required desktop and mobile brand review, and the safe fixture class.

| Route | Classification | Shell / brand owner | Required review states | Fixture / production state |
| --- | --- | --- | --- | --- |
| `/` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/library` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/pricing` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/book/dracula` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/book/devdas` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/about` | `PUBLIC_INDEXABLE` | standalone About experience | desktop, mobile | public-safe |
| `/journal` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/journal/how-reading-shapes-better-founders` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/contact` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/micro-story` | `PUBLIC_INDEXABLE` | shared public header | desktop, mobile | public-safe |
| `/login` | `PUBLIC_NOINDEX` | auth shell | desktop, mobile | public-safe |
| `/signup` | `PUBLIC_NOINDEX` | auth shell | desktop, mobile | public-safe |
| `/account` | `AUTHENTICATED_PRIVATE` | account shell | desktop, mobile | sanitized account fixture |
| `/my-library` | `AUTHENTICATED_PRIVATE` | account shell | desktop, mobile | sanitized account fixture |
| `/reader/dracula` | `AUTHENTICATED_PRIVATE` | Reader experience | desktop, mobile | reader visual-safe fixture |
| `/listener/a-ghost-story` | `AUTHENTICATED_PRIVATE` | Listener experience | desktop, mobile | listener non-playable fixture |
| `/listener/dracula` | `AUTHENTICATED_PRIVATE` | Listener experience | desktop, mobile | listener non-playable fixture |
| `UNKNOWN_URL` | `NOT_FOUND` | NotFound shell | desktop, mobile | public-safe; noindex |
| `/product/patterned-wrap-dress` | `TOMBSTONED` | 410 tombstone | desktop, mobile | public-safe; noindex |

`UNKNOWN_URL` denotes the existing catch-all fallback rather than a concrete
customer route. The product path is an existing retired route recognized by
`frontend/api/removed-content.js`; it remains non-indexable.
