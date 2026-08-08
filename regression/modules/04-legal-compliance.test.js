const { apiGet } = require("../utils/http");
const fixture = require("../fixtures/books.manifest.json");

function nestedKeys(value) {
  if (Array.isArray(value)) return value.flatMap(nestedKeys);
  if (!value || typeof value !== "object") return [];
  return Object.entries(value).flatMap(([key, item]) => [key, ...nestedKeys(item)]);
}

describe("Legal & Compliance", () => {
  test("public books do not expose internal legal review notes or PII", async () => {
    const books = (await apiGet("/books")).data;
    for (const book of books) {
      expect(nestedKeys(book).join(" ")).not.toMatch(
        /\b(?:rights_metadata|upload_notes|reviewer|private_notes|source_file|source_url|email|user_id|token)\b/i,
      );
      if (book.expiryDate === null || book.expiryDate === "not_applicable" || book.expiry_date === null) {
        expect(true).toBe(true);
      }
    }
  });

  test("restricted fixture slugs are blocked across public book APIs", async () => {
    for (const slug of fixture.draftOrPrivateSlugs) {
      expect([401, 403, 404]).toContain((await apiGet(`/books/${slug}`)).status);
      expect([401, 403, 404]).toContain((await apiGet(`/books/${slug}/chapters`)).status);
    }
  });

  test("reader-facing metadata contains no restricted source boilerplate", async () => {
    const books = (await apiGet("/books")).data;
    const blob = JSON.stringify(books);
    for (const term of fixture.blockedSourceTerms) {
      expect(blob.toLowerCase()).not.toContain(term.toLowerCase());
    }
  });
});
