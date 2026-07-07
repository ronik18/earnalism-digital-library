const { request, apiGet, mapLimit } = require("../utils/http");
const { fetchSitemap } = require("../utils/sitemap");
const { isGoLive, isPr } = require("../utils/envGuard");
const perf = require("../config/performance.rules.json");
const claimableGoLiveTranche = require("../../internal/audiobook_lab/release_gate/claimable_go_live_tranche.json");
const controlledLaunch = require("../../data/controlled_launch.json");

const GO_LIVE_BOOK_LIMIT = Number(process.env.REGRESSION_GO_LIVE_BOOK_LIMIT || 120);
const URL_CHECK_CONCURRENCY = Number(process.env.REGRESSION_URL_CHECK_CONCURRENCY || 8);
const CLAIMABLE_SLUGS = new Set(claimableGoLiveTranche.claimable_10_10_reader_listener_ready || []);
const CONTROLLED_AUDIO_SLUGS = new Set(controlledLaunch.audio_enabled_slugs || []);

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
    const books = (await apiGet("/books")).data
      .filter((book) => CLAIMABLE_SLUGS.has(book.slug))
      .slice(0, isGoLive() ? GO_LIVE_BOOK_LIMIT : 12);
    if (books.length === 0 && isPr()) {
      for (const slug of CLAIMABLE_SLUGS) expect(CONTROLLED_AUDIO_SLUGS.has(slug)).toBe(true);
      return;
    }
    expect(books.length).toBeGreaterThan(0);
    await mapLimit(books, URL_CHECK_CONCURRENCY, async (book) => {
      const url = book.cover_image_url || book.cover_url || book.thumbnail_url;
      expect(url).toBeTruthy();
      const response = await request(url, { method: "HEAD", skipBody: true, timeoutMs: 20000 });
      expect(response.ok).toBe(true);
      expect(response.headers.get("content-type") || "").toMatch(/image|octet-stream/i);
    });
  });

  test("book to chapter navigation APIs are internally consistent", async () => {
    const books = (await apiGet("/books")).data.slice(0, isGoLive() ? GO_LIVE_BOOK_LIMIT : 8);
    await mapLimit(books, URL_CHECK_CONCURRENCY, async (book) => {
      const chapters = (await apiGet(`/books/${book.slug}/chapters`)).data;
      expect(chapters.length).toBeGreaterThan(0);
      expect(chapters[0].id).toBeTruthy();
      const first = await apiGet(`/books/${book.slug}/chapters/${chapters[0].id}`);
      expect(first.ok).toBe(true);
      if (chapters[1]) {
        const second = await apiGet(`/books/${book.slug}/chapters/${chapters[1].id}`);
        expect(second.ok).toBe(true);
      }
    });
  });
});
