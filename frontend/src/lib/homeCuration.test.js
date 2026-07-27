import { getHomeCurationSnapshot, normalizeHomeCuration, shelfMode } from "./homeCuration";

test("shelf modes remain bounded and explicit", () => {
  expect([0, 1, 2, 3, 6, 8].map(shelfMode)).toEqual(["Zero", "Spotlight", "Duo", "Trio", "Runway", "Overflow"]);
});

test("curation removes duplicate or coverless books", () => {
  const result = normalizeHomeCuration({ shelves: [{ id: "bengali-classics", books: [{ slug: "a", title: "A", cover_image_url: "/a" }, { slug: "a", title: "A2", cover_image_url: "/a2" }, { slug: "b", title: "B" }] }] });
  expect(result.shelves[0].books.map((book) => book.slug)).toEqual(["a"]);
  expect(result.shelves[0].mode).toBe("Spotlight");
});

test("bundled release snapshot keeps truthful hero books available before the runtime request resolves", () => {
  const snapshot = getHomeCurationSnapshot();
  expect(snapshot.source.truth_source).toBe("bundled_sprint1_release_snapshot");
  expect(snapshot.hero.featured_books.length).toBeGreaterThanOrEqual(4);
  expect(snapshot.hero.featured_books.slice(0, 4).every((book) => (
    book.reader_enabled !== false
      && book.cover_valid !== false
      && book.is_placeholder !== true
      && Boolean(book.front_cover_url)
  ))).toBe(true);
});
