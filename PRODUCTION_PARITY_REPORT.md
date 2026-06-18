# Production Parity Report

Status: `PASS`

## Local Removed Routes

| Path | Status | Matched | X-Robots-Tag | Generic Shell |
| --- | --- | --- | --- | --- |
| /product/patterned-wrap-dress | 410 | removed-content | noindex, nofollow, noarchive | False |
| /journal/denim-jackets | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop | 410 | removed-content | noindex, nofollow, noarchive | False |
| /shop/example | 410 | removed-content | noindex, nofollow, noarchive | False |
| /fashion | 410 | removed-content | noindex, nofollow, noarchive | False |
| /clothing | 410 | removed-content | noindex, nofollow, noarchive | False |
| /woocommerce/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /sample-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |
| /placeholder-product/test | 410 | removed-content | noindex, nofollow, noarchive | False |

## Production Removed Routes

| URL | Status | X-Robots-Tag | Generic Shell | Error |
| --- | --- | --- | --- | --- |
| https://theearnalism.com/product/patterned-wrap-dress | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/journal/denim-jackets | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/shop | 308 |  | False |  |
| https://theearnalism.com/shop/example | 404 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/fashion | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/clothing | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/woocommerce/test | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/sample-product/test | 410 | noindex, nofollow, noarchive | False |  |
| https://theearnalism.com/placeholder-product/test | 410 | noindex, nofollow, noarchive | False |  |

## Operator Verification Commands

```bash
for path in /product/patterned-wrap-dress /journal/denim-jackets /shop /shop/example /fashion /clothing /woocommerce/test /sample-product/test /placeholder-product/test; do
  curl -i -L --max-time 10 "https://theearnalism.com$path" | sed -n '1,20p'
done
```
