export const HERO_CAROUSEL_EXCLUDED_SLUGS = Object.freeze([
  "devdas",
  "debdas",
  "devdas-study-edition",
]);

const HERO_CAROUSEL_EXCLUDED_SLUG_SET = new Set(HERO_CAROUSEL_EXCLUDED_SLUGS);

function normalizeSlug(value) {
  return String(value || "").trim().toLowerCase();
}

function resolveCarouselInput(curation = {}) {
  const hero = curation.hero || {};
  // `hero.carousel_books` is the server-owned Sprint1 allowlist. Do not
  // rebuild the hero from shelves or audiobook collections: those are valid
  // for their own surfaces, but are not a hero publication contract.
  return [
    ...Array.isArray(hero.carousel_books) ? hero.carousel_books : [],
    ...(Array.isArray(hero.carousel_books) && hero.carousel_books.length > 0
      ? []
      : Array.isArray(hero.featured_books) ? hero.featured_books : []),
  ];
}

export function heroCarouselBooks(curation = {}) {
  return Array.from(new Map(
    resolveCarouselInput(curation)
      .filter((book) => {
        const slug = normalizeSlug(book?.slug);
        if (!slug) return false;
        if (HERO_CAROUSEL_EXCLUDED_SLUG_SET.has(slug)) return false;
        if (book?.reader_enabled === false) return false;
        if (book?.cover_valid === false) return false;
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
