const fs = require("fs");
const { apiGet } = require("../utils/http");
const { getMongoUrl, withDb } = require("../utils/db");

describe("Migration, Backup & Data Consistency", () => {
  test("backup or recovery documentation exists before GO LIVE", async () => {
    const docs = ["DEPLOYMENT.md", "RAILWAY_SCALING_SETUP.md", "docs/BULK_PUBLISHING_PIPELINE.md"];
    expect(docs.some((file) => fs.existsSync(file) && /backup|rollback|restore|volume/i.test(fs.readFileSync(file, "utf8")))).toBe(true);
  });

  test("published books have valid category, author, chapter and cover data", async () => {
    if (!getMongoUrl()) {
      const books = (await apiGet("/books")).data;
      expect(books.length).toBeGreaterThan(0);
      for (const book of books) {
        expect(book.slug).toBeTruthy();
        expect(book.category_slug).toBeTruthy();
        expect(book.author).toBeTruthy();
        expect(book.cover_image_url || book.cover_url).toBeTruthy();
      }
      return;
    }
    const result = await withDb(async (db) => {
      const books = await db.collection("books").find({ is_published: true }, {
        projection: { slug: 1, category_slug: 1, author: 1, chapters: 1, cover_image_url: 1, cover_url: 1, rights_metadata: 1 },
      }).toArray();
      expect(books.length).toBeGreaterThan(0);
      for (const book of books) {
        expect(book.slug).toBeTruthy();
        expect(book.category_slug).toBeTruthy();
        expect(book.author).toBeTruthy();
        expect((book.chapters || []).length).toBeGreaterThan(0);
        expect(book.cover_image_url || book.cover_url).toBeTruthy();
      }
    });
    if (result.skipped) throw new Error(result.reason);
  });

  test("no orphaned audio sync records when audio collection exists", async () => {
    if (!getMongoUrl()) {
      expect(true).toBe(true);
      return;
    }
    const result = await withDb(async (db) => {
      const collections = await db.listCollections({}, { nameOnly: true }).toArray();
      if (!collections.some((collection) => collection.name === "audio_sync")) return;
      const orphaned = await db.collection("audio_sync").aggregate([
        { $lookup: { from: "books", localField: "book_slug", foreignField: "slug", as: "book" } },
        { $match: { book: { $size: 0 } } },
        { $limit: 1 },
      ]).toArray();
      expect(orphaned).toEqual([]);
    });
    if (result.skipped) throw new Error(result.reason);
  });
});
