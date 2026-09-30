const { renderBrandedStatusPage } = require("./_lib/render-branded-status-page");

module.exports = function notFound(req, res) {
  const unavailableTitle = req.query?.title === "dracula" ? "Dracula" : "";
  res.statusCode = 404;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "public, max-age=300, s-maxage=3600");
  res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive");
  res.end(renderBrandedStatusPage({
    statusCode: 404,
    documentTitle: unavailableTitle ? `${unavailableTitle} unavailable | The Earnalism` : "Page not found | The Earnalism",
    eyebrow: unavailableTitle ? "Public title unavailable" : "404 · Page unavailable",
    heading: unavailableTitle ? `${unavailableTitle} is not currently available.` : "This page is not on the shelf.",
    body: unavailableTitle
      ? "This title is not in the current public catalogue. This page does not provide book text, a reader session, or audio. Explore the current library or return home."
      : "The link may be incomplete or the page may have moved. Explore the library or return home.",
    primaryAction: { href: "/library", label: "Browse Library" },
    secondaryAction: { href: "/", label: "Home" },
  }));
};
