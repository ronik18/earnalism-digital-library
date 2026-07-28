import {
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
