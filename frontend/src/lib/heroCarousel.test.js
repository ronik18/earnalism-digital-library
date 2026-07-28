import {
  HERO_BOOKS_PER_FRAME,
  heroCarouselBooks,
  heroCarouselPages,
} from "./heroCarousel";

function book(index) {
  return {
    slug: `sprint1-${index}`,
    title: `Sprint 1 ${index}`,
    author: "Earnalism",
    reader_enabled: true,
    cover_valid: true,
    front_cover_url: `/assets/sprint1-${index}.webp`,
  };
}

test("carousel fails closed instead of importing general shelf books", () => {
  const shelfBook = book(0);

  expect(heroCarouselBooks({
    hero: { carousel_books: [] },
    literary_shelves: [{ books: [shelfBook] }],
  })).toEqual([]);
});

test("carousel deduplicates valid explicit books and rejects unsafe records", () => {
  const valid = book(0);

  expect(heroCarouselBooks({
    hero: {
      carousel_books: [
        valid,
        { ...valid },
        { ...book(1), cover_valid: false },
        { ...book(2), reader_enabled: false },
        { ...book(3), front_cover_url: "" },
      ],
    },
  })).toEqual([valid]);
});

test("carousel forms stable four-book frames and wraps the final frame", () => {
  const books = Array.from({ length: 5 }, (_, index) => book(index));
  const pages = heroCarouselPages(books);

  expect(HERO_BOOKS_PER_FRAME).toBe(4);
  expect(pages.map((page) => page.map((item) => item.slug))).toEqual([
    ["sprint1-0", "sprint1-1", "sprint1-2", "sprint1-3"],
    ["sprint1-4", "sprint1-0", "sprint1-1", "sprint1-2"],
  ]);
});
