export const HERO_CAROUSEL_EXCLUDED_SLUGS = Object.freeze([
  "devdas",
  "debdas",
  "devdas-study-edition",
]);

const HERO_CAROUSEL_EXCLUDED_SLUG_SET = new Set(HERO_CAROUSEL_EXCLUDED_SLUGS);

function normalizeSlug(value) {
  return String(value || "").trim().toLowerCase();
}

function sprint1ApprovedSlugs(curation = {}) {
  const shelves = curation.shelves;
  const approved = Array.isArray(curation.approved_audiobooks)
    ? curation.approved_audiobooks
    : (shelves && typeof shelves === "object" && !Array.isArray(shelves))
      ? shelves.approved_audiobooks
      : [];

  if (!Array.isArray(approved)) return new Set();
  return new Set(
    approved
      .map((book) => normalizeSlug(book?.slug))
      .filter(Boolean),
  );
}

function resolveCarouselInput(curation = {}) {
  const hero = curation.hero || {};
  const approved = Array.isArray(curation.approved_audiobooks)
    ? curation.approved_audiobooks
    : (curation.shelves && typeof curation.shelves === "object" && !Array.isArray(curation.shelves))
      ? curation.shelves.approved_audiobooks || []
      : [];
  const shelves = Array.isArray(curation.shelves)
    ? curation.shelves
    : Array.isArray(curation.groups)
      ? curation.groups
      : [];
  const shelfBooks = shelves.flatMap((shelf = {}) => (
    Array.isArray(shelf.visible_books)
      ? shelf.visible_books
      : Array.isArray(shelf.books)
        ? shelf.books
        : []
  ));
  const fromAudio = Array.isArray(curation.selected_audiobooks)
    ? curation.selected_audiobooks
    : Array.isArray(curation.listening_rooms?.items)
      ? curation.listening_rooms.items
      : [];

  return [
    ...Array.isArray(hero.carousel_books) ? hero.carousel_books : [],
    ...Array.isArray(hero.featured_books) ? hero.featured_books : [],
    ...shelfBooks,
    ...approved,
    ...fromAudio,
  ];
}

export function heroCarouselBooks(curation = {}) {
  const sprint1Approved = sprint1ApprovedSlugs(curation);

  return Array.from(new Map(
    resolveCarouselInput(curation)
      .filter((book) => {
        const slug = normalizeSlug(book?.slug);
        if (!slug) return false;
        if (HERO_CAROUSEL_EXCLUDED_SLUG_SET.has(slug)) return false;
        if (book?.reader_enabled === false) return false;
        if (book?.cover_valid === false && !sprint1Approved.has(slug)) return false;
        if (!book?.front_cover_url) return false;
        if (!book?.book_url) return false;
        return true;
      })
      .map((book) => {
        const slug = normalizeSlug(book.slug);
        return [slug, {
          ...book,
          id: slug,
          slug,
          destination: book.book_url,
          coverSrc: book.front_cover_url,
          coverAlt: book.cover_alt_text || `${book.title} by ${book.author}`,
          locale: book.language || "und",
        }];
      }),
  ).values());
}

export function wrapCarouselIndex(index, itemCount) {
  if (!Number.isFinite(index) || itemCount <= 0) return 0;
  return ((Math.trunc(index) % itemCount) + itemCount) % itemCount;
}

export function stepCarouselIndex(activeIndex, direction, itemCount) {
  const step = direction < 0 ? -1 : 1;
  return wrapCarouselIndex(activeIndex + step, itemCount);
}

export function activeHeroSlide(slides, activeIndex) {
  if (!Array.isArray(slides) || slides.length === 0) return null;
  return slides[wrapCarouselIndex(activeIndex, slides.length)] || null;
}

export function relativeCarouselPosition(index, activeIndex, itemCount) {
  if (itemCount <= 1) return 0;
  const forwardDistance = wrapCarouselIndex(index - activeIndex, itemCount);
  return forwardDistance <= itemCount / 2
    ? forwardDistance
    : forwardDistance - itemCount;
}

export function carouselSlideState(index, activeIndex, itemCount) {
  const position = relativeCarouselPosition(index, activeIndex, itemCount);
  if (position === 0) return "active";
  if (position === -1) return "previous";
  if (position === 1) return "next";
  return position < 0 ? "far-previous" : "far-next";
}

export function canRotateCarousel({
  itemCount,
  reducedMotion,
  narrowViewport,
  manualPaused,
  interactionPaused,
  dragging,
  documentVisible,
  initialCoverReady,
}) {
  return (
    itemCount > 1
    && !reducedMotion
    && !narrowViewport
    && !manualPaused
    && !interactionPaused
    && !dragging
    && documentVisible
    && initialCoverReady
  );
}
