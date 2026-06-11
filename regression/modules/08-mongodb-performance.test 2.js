const expectedIndexes = require("../config/expected-indexes.json");
const { getMongoUrl, withDb } = require("../utils/db");

const hasMongoUrl = Boolean(getMongoUrl());
const dbTest = hasMongoUrl ? test : test.skip;

function sameKeys(actual, expected) {
  return JSON.stringify(actual) === JSON.stringify(expected);
}

describe("MongoDB Index & Query Performance", () => {
  dbTest("required indexes exist for critical public collections", async () => {
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

  dbTest("published books have no duplicate slugs or duplicate chapter orders", async () => {
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
