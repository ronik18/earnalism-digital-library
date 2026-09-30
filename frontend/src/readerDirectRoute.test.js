import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("approved Reader direct-route contract", () => {
  const app = read("src/App.js");
  const vercel = JSON.parse(read("vercel.json"));

  test("keeps the current A White Heron Reader route reachable before the generic reader 404 policy", () => {
    expect(app).toContain('<Route path="/reader/:slug" element={<ReaderV2 />} />');
    const rewrites = vercel.rewrites || [];
    const dynamicNotFound = rewrites.findIndex(
      (rule) => rule.source === "/reader/:slug" && rule.destination === "/api/not-found",
    );
    expect(dynamicNotFound).toBeGreaterThanOrEqual(0);

    [
      "/reader/a-white-heron",
      "/reader/a-white-heron/",
    ].forEach((source) => {
      const index = rewrites.findIndex(
        (rule) => rule.source === source && rule.destination === "/index.html",
      );
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(dynamicNotFound);
    });
  });

  test("keeps unknown reader slugs behind the explicit not-found policy", () => {
    expect(vercel.rewrites).toContainEqual({
      source: "/reader/:slug",
      destination: "/api/not-found",
    });
  });

  test("keeps the historical Dracula Reader and Listener URLs on the safe unavailable route", () => {
    expect(app).toContain('<Route path="/reader/dracula" element={<UnavailableTitle />} />');
    expect(app).toContain('<Route path="/listener/dracula" element={<UnavailableTitle />} />');
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/reader/:slug" && rule.destination === "/api/not-found");
    const genericListenerNotFound = rewrites.findIndex((rule) => rule.source === "/listener/:slug" && rule.destination === "/api/not-found");
    ["/reader/dracula", "/reader/dracula/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
    ["/listener/dracula", "/listener/dracula/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericListenerNotFound);
    });
  });

  test("serves the held historical Selfish Giant Reader URL without entering the Reader", () => {
    expect(app).toContain('<Route path="/reader/the-selfish-giant" element={<UnavailableTitle title="The Selfish Giant" slug="the-selfish-giant" />} />');
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/reader/:slug" && rule.destination === "/api/not-found");
    ["/reader/the-selfish-giant", "/reader/the-selfish-giant/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
  });

  test("serves the held historical Selfish Giant Listener URL without entering the player", () => {
    expect(app).toContain('<Route path="/listener/the-selfish-giant" element={<UnavailableTitle title="The Selfish Giant" slug="the-selfish-giant" />} />');
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/listener/:slug" && rule.destination === "/api/not-found");
    ["/listener/the-selfish-giant", "/listener/the-selfish-giant/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
  });

  test("keeps cross-browser review on a live populated detail while checking Dracula as held", () => {
    const crossBrowserReview = read("../scripts/verify_exact_primary_cross_browser.mjs");
    expect(crossBrowserReview).toContain('publicReaderExposureEnabled ? "a-white-heron" : "dracula"');
    expect(crossBrowserReview).toContain('["book-detail-held-desktop", "/book/dracula"');
    expect(crossBrowserReview).toContain('"held-book": ["[data-testid=unavailable-title-page]"]');
  });
});
