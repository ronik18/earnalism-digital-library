const { frontendUrl } = require("./envGuard");
const { request } = require("./http");

function extractLocs(xml) {
  return [...String(xml || "").matchAll(/<loc>([^<]+)<\/loc>/gi)].map((match) => match[1].trim());
}

async function fetchSitemap() {
  const response = await request(`${frontendUrl()}/sitemap.xml`);
  return {
    ...response,
    locs: extractLocs(response.text),
  };
}

module.exports = { extractLocs, fetchSitemap };
