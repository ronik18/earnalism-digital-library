# Production Parity Report

Status: `BLOCKED`

Removed/demo routes must return `410` or `404` with exactly `X-Robots-Tag: noindex, nofollow, noarchive`. Redirects, generic SPA shells, and HTTP 200 responses are launch blockers. `/shop` must not return `308`.

## Local Removed Routes

| Path | Status | Matched | X-Robots-Tag | Generic Shell |
| --- | --- | --- | --- | --- |
| /product/patterned-wrap-dress | 410 | removed-content | noindex, nofollow, noarchive | False |
| /journal/denim-jackets | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop/ | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop/example | 410 | removed-content | noindex, nofollow, noarchive | False |
| /fashion | 410 | removed-content | noindex, nofollow, noarchive | False |
| /clothing | 410 | removed-content | noindex, nofollow, noarchive | False |
| /woocommerce/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /sample-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /placeholder-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |

## Production Removed Routes

| URL | Status | Final URL | X-Robots-Tag | Generic Shell | Error |
| --- | --- | --- | --- | --- | --- |
| https://theearnalism.com/product/patterned-wrap-dress | 410 | https://theearnalism.com/product/patterned-wrap-dress | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/journal/denim-jackets | 410 | https://theearnalism.com/journal/denim-jackets | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/shop | 308 | https://theearnalism.com/library |  | False |  |
| https://theearnalism.com/shop/ | 308 | https://theearnalism.com/library |  | False |  |
| https://theearnalism.com/shop/example | 404 | https://theearnalism.com/shop/example | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/fashion | 410 | https://theearnalism.com/fashion | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/clothing | 410 | https://theearnalism.com/clothing | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/woocommerce/test | 410 | https://theearnalism.com/woocommerce/test | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/sample-product/test | 410 | https://theearnalism.com/sample-product/test | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/placeholder-product/test | 410 | https://theearnalism.com/placeholder-product/test | noindex, nofollow, noarchive | False |  |

## Raw Evidence Files

- `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/production_removed_routes_curl.txt`
- `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/production_removed_routes.json`

## Operator Verification Commands

```bash
for path in /product/patterned-wrap-dress /journal/denim-jackets /shop /shop/ /shop/example /fashion /clothing /woocommerce/test /sample-product/test /placeholder-product/test; do
  curl -i --max-time 10 "https://theearnalism.com$path" | sed -n '1,24p'
done
```
