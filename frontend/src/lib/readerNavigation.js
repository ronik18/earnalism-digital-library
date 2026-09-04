function normalizeSlug(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw).trim().toLowerCase();
  } catch {
    return '';
  }
}

export function readerRouteForBook(bookSlug, { listen = false } = {}) {
  const slug = String(bookSlug || '').trim();
  if (!slug) return '/library';
  return `/reader/${encodeURIComponent(slug)}${listen ? '?listen=1' : ''}`;
}

export function readerBookMatchesRoute(book, requestedSlug) {
  const returnedSlug = normalizeSlug(book?.slug);
  const routeSlug = normalizeSlug(requestedSlug);
  return Boolean(routeSlug) && Boolean(returnedSlug) && returnedSlug === routeSlug;
}
