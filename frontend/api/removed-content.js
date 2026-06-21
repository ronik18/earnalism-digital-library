const BLOCKED_TERMS = [
  "add-to-cart",
  "apparel",
  "bookstore",
  "clothing",
  "denim",
  "denim-jacket",
  "denim-jackets",
  "fashion",
  "lorem-ipsum",
  "my-account",
  "patterned-wrap-dress",
  "placeholder-product",
  "sample-product",
  "woocommerce",
  "wp-admin",
  "wp-content",
  "wp-json",
];

function isBlockedPath(value = "") {
  const rawPath = String(value || "").toLowerCase();
  const path = rawPath.replace(/^https?:\/\/[^/]+/, "").split("?", 1)[0];
  const segments = new Set(path.split("/").filter(Boolean));
  const retiredRouteFamilies = new Set([
    "blog",
    "cart",
    "category",
    "checkout",
    "my-account",
    "post",
    "product",
    "products",
    "product-category",
    "sample-product",
    "shop",
    "tag",
    "woocommerce",
    "wp-admin",
    "wp-content",
    "wp-json",
  ]);
  return [...retiredRouteFamilies].some((segment) => segments.has(segment))
    || BLOCKED_TERMS.some((term) => rawPath.includes(term));
}

module.exports = function removedContent(req, res) {
  const path = req.query?.path || req.headers["x-original-path"] || req.url || "";
  const statusCode = isBlockedPath(path) ? 410 : 404;
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "public, max-age=3600, s-maxage=86400");
  res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive");
  res.end(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>${statusCode === 410 ? "Gone" : "Not Found"} | Earnalism</title>
  </head>
  <body style="font-family: Georgia, serif; max-width: 720px; margin: 12vh auto; padding: 0 24px; color: #2c1810; line-height: 1.7;">
    <p style="letter-spacing: .18em; text-transform: uppercase; color: #8f6b2d; font-size: .72rem;">Earnalism</p>
    <h1 style="color: #4A1C27; font-size: clamp(2rem, 6vw, 3.5rem); line-height: 1.05;">This page is no longer available.</h1>
    <p>The requested retired page is not part of The Earnalism.</p>
    <p><a href="/" style="color: #4A1C27;">Return to Earnalism</a></p>
  </body>
</html>`);
};
