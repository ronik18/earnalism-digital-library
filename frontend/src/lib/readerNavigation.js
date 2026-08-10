function normalizeSlug(value) {
  return decodeURIComponent(String(value || '').trim()).toLowerCase();
}

export function readerRouteForBook(bookSlug, { listen = false } = {}) {
  const slug = String(bookSlug || '').trim();
  if (!slug) return '/library';
  return `/reader/${encodeURIComponent(slug)}${listen ? '?listen=1' : ''}`;
}

export function readerBookMatchesRoute(book, requestedSlug) {
  const returnedSlug = normalizeSlug(book?.slug);
  const routeSlug = normalizeSlug(requestedSlug);
  return Boolean(routeSlug) && (!returnedSlug || returnedSlug === routeSlug);
}
