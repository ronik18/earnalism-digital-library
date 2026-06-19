# Post-Deploy Verification

Launch remains `HOLD_FOR_FIXES` until these checks pass on production after the main-branch deployment.

Expected result for every route: HTTP `410` or `404`, no redirect, no generic SPA shell, and exactly `X-Robots-Tag: noindex, nofollow, noarchive`.

```bash
set -euo pipefail
for path in /product/patterned-wrap-dress /journal/denim-jackets /shop /shop/ /shop/example /fashion /clothing; do
  echo "==== $path"
  curl -i --max-time 10 "https://theearnalism.com$path" | sed -n '1,28p'
done
```

## Pass Criteria

- `/shop` and `/shop/` do not return `308`, `301`, `302`, or `307`.
- `/product/patterned-wrap-dress` does not serve the generic Earnalism shell.
- Removed/demo URLs stay out of `sitemap.xml`.
- Removed/demo URLs remain crawlable by `robots.txt` so crawlers can see the deindexing response.
