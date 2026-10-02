import { mergeDraculaBook } from "./lib/controlledLaunch";
import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("approved Book Detail direct-route contract", () => {
  const app = read("src/App.js");
  const vercel = JSON.parse(read("vercel.json"));

  test("keeps current and historical book routes ahead of the dynamic 404 policy", () => {
    expect(app).toContain('<Route path="/book/:slug" element={<BookDetail />} />');
    const rewrites = vercel.rewrites || [];
    const dynamicNotFound = rewrites.findIndex((rule) => rule.source === "/book/:slug" && rule.destination === "/api/not-found");
    expect(dynamicNotFound).toBeGreaterThanOrEqual(0);

    [
      "/book/a-white-heron",
      "/book/a-white-heron/",
      "/book/the-selfish-giant",
      "/book/the-selfish-giant/",
    ].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(dynamicNotFound);
    });
  });

  test("retains the true-unknown and retired status-document policies", () => {
    const rewrites = vercel.rewrites || [];
    expect(rewrites).toContainEqual({ source: "/book/:slug", destination: "/api/not-found" });
    expect(rewrites).toContainEqual({ source: "/product", destination: "/api/removed-content?path=/product" });
  });

  test("serves released Dracula through the existing API-gated Book Detail, Reader and Listener routes", () => {
    ["book", "reader", "listener"].forEach((kind) => {
      expect(app).not.toContain(`<Route path="/${kind}/dracula"`);
    });
    expect(app).toContain('<Route path="/book/:slug" element={<BookDetail />} />');
    expect(app).toContain('<Route path="/reader/:slug" element={<ReaderV2 />} />');
    expect(app).toContain('<Route path="/listener/:slug" element={<ListenerV2 />} />');
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/book/:slug" && rule.destination === "/api/not-found");
    ["/book/dracula", "/book/dracula/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
  });

  test("serves the historical Selfish Giant URL through the safe unavailable route", () => {
    ["book", "reader", "listener"].forEach((kind) => {
      expect(app).toContain(`<Route path="/${kind}/the-selfish-giant" element={<UnavailableTitle title="The Selfish Giant" slug="the-selfish-giant" />} />`);
    });
    const rewrites = vercel.rewrites || [];
    const genericNotFound = rewrites.findIndex((rule) => rule.source === "/book/:slug" && rule.destination === "/api/not-found");
    ["/book/the-selfish-giant", "/book/the-selfish-giant/"].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(genericNotFound);
    });
  });

  test("includes historical title URLs in the responsive route crawler", () => {
    const crawler = read("scripts/route-action-audit.mjs");
    [
      "/book/the-selfish-giant",
      "/book/the-selfish-giant/",
      "/book/moby-dick-or-the-whale",
      "/reader/moby-dick-or-the-whale/",
      "/book/the-count-of-monte-cristo",
      "/reader/the-count-of-monte-cristo/",
      "/book/dracula/",
      "/listener/the-selfish-giant",
      "/listener/the-selfish-giant/",
    ].forEach((route) => expect(crawler).toContain(`"${route}"`));
  });

  test("the unavailable-title component is noindex and has no title-content or manifest dependency", () => {
    const page = read("src/pages/UnavailableTitle.jsx");
    expect(page).toContain('robots: "noindex, nofollow"');
    expect(page).toContain("is not currently available.");
    expect(page).toContain("not part of the current public release");
    expect(page).toContain("No book text, reader session, or audio is available");
    expect(page).not.toMatch(/fetch\(|axios|manifest|audioUrl|chapter/i);
  });

  test("attributes the Radharani source layer without relicensing unrelated material", () => {
    const detail = read("src/pages/BookDetail.jsx");
    expect(detail).toContain('publicBook.slug === "radharani"');
    expect(detail).toContain('data-testid="radharani-source-attribution"');
    expect(detail).toContain("Bengali Wikisource transcription of the 1940 edition");
    expect(detail).toContain("https://creativecommons.org/licenses/by-sa/4.0/");
    expect(detail).toContain("The underlying Bengali literary work");
    expect(detail).toContain("This does not license Earnalism’s separate cover art");
  });
});


test("Dracula detail preserves exact current API cover bytes instead of legacy artwork aliases", () => {
  const current = {
    slug: "dracula",
    cover_image_url: "https://theearnalism.com/assets/books/dracula/dracula-front-5596e419.webp",
    cover_url: "https://theearnalism.com/assets/books/dracula/dracula-front-5596e419.webp",
    thumbnail_url: "https://theearnalism.com/assets/books/dracula/dracula-front-5596e419.webp",
    back_cover_image_url: "https://theearnalism.com/assets/books/dracula/dracula-back-c35004ef.webp",
    back_cover_url: "https://theearnalism.com/assets/books/dracula/dracula-back-c35004ef.webp",
    back_cover_thumbnail_url: "https://theearnalism.com/assets/books/dracula/dracula-back-c35004ef.webp",
    chapters: [{ id: "preface", title: "Preface" }],
  };
  const rendered = mergeDraculaBook(current);
  Object.keys(current).forEach((key) => expect(rendered[key]).toEqual(current[key]));
  expect(rendered.audiobook_enabled).toBe(false);
  expect(rendered.generate_audiobook).toBe(false);
});
