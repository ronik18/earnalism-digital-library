# Production Parity Report

Status: `PASS`

Removed/demo routes must return `410` or `404` with exactly `X-Robots-Tag: noindex, nofollow, noarchive`. Redirects, generic SPA shells, and HTTP 200 responses are launch blockers. `/shop` must not return `308`.

## Local Removed Routes

| Path | Status | Matched | X-Robots-Tag | Generic Shell |
| --- | --- | --- | --- | --- |
| /product/patterned-wrap-dress | 410 | removed-content | noindex, nofollow, noarchive | False |
| /journal/denim-jackets | 410 | removed-content | noindex, nofollow, noarchive | False |
| /journal/the-quiet-power-of-a-premium-bookstore-brand | 404 | removed-content | noindex, nofollow, noarchive | False |
| /blog/lorem-ipsum | 410 | removed-content | noindex, nofollow, noarchive | False |
| /post/sample-product | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop/ | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop/example | 410 | removed-content | noindex, nofollow, noarchive | False |
| /fashion | 410 | removed-content | noindex, nofollow, noarchive | False |
| /clothing | 410 | removed-content | noindex, nofollow, noarchive | False |
| /category/fashion | 410 | removed-content | noindex, nofollow, noarchive | False |
| /tag/fashion | 410 | removed-content | noindex, nofollow, noarchive | False |
| /cart | 410 | removed-content | noindex, nofollow, noarchive | False |
| /checkout | 410 | removed-content | noindex, nofollow, noarchive | False |
| /my-account | 410 | removed-content | noindex, nofollow, noarchive | False |
| /woocommerce | 410 | removed-content | noindex, nofollow, noarchive | False |
| /woocommerce/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /sample-product | 410 | removed-content | noindex, nofollow, noarchive | False |
| /sample-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /placeholder-product | 410 | removed-content | noindex, nofollow, noarchive | False |
| /placeholder-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /lorem-ipsum | 410 | removed-content | noindex, nofollow, noarchive | False |
| /wp-content/uploads/demo.jpg | 410 | removed-content | noindex, nofollow, noarchive | False |

## Production Removed Routes

Production network check was skipped.

## Raw Evidence Files

- `/private/var/folders/yd/zn1ydw_50ts7mj_ldjxbyd3m0000gn/T/pytest-of-ronikbasak/pytest-14/test_all_audit_writes_required0/launch/production_removed_routes_curl.txt`
- `/private/var/folders/yd/zn1ydw_50ts7mj_ldjxbyd3m0000gn/T/pytest-of-ronikbasak/pytest-14/test_all_audit_writes_required0/launch/production_removed_routes.json`

## Operator Verification Commands

```bash
for path in /product/patterned-wrap-dress /journal/denim-jackets /shop /shop/ /shop/example /fashion /clothing /woocommerce/test /sample-product/test /placeholder-product/test; do
  curl -i --max-time 10 "https://theearnalism.com$path" | sed -n '1,24p'
done
```
