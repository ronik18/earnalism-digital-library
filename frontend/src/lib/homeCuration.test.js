import { getHomeCurationSnapshot, normalizeHomeCuration, shelfMode } from "./homeCuration";

test("shelf modes remain bounded and explicit", () => {
  expect([0, 1, 2, 3, 6, 8].map(shelfMode)).toEqual(["Zero", "Spotlight", "Duo", "Trio", "Runway", "Overflow"]);
});

test("curation removes duplicate or coverless books", () => {
  const result = normalizeHomeCuration({ shelves: [{ id: "bengali-classics", books: [{ slug: "a", title: "A", cover_image_url: "/a" }, { slug: "a", title: "A2", cover_image_url: "/a2" }, { slug: "b", title: "B" }] }] });
  expect(result.shelves[0].books.map((book) => book.slug)).toEqual(["a"]);
  expect(result.shelves[0].mode).toBe("Spotlight");
});

test("hero carousel books are canonical-cover normalized and deduplicated", () => {
  const result = normalizeHomeCuration({
    hero: {
      featured_books: [],
      carousel_books: [
        { slug: "a", title: "A", author: "Author", front_cover_url: "/a", reader_enabled: true },
        { slug: "a", title: "Duplicate", author: "Author", front_cover_url: "/duplicate", reader_enabled: true },
        { slug: "blocked", title: "Blocked", author: "Author", front_cover_url: "/blocked", cover_valid: false },
        { slug: "coverless", title: "Coverless", author: "Author" },
      ],
    },
  });

  expect(result.hero.carousel_books.map((book) => book.slug)).toEqual(["a"]);
  expect(result.hero.carousel_books[0].book_url).toBe("/book/a");
  expect(result.hero.carousel_books[0].cover_alt_text).toBe("A by Author");
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
  expect(snapshot.hero.carousel_books.length).toBeGreaterThanOrEqual(4);
});
