import {
  getHomeCurationCache,
  getHomeCurationSnapshot,
  normalizeHomeCuration,
  setHomeCurationCache,
  shelfMode,
} from "./homeCuration";

test("shelf modes remain bounded and explicit", () => {
  expect([0, 1, 2, 3, 6, 8].map(shelfMode)).toEqual(["Zero", "Spotlight", "Duo", "Trio", "Runway", "Overflow"]);
});

test("curation removes duplicate or coverless books", () => {
  const result = normalizeHomeCuration({ shelves: [{ id: "bengali-classics", books: [{ slug: "a", title: "A", cover_image_url: "/a" }, { slug: "a", title: "A2", cover_image_url: "/a2" }, { slug: "b", title: "B" }] }] });
  expect(result.shelves[0].books.map((book) => book.slug)).toEqual(["a"]);
  expect(result.shelves[0].mode).toBe("Spotlight");
});

test("curation supports object-based shelves payloads from sprint fixtures", () => {
  const result = normalizeHomeCuration({
    shelves: {
      bengali_classics: [{ slug: "b1", title: "B", front_cover_url: "/b1", reader_enabled: true }],
      english_classics: [{ slug: "e1", title: "E", front_cover_url: "/e1", reader_enabled: true }],
      "selected-listening": [{ slug: "a1", title: "A", front_cover_url: "/a1", reader_enabled: true, audiobook_enabled: true, audiobook_release_gate: "APPROVED", audio_qa_status: "QA_PASSED", audio_url: "/api/reader/book/a1/audiobook", audio_package_valid: true }],
      approved_audiobooks: [{ slug: "a2", title: "A2", front_cover_url: "/a2", reader_enabled: true, audiobook_enabled: true, audiobook_release_gate: "APPROVED", audio_qa_status: "QA_PASSED", audio_url: "/api/reader/book/a2/audiobook", audio_package_valid: true }],
    },
  });

  expect(result.shelves.map((shelf) => shelf.id).sort()).toEqual(["bengali_classics", "english_classics"].sort());
  expect(result.shelf_collage.groups.map((shelf) => shelf.id)).not.toContain("selected-listening");
  expect(result.selected_audiobooks.map((book) => book.slug)).toEqual(["a2"]);
});

test("curation preserves editorial shelf groups when object shelf facets are also present", () => {
  const result = normalizeHomeCuration({
    shelves: {
      reader_favorites: [{ slug: "facet", title: "Facet", front_cover_url: "/facet" }],
    },
    shelf_collage: {
      groups: [{ id: "editorial", books: [{ slug: "book", title: "Book", front_cover_url: "/book" }] }],
    },
  });

  expect(result.groups.map((shelf) => shelf.id)).toEqual(["editorial"]);
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

test("home curation uses localStorage cache with TTL", () => {
  const store = new Map();
  const mockLocalStorage = {
    getItem: (key) => store.get(key) || null,
    setItem: (key, value) => {
      store.set(key, value);
    },
  };
  const previousLocalStorage = global.localStorage;
  Object.defineProperty(global, "localStorage", {
    configurable: true,
    value: mockLocalStorage,
  });

  const payload = normalizeHomeCuration({ hero: { featured_books: [{ slug: "cache-1", title: "Cache One", cover_image_url: "/cache.jpg", reader_enabled: true, book_url: "/book/cache-1" }] } });
  setHomeCurationCache(payload);
  const fromCache = getHomeCurationCache();

  if (previousLocalStorage) {
    Object.defineProperty(global, "localStorage", {
      configurable: true,
      value: previousLocalStorage,
    });
  } else {
    delete global.localStorage;
  }

  expect(fromCache?.hero?.featured_books?.map((book) => book.slug)).toEqual(["cache-1"]);
});
