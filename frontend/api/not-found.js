const { renderBrandedStatusPage } = require("./_lib/render-branded-status-page");

module.exports = function notFound(req, res) {
  res.statusCode = 404;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "public, max-age=300, s-maxage=3600");
  res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive");
  res.end(renderBrandedStatusPage({
    statusCode: 404,
    documentTitle: "Page not found | The Earnalism",
    eyebrow: "404 · Page unavailable",
    heading: "This page is not on the shelf.",
    body: "The link may be incomplete or the page may have moved. Explore the library or return home.",
    primaryAction: { href: "/library", label: "Browse Library" },
    secondaryAction: { href: "/", label: "Home" },
  }));
};
