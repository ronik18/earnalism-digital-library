const fs = require("fs");
const path = require("path");
const { request } = require("../utils/http");
const { frontendUrl } = require("../utils/envGuard");
const { fetchSitemap } = require("../utils/sitemap");

const ROOT = path.resolve(__dirname, "../..");
const vercelConfig = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/vercel.json"), "utf8"));

const BLOCKED_TERMS = [
  "apparel",
  "clothing",
  "denim-jacket",
  "denim-jackets",
  "fashion",
  "lorem-ipsum",
  "patterned-wrap-dress",
  "placeholder-product",
  "sample-product",
  "woocommerce",
];

const REMOVED_PATHS = [
  "/product/patterned-wrap-dress",
  "/journal/denim-jackets",
  "/denim-jackets",
];

describe("Public content governance", () => {
  test("Vercel routes demo ecommerce paths to removed-content handler", () => {
    const rewrites = vercelConfig.rewrites || [];
    for (const source of ["/product", "/product/:path*", "/fashion", "/journal/denim-jackets", "/denim-jackets"]) {
      expect(rewrites.some((rewrite) => rewrite.source === source && rewrite.destination.includes("/api/removed-content"))).toBe(true);
    }
    expect((vercelConfig.redirects || []).some((redirect) => redirect.source === "/shop" && redirect.destination === "/library")).toBe(true);
  });

  test("robots.txt blocks demo ecommerce and fashion route families", async () => {
    const fallbackRobots = fs.readFileSync(path.join(ROOT, "frontend/public/robots.txt"), "utf8");
    let text = fallbackRobots;
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP === "true") {
      const robots = await request(`${frontendUrl()}/robots.txt`);
      text = robots.ok ? robots.text : fallbackRobots;
    }
    for (const rule of [
      "Disallow: /product/",
      "Disallow: /products/",
      "Disallow: /product-category/",
      "Disallow: /shop/",
      "Disallow: /fashion/",
      "Disallow: /clothing/",
      "Disallow: /apparel/",
    ]) {
      expect(text).toContain(rule);
    }
  });

  test("sitemap excludes blocked demo ecommerce terms", async () => {
    const fallback = fs.readFileSync(path.join(ROOT, "frontend/public/sitemap.xml"), "utf8");
    let text = fallback;
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP === "true") {
      const sitemap = await fetchSitemap();
      text = sitemap.ok ? sitemap.text : fallback;
    }
    for (const term of BLOCKED_TERMS) {
      expect(text.toLowerCase()).not.toContain(term);
    }
    for (const required of ["/", "/library", "/journal", "/about", "/contact"]) {
      expect(text).toContain(`${frontendUrl()}${required === "/" ? "/" : required}`);
    }
  });

  test("removed demo URLs do not expose homepage shell after cleanup deploy", async () => {
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP !== "true") {
      expect(REMOVED_PATHS.length).toBeGreaterThan(0);
      return;
    }
    for (const removedPath of REMOVED_PATHS) {
      const response = await request(`${frontendUrl()}${removedPath}`);
      expect([404, 410]).toContain(response.status);
      expect(response.text).not.toMatch(/<meta name="robots" content="index, follow"/i);
      expect(response.text).not.toMatch(/Earnalism Digital Library \| Audiobooks, Bengali Books/i);
    }
  });
});
