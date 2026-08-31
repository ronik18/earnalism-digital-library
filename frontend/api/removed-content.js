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
const { renderBrandedStatusPage } = require("./_lib/render-branded-status-page");

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
  const retired = statusCode === 410;
  res.end(renderBrandedStatusPage({
    statusCode,
    documentTitle: `${retired ? "Gone" : "Not Found"} | Earnalism`,
    eyebrow: retired ? "410 · Retired route" : "404 · Page unavailable",
    heading: retired ? "This page is no longer available." : "This page is not on the shelf.",
    body: retired
      ? "The requested retired page is not part of The Earnalism. The library remains available."
      : "The requested page is not available. Explore the library or return home.",
    primaryAction: { href: "/library", label: "Browse Library" },
    secondaryAction: { href: "/", label: "Home" },
  }));
};
