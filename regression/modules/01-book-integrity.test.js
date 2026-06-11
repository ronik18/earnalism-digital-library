const { apiGet } = require("../utils/http");
const { isGoLive } = require("../utils/envGuard");
const fixture = require("../fixtures/books.manifest.json");

function sampleBooks(books) {
  return isGoLive() ? books : books.slice(0, Number(process.env.REGRESSION_PR_BOOK_LIMIT || 8));
}

describe("Book Integrity & Content Fidelity", () => {
  test("public books endpoint returns published metadata only", async () => {
    const response = await apiGet("/books");
    expect(response.ok).toBe(true);
    expect(Array.isArray(response.data)).toBe(true);
    expect(response.data.length).toBeGreaterThan(0);
    for (const book of response.data) {
      expect(book.slug).toBeTruthy();
      expect(book.title).toBeTruthy();
      expect(book.is_published).not.toBe(false);
      expect(book.rights_metadata).toBeUndefined();
      expect(book.upload_notes).toBeUndefined();
      expect(JSON.stringify(book)).not.toMatch(/source_url|reviewer|private_notes|password_hash|token/i);
    }
  });

  test("chapter order is strictly increasing and public detail stays metadata-only", async () => {
    const books = (await apiGet("/books")).data;
    for (const book of sampleBooks(books)) {
      const detail = await apiGet(`/books/${book.slug}`);
      expect(detail.ok).toBe(true);
      expect(JSON.stringify(detail.data.chapters || [])).not.toMatch(/<p>|chapter body|rights_metadata/i);

      const chaptersResponse = await apiGet(`/books/${book.slug}/chapters`);
      expect(chaptersResponse.ok).toBe(true);
      const chapters = chaptersResponse.data;
      expect(Array.isArray(chapters)).toBe(true);
      expect(chapters.length).toBeGreaterThan(0);
      const orders = chapters.map((chapter) => Number(chapter.order));
      expect(new Set(orders).size).toBe(orders.length);
      expect([...orders].sort((a, b) => a - b)).toEqual(orders);
      expect(new Set(chapters.map((chapter) => chapter.id).filter(Boolean)).size).toBe(chapters.filter((chapter) => chapter.id).length);
    }
  });

  test("draft or private fixture slugs are not publicly visible", async () => {
    for (const slug of fixture.draftOrPrivateSlugs) {
      const detail = await apiGet(`/books/${slug}`);
      expect([401, 403, 404]).toContain(detail.status);
      const chapters = await apiGet(`/books/${slug}/chapters`);
      expect([401, 403, 404]).toContain(chapters.status);
    }
  });

  test("reader-facing public content has no known source boilerplate terms", async () => {
    const books = (await apiGet("/books")).data;
    for (const book of sampleBooks(books)) {
      const blob = JSON.stringify(book);
      for (const term of fixture.blockedSourceTerms) {
        expect(blob.toLowerCase()).not.toContain(term.toLowerCase());
      }
    }
  });
});
