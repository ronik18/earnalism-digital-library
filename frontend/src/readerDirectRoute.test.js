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

  test("keeps the approved Dracula Reader and disabled Listener static routes ahead of generic 404 policy", () => {
    expect(app).not.toContain('<Route path="/reader/dracula" element={<UnavailableTitle />} />');
    expect(app).not.toContain('<Route path="/listener/dracula" element={<UnavailableTitle />} />');
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/reader/:slug" && rule.destination === "/api/not-found");
    const genericListenerNotFound = rewrites.findIndex((rule) => rule.source === "/listener/:slug" && rule.destination === "/api/not-found");
    ["/reader/dracula", "/reader/dracula/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/reader/dracula/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
    ["/listener/dracula", "/listener/dracula/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/listener/dracula/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericListenerNotFound);
    });
  });

  test("keeps cross-browser review on a live populated detail while checking Indira as held", () => {
    const crossBrowserReview = read("../scripts/verify_exact_primary_cross_browser.mjs");
    expect(crossBrowserReview).toContain('publicReaderExposureEnabled ? "a-white-heron" : "dracula"');
    expect(crossBrowserReview).toContain('["book-detail-held-desktop", "/book/bn-060"');
    expect(crossBrowserReview).toContain('"held-book": ["[data-testid=book-not-found]"]');
  });
  test("released Selfish Giant uses ordinary Reader and disabled Listener routes", () => {
    ["book", "reader", "listener"].forEach((kind) => {
      expect(app).not.toContain(`<Route path="/${kind}/the-selfish-giant"`);
    });
    expect(app).toContain('<Route path="/reader/:slug" element={<ReaderV2 />} />');
    expect(app).toContain('<Route path="/listener/:slug" element={<ListenerV2 />} />');
    ["reader", "listener"].forEach((kind) => {
      const generic = vercel.rewrites.findIndex((rule) => rule.source === `/${kind}/:slug` && rule.destination === "/api/not-found");
      [`/${kind}/the-selfish-giant`, `/${kind}/the-selfish-giant/`].forEach((source) => {
        const index = vercel.rewrites.findIndex((rule) => rule.source === source && rule.destination === `/${kind}/the-selfish-giant/index.html`);
        expect(index).toBeGreaterThanOrEqual(0);
        expect(index).toBeLessThan(generic);
      });
    });
  });

});
