import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("My Library direct-route contract", () => {
  const app = read("src/App.js");
  const vercel = JSON.parse(read("vercel.json"));
  const snapshots = read("scripts/generate-static-seo-snapshots.mjs");
  const snapshotVerifier = read("scripts/verify-static-seo-snapshots.mjs");
  const seoAssets = read("scripts/generate-seo-assets.mjs");

  test("keeps My Library lazy-loaded and ahead of the wildcard route", () => {
    expect(app).toContain('MyLibrary: () => import("./pages/MyLibrary")');
    expect(app).toContain('<Route path="/my-library" element={<MyLibrary />} />');
    expect(app.indexOf('<Route path="/my-library" element={<MyLibrary />} />')).toBeLessThan(app.indexOf('<Route path="*" element={<NotFound />} />'));
  });

  test("allows only the private My Library route through the explicit SPA policy", () => {
    const rewrites = vercel.rewrites || [];
    const fallback = rewrites.findIndex((rule) => rule.source.startsWith("/((?!static/"));
    ["/my-library", "/my-library/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(fallback);
    });
    expect(rewrites[fallback]).toEqual(expect.objectContaining({ destination: "/api/not-found" }));
  });

  test("ships a noindex, authenticated-private static snapshot outside the sitemap", () => {
    expect(snapshots).toContain('path: "/my-library"');
    expect(snapshots).toContain('snapshot_classification: "AUTHENTICATED_PRIVATE"');
    expect(snapshotVerifier).toContain('"/my-library"');
    expect(seoAssets).toContain('"Disallow: /my-library"');
    expect(seoAssets).not.toContain('path: "/my-library"');
  });

  test("applies no-store cache headers only to normalized My Library requests", () => {
    const headers = vercel.headers || [];
    ["/my-library", "/my-library/"].forEach((source) => {
      expect(headers).toEqual(expect.arrayContaining([
        expect.objectContaining({
          source,
          headers: expect.arrayContaining([
            expect.objectContaining({ key: "Cache-Control", value: "private, no-store" }),
          ]),
        }),
      ]));
    });
  });
});
