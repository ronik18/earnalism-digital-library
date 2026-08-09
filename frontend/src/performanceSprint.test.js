import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("Home performance sprint contract", () => {
  test("prerenders and hydrates the real app without a temporary preview replacement", () => {
    const html = read("public/index.html");
    const entry = read("src/index.js");
    const snapshots = read("scripts/generate-static-seo-snapshots.mjs");

    expect(html).not.toMatch(/loading preview|root\.innerHTML/i);
    expect(entry).toContain("hydrateRoot");
    expect(entry).toContain('dataset.prerendered === "home"');
    expect(snapshots).toContain("renderHomeApp");
    expect(snapshots).toContain('data-prerendered="home"');
  });

  test("keeps noncritical Home modules and Reader CSS out of the initial route bundle", () => {
    const home = read("src/pages/Home.jsx");
    const globalStyles = read("src/index.css");
    const readerStyles = read("src/pages/ReaderRoute.css");

    expect(home).toContain('lazy(() => import("../components/HomeListeningRoom"))');
    expect(home).toContain('lazy(() => import("../components/HomeShelfArchitecture"))');
    expect(home).toContain("<DeferredMount");
    expect(globalStyles).not.toContain(".premium-reader {");
    expect(readerStyles).toContain(".premium-reader {");
  });

  test("splits anonymous hero and listening data without blocking the initial shell", () => {
    const home = read("src/pages/Home.jsx");
    const surfaces = read("src/lib/homeSurfaces.js");
    const listening = read("src/components/HomeListeningRoom.jsx");
    const vercel = read("vercel.json");

    expect(home).toContain("getHomeHeroSnapshot()");
    expect(home).toContain("fetchHomeHero(controller.signal)");
    expect(home).not.toContain("fetchHomeCuration(controller.signal)");
    expect(listening).toContain("fetchHomeListening(controller.signal, 3)");
    expect(surfaces).toContain('credentials: "omit"');
    expect(surfaces).toContain('"/home/hero"');
    expect(surfaces).toContain('`/home/listening?limit=${boundedLimit}`');
    expect(vercel).toContain('"source": "/api/home/hero"');
    expect(vercel).toContain('"source": "/api/home/listening"');
  });

  test("ships responsive immutable brand and hero assets plus field metrics", () => {
    const entry = read("src/index.js");
    const brand = read("src/components/BrandMark.jsx");
    const vercel = read("vercel.json");
    const assetNames = [
      "earnalism-brand-lockup-320.avif",
      "earnalism-brand-lockup-320.webp",
      "earnalism-brand-lockup-640.avif",
      "earnalism-brand-lockup-640.webp",
    ];

    assetNames.forEach((name) => {
      const stat = fs.statSync(path.join(root, "public/assets/performance", name));
      expect(stat.size).toBeLessThan(80000);
    });
    expect(brand).toContain('width="640"');
    expect(brand).toContain('height="192"');
    expect(vercel).toContain('"source": "/assets/hero/(.*)"');
    expect(entry).toContain("injectSpeedInsights");
  });
});
