export const HERO_BOOKS_PER_FRAME = 4;

export function heroCarouselBooks(curation = {}) {
  const suppliedCarousel = Array.isArray(curation?.hero?.carousel_books)
    ? curation.hero.carousel_books
    : [];

  return Array.from(new Map(
    suppliedCarousel
      .filter((book) => (
        book?.slug
        && book.reader_enabled !== false
        && book.cover_valid !== false
        && book.front_cover_url
      ))
      .map((book) => [book.slug, book]),
  ).values());
}

export function heroCarouselPages(books) {
  if (books.length === 0) return [];
  if (books.length <= HERO_BOOKS_PER_FRAME) return [books];

  const pageCount = Math.ceil(books.length / HERO_BOOKS_PER_FRAME);
  return Array.from(
    { length: pageCount },
    (_, pageIndex) => Array.from(
      { length: HERO_BOOKS_PER_FRAME },
      (_, offset) => books[
        ((pageIndex * HERO_BOOKS_PER_FRAME) + offset) % books.length
      ],
    ),
  );
}
