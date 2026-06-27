const { request } = require("../utils/http");
const { frontendUrl } = require("../utils/envGuard");
const { fetchSitemap } = require("../utils/sitemap");
const rules = require("../config/seo.rules.json");

describe("SEO", () => {
  test("robots.txt exists and does not block public content", async () => {
    const robots = await request(`${frontendUrl()}/robots.txt`);
    expect(robots.ok).toBe(true);
    expect(robots.text).toMatch(/User-agent:\s*\*/i);
    expect(robots.text).toMatch(/Sitemap:/i);
    expect(robots.text).not.toMatch(/Disallow:\s*\/\s*$/im);
  });

  test("sitemap.xml is valid enough for public indexing", async () => {
    const sitemap = await fetchSitemap();
    expect(sitemap.ok).toBe(true);
    expect(sitemap.text).toMatch(/<urlset[\s>]/i);
    expect(sitemap.locs.length).toBeGreaterThan(0);
    expect(new Set(sitemap.locs).size).toBe(sitemap.locs.length);
  });

  test("public HTML shell has baseline SEO tags", async () => {
    const home = await request(`${frontendUrl()}/`);
    expect(home.ok).toBe(true);
    expect(home.text).toMatch(/<title>[^<]+<\/title>/i);
    if (rules.description.hardFailMissing) expect(home.text).toMatch(/name=["']description["']/i);
    if (rules.canonical.hardFailMissing) expect(home.text).toMatch(/rel=["']canonical["']/i);
    for (const tag of rules.openGraph.required) {
      expect(home.text).toMatch(new RegExp(`property=["']${tag}["']`, "i"));
    }
  });
});
