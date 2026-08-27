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
  <body style="margin:0;background:#f8f4eb;color:#231f1b;font-family:Georgia,serif;line-height:1.65;">
    <main style="box-sizing:border-box;max-width:760px;margin:12vh auto;padding:28px;">
      <div style="border:1px solid #d8c8aa;border-radius:20px;background:#fffdf8;padding:clamp(28px,6vw,56px);box-shadow:0 18px 50px rgba(44,24,16,.08);">
        <img src="/assets/brand/earnalism-brand-lockup.png" width="640" height="192" alt="The Earnalism" style="display:block;width:min(260px,100%);height:auto;margin:0 0 40px;">
        <p style="margin:0 0 12px;color:#8d632e;font-family:Arial,sans-serif;font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;">${statusCode} · Retired route</p>
        <h1 style="margin:0;color:#4a1c27;font-size:clamp(36px,7vw,62px);line-height:1.04;">This page is no longer available.</h1>
        <p style="max-width:56ch;font-size:18px;">The requested retired page is not part of The Earnalism. The library remains available.</p>
        <p style="display:flex;flex-wrap:wrap;gap:12px;margin:30px 0 0;"><a href="/library" style="display:inline-block;border-radius:8px;background:#4a1c27;color:#fff8e8;padding:13px 18px;font-family:Arial,sans-serif;font-weight:700;text-decoration:none;">Browse Library</a><a href="/" style="display:inline-block;border:1px solid #8d632e;border-radius:8px;color:#4a1c27;padding:12px 18px;font-family:Arial,sans-serif;font-weight:700;text-decoration:none;">Home</a></p>
      </div>
    </main>
  </body>
</html>`);
};
