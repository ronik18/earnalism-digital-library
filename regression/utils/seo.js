function metaContent(document, selector) {
  const node = document.querySelector(selector);
  return node ? node.getAttribute("content") || "" : "";
}

function publicPageHasNoindex(robots = "") {
  return /(^|,\s*)noindex(\s*,|$)/i.test(robots || "");
}

function jsonLdBlocks(document) {
  return [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map((node) => {
      try {
        return JSON.parse(node.textContent || "{}");
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

module.exports = { metaContent, publicPageHasNoindex, jsonLdBlocks };
