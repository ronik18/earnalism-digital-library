import {
  activeHeroSlide,
  canRotateCarousel,
  carouselSlideState,
  heroCarouselBooks,
  relativeCarouselPosition,
  stepCarouselIndex,
  wrapCarouselIndex,
} from "./heroCarousel";

function book(index) {
  return {
    slug: `sprint1-${index}`,
    title: `Sprint 1 ${index}`,
    author: "Earnalism",
    reader_enabled: true,
    cover_valid: true,
    front_cover_url: `/assets/sprint1-${index}.webp`,
    cover_alt_text: `Sprint 1 ${index} by Earnalism`,
    book_url: `/book/sprint1-${index}`,
    language: "en",
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
  const [slide] = heroCarouselBooks({
    hero: {
      carousel_books: [
        valid,
        { ...valid },
        { ...book(1), cover_valid: false },
        { ...book(2), reader_enabled: false },
        { ...book(3), front_cover_url: "" },
      ],
    },
  });

  expect(slide).toMatchObject({
    ...valid,
    id: valid.slug,
    destination: valid.book_url,
    coverSrc: valid.front_cover_url,
    coverAlt: valid.cover_alt_text,
    locale: valid.language,
  });
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
  })).toHaveLength(1);
});

test("carousel excludes Devdas aliases from hero data without mutating the catalog records", () => {
  const globalCatalog = [
    { ...book(0), slug: "devdas", book_url: "/book/devdas" },
    { ...book(1), slug: "debdas", book_url: "/book/debdas" },
    { ...book(2), slug: "devdas-study-edition", book_url: "/book/devdas-study-edition" },
    book(3),
  ];

  const heroSlides = heroCarouselBooks({ hero: { carousel_books: globalCatalog } });

  expect(globalCatalog.map((item) => item.slug)).toContain("devdas");
  expect(heroSlides.map((item) => item.slug)).toEqual(["sprint1-3"]);
  expect(heroSlides.some((item) => /devdas|debdas/i.test(`${item.slug} ${item.coverSrc} ${item.coverAlt}`))).toBe(false);
});

test("active cover, metadata, route, and accessible identity share one slide object", () => {
  const slides = heroCarouselBooks({ hero: { carousel_books: [book(0), book(1), book(2)] } });
  const slide = activeHeroSlide(slides, 1);

  expect(slide).toBe(slides[1]);
  expect(slide).toMatchObject({
    id: "sprint1-1",
    title: "Sprint 1 1",
    author: "Earnalism",
    coverSrc: "/assets/sprint1-1.webp",
    destination: "/book/sprint1-1",
    coverAlt: "Sprint 1 1 by Earnalism",
  });
  expect(activeHeroSlide(slides, 3)).toBe(slides[0]);
  expect(activeHeroSlide([], 0)).toBeNull();
});

test.each([4, 6, 10])("carousel wraps circular indexes for a %i-item data set", (itemCount) => {
  expect(wrapCarouselIndex(-1, itemCount)).toBe(itemCount - 1);
  expect(wrapCarouselIndex(itemCount, itemCount)).toBe(0);
  expect(wrapCarouselIndex(itemCount + 1, itemCount)).toBe(1);
  expect(stepCarouselIndex(0, -1, itemCount)).toBe(itemCount - 1);
  expect(stepCarouselIndex(itemCount - 1, 1, itemCount)).toBe(0);
});

test("carousel calculates stable previous, active, next, and hidden positions", () => {
  expect(relativeCarouselPosition(5, 0, 6)).toBe(-1);
  expect(relativeCarouselPosition(0, 0, 6)).toBe(0);
  expect(relativeCarouselPosition(1, 0, 6)).toBe(1);
  expect(carouselSlideState(5, 0, 6)).toBe("previous");
  expect(carouselSlideState(0, 0, 6)).toBe("active");
  expect(carouselSlideState(1, 0, 6)).toBe("next");
  expect(carouselSlideState(2, 0, 6)).toBe("far-next");
  expect(carouselSlideState(4, 0, 6)).toBe("far-previous");
});

test("autoplay fails closed for every pause and stability gate", () => {
  const ready = {
    itemCount: 6,
    reducedMotion: false,
    narrowViewport: false,
    manualPaused: false,
    interactionPaused: false,
    dragging: false,
    documentVisible: true,
    initialCoverReady: true,
  };

  expect(canRotateCarousel(ready)).toBe(true);
  [
    ["reducedMotion", true],
    ["narrowViewport", true],
    ["manualPaused", true],
    ["interactionPaused", true],
    ["dragging", true],
    ["documentVisible", false],
    ["initialCoverReady", false],
    ["itemCount", 1],
  ].forEach(([property, value]) => {
    expect(canRotateCarousel({ ...ready, [property]: value })).toBe(false);
  });
});
