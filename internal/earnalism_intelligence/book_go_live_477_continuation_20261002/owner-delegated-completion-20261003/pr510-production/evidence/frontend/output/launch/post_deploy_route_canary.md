# Post-Deploy Route Canary

Status: `PASS`

Removed/demo routes must return `410` or `404`, must not redirect, must not serve the generic SPA shell, and must include exactly `X-Robots-Tag: noindex, nofollow, noarchive`.

| Path | Status | Redirected | X-Robots-Tag | Generic Shell | Issues |
| --- | --- | --- | --- | --- | --- |
| /product/patterned-wrap-dress | 410 | False | noindex, nofollow, noarchive | False |  |
| /journal/denim-jackets | 410 | False | noindex, nofollow, noarchive | False |  |
| /journal/the-quiet-power-of-a-premium-bookstore-brand | 410 | False | noindex, nofollow, noarchive | False |  |
| /blog/lorem-ipsum | 410 | False | noindex, nofollow, noarchive | False |  |
| /post/sample-product | 410 | False | noindex, nofollow, noarchive | False |  |
| /shop | 410 | False | noindex, nofollow, noarchive | False |  |
| /shop/ | 410 | False | noindex, nofollow, noarchive | False |  |
| /shop/example | 410 | False | noindex, nofollow, noarchive | False |  |
| /fashion | 410 | False | noindex, nofollow, noarchive | False |  |
| /clothing | 410 | False | noindex, nofollow, noarchive | False |  |
| /category/fashion | 410 | False | noindex, nofollow, noarchive | False |  |
| /tag/fashion | 410 | False | noindex, nofollow, noarchive | False |  |
| /cart | 410 | False | noindex, nofollow, noarchive | False |  |
| /checkout | 410 | False | noindex, nofollow, noarchive | False |  |
| /my-account | 410 | False | noindex, nofollow, noarchive | False |  |
| /woocommerce | 410 | False | noindex, nofollow, noarchive | False |  |
| /woocommerce/test | 410 | False | noindex, nofollow, noarchive | False |  |
| /sample-product | 410 | False | noindex, nofollow, noarchive | False |  |
| /sample-product/test | 410 | False | noindex, nofollow, noarchive | False |  |
| /placeholder-product | 410 | False | noindex, nofollow, noarchive | False |  |
| /placeholder-product/test | 410 | False | noindex, nofollow, noarchive | False |  |
| /lorem-ipsum | 410 | False | noindex, nofollow, noarchive | False |  |
| /wp-content/uploads/demo.jpg | 410 | False | noindex, nofollow, noarchive | False |  |

## Rollback / Operator Instructions

- If any route is `BLOCKED`, keep launch status at `HOLD_FOR_FIXES`.
- Roll back the last Vercel production deployment or re-deploy the commit containing the removed-content route fix.
- Rerun `npm run launch:post-deploy-route-canary` after rollback or redeploy.
- Do not create `GO_FOR_CONTROLLED_PUBLICATION` or enable publication flags from a failed canary.
