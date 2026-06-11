const { request, apiGet } = require("../utils/http");
const { fetchSitemap } = require("../utils/sitemap");
const { isGoLive } = require("../utils/envGuard");
const perf = require("../config/performance.rules.json");

describe("URL, Path & Navigation", () => {
  test("sitemap.xml is reachable and public URLs do not 404", async () => {
    const sitemap = await fetchSitemap();
    expect(sitemap.ok).toBe(true);
    expect(sitemap.locs.length).toBeGreaterThan(0);
    const max = isGoLive() ? perf.crawl.goLiveMaxUrls : perf.crawl.prMaxUrls;
    for (const loc of sitemap.locs.slice(0, max)) {
      const response = await request(loc, { skipBody: true });
      expect(response.status).toBeLessThan(500);
      expect(response.status).not.toBe(404);
    }
  });

  test("cover images resolve as valid image resources", async () => {
    const books = (await apiGet("/books")).data.slice(0, isGoLive() ? 500 : 12);
    for (const book of books) {
      const url = book.cover_image_url || book.cover_url || book.thumbnail_url;
      expect(url).toBeTruthy();
      const response = await request(url, { skipBody: true });
      expect(response.ok).toBe(true);
      expect(response.headers.get("content-type") || "").toMatch(/image|octet-stream/i);
    }
  });

  test("book to chapter navigation APIs are internally consistent", async () => {
    const books = (await apiGet("/books")).data.slice(0, isGoLive() ? 500 : 8);
    for (const book of books) {
      const chapters = (await apiGet(`/books/${book.slug}/chapters`)).data;
      expect(chapters.length).toBeGreaterThan(0);
      expect(chapters[0].id).toBeTruthy();
      const first = await apiGet(`/books/${book.slug}/chapters/${chapters[0].id}`);
      expect(first.ok).toBe(true);
      if (chapters[1]) {
        const second = await apiGet(`/books/${book.slug}/chapters/${chapters[1].id}`);
        expect(second.ok).toBe(true);
      }
    }
  });
});
