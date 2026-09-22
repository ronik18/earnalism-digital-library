const fs = require("fs");
const path = require("path");
const { request, apiGet, mapLimit } = require("../utils/http");
const { fetchSitemap } = require("../utils/sitemap");
const { frontendUrl, isGoLive, isPr } = require("../utils/envGuard");
const perf = require("../config/performance.rules.json");
const publicAudioTruth = require("../../internal/audiobook_lab/release_gate/claimable_go_live_tranche.json");
const controlledLaunch = require("../../data/controlled_launch.json");

const GO_LIVE_BOOK_LIMIT = Number(process.env.REGRESSION_GO_LIVE_BOOK_LIMIT || 120);
const URL_CHECK_CONCURRENCY = Number(process.env.REGRESSION_URL_CHECK_CONCURRENCY || 8);
const APPROVED_PUBLIC_AUDIO_SLUGS = new Set(publicAudioTruth.approved_public_audio_slugs || []);
const CONTROLLED_AUDIO_SLUGS = new Set(controlledLaunch.audio_enabled_slugs || []);
const PUBLIC_AUDIO_RELEASE_HELD = controlledLaunch.public_reader_exposure_enabled !== true
  || controlledLaunch.public_audio_exposure_enabled !== true;
const ROOT = path.resolve(__dirname, "../..");

function controlledPublicationCover(slug) {
  const artifactPath = path.join(ROOT, "data", "controlled_publications", slug, "public_book.json");
  if (!fs.existsSync(artifactPath)) return "";
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  return artifact.cover_image_url || artifact.cover_url || artifact.thumbnail_url || "";
}

describe("URL, Path & Navigation", () => {
  test("sitemap.xml is reachable and public URLs do not 404", async () => {
    const sitemap = await fetchSitemap();
    expect(sitemap.ok).toBe(true);
    expect(sitemap.locs.length).toBeGreaterThan(0);
    const max = isGoLive() ? perf.crawl.goLiveMaxUrls : perf.crawl.prMaxUrls;
    for (const loc of sitemap.locs.slice(0, max)) {
      // PR regression validates the candidate's local frontend, not whichever
      // older release happens to be serving the production sitemap origin.
      // Keep production/go-live checks on the published absolute URL.
      const candidateLoc = isPr()
        ? new URL(new URL(loc).pathname + new URL(loc).search, frontendUrl()).toString()
        : loc;
      const response = await request(candidateLoc, { skipBody: true });
      expect(response.status).toBeLessThan(500);
      expect(response.status).not.toBe(404);
    }
  });

  test("cover images resolve as valid image resources", async () => {
    const allBooks = (await apiGet("/books")).data;
    const books = (PUBLIC_AUDIO_RELEASE_HELD
      ? allBooks
      : allBooks.filter((book) => APPROVED_PUBLIC_AUDIO_SLUGS.has(book.slug)))
      .slice(0, isGoLive() ? GO_LIVE_BOOK_LIMIT : 12);
    if (PUBLIC_AUDIO_RELEASE_HELD) {
      expect(CONTROLLED_AUDIO_SLUGS).toEqual(new Set());
      expect(allBooks.length).toBeGreaterThan(0);
      expect(allBooks.filter((book) => APPROVED_PUBLIC_AUDIO_SLUGS.has(book.slug))).toEqual([]);
    }
    if (!PUBLIC_AUDIO_RELEASE_HELD && books.length === 0 && isPr()) {
      for (const slug of APPROVED_PUBLIC_AUDIO_SLUGS) expect(CONTROLLED_AUDIO_SLUGS.has(slug)).toBe(true);
      return;
    }
    expect(books.length).toBeGreaterThan(0);
    await mapLimit(books, URL_CHECK_CONCURRENCY, async (book) => {
      const sourceCover = isPr() && CONTROLLED_AUDIO_SLUGS.has(book.slug)
        ? controlledPublicationCover(book.slug)
        : "";
      const url = book.cover_image_url || book.cover_url || book.thumbnail_url || sourceCover;
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
