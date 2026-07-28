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

export function wrapCarouselIndex(index, itemCount) {
  if (!Number.isFinite(index) || itemCount <= 0) return 0;
  return ((Math.trunc(index) % itemCount) + itemCount) % itemCount;
}

export function stepCarouselIndex(activeIndex, direction, itemCount) {
  const step = direction < 0 ? -1 : 1;
  return wrapCarouselIndex(activeIndex + step, itemCount);
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
