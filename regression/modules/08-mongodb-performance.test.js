const expectedIndexes = require("../config/expected-indexes.json");
const { apiGet } = require("../utils/http");
const { getMongoUrl, withDb } = require("../utils/db");

function sameKeys(actual, expected) {
  return JSON.stringify(actual) === JSON.stringify(expected);
}

describe("MongoDB Index & Query Performance", () => {
  test("required indexes exist when Mongo is configured, otherwise public queries stay healthy", async () => {
    if (!getMongoUrl()) {
      const books = await apiGet("/books");
      const categories = await apiGet("/categories");
      expect(books.ok).toBe(true);
      expect(categories.ok).toBe(true);
      expect(books.ms).toBeLessThan(5000);
      expect(categories.ms).toBeLessThan(5000);
      return;
    }
    const result = await withDb(async (db) => {
      for (const [collectionName, expected] of Object.entries(expectedIndexes)) {
        const indexes = await db.collection(collectionName).indexes();
        for (const wanted of expected) {
          expect(indexes.some((idx) => sameKeys(idx.key, wanted.keys))).toBe(true);
        }
      }
      return { ok: true };
    });
    if (result.skipped) throw new Error(result.reason);
  });

  test("published books have no duplicate slugs or duplicate chapter orders", async () => {
    if (!getMongoUrl()) {
      const books = (await apiGet("/books")).data;
      const slugs = books.map((book) => book.slug);
      expect(new Set(slugs).size).toBe(slugs.length);
      return;
    }
    const result = await withDb(async (db) => {
      const duplicates = await db.collection("books").aggregate([
        { $group: { _id: "$slug", count: { $sum: 1 } } },
        { $match: { count: { $gt: 1 } } },
      ]).toArray();
      expect(duplicates).toEqual([]);
      const books = await db.collection("books").find({ is_published: true }, { projection: { slug: 1, chapters: 1 } }).toArray();
      for (const book of books) {
        const orders = (book.chapters || []).map((chapter) => chapter.order);
        expect(new Set(orders).size).toBe(orders.length);
      }
    });
    if (result.skipped) throw new Error(result.reason);
  });
});
