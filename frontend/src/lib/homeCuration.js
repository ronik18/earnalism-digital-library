export const HOME_SHELF_ORDER = [
  "bengali-classics",
  "gothic-classics",
  "love-society-human-nature",
  "adventure-journeys",
  "short-masterpieces",
  "selected-listening",
];

export function shelfMode(count) {
  if (!count) return "Zero";
  if (count === 1) return "Spotlight";
  if (count === 2) return "Duo";
  if (count <= 4) return "Trio";
  if (count <= 7) return "Runway";
  return "Overflow";
}

export function normalizeShelf(shelf = {}) {
  const books = Array.from(new Map((shelf.books || [])
    .filter((book) => book?.slug && (book.front_cover_url || book.cover_image_url || book.cover_url))
    .map((book) => [book.slug, book])).values());
  return { ...shelf, books, mode: shelfMode(books.length) };
}

export function normalizeHomeCuration(payload = {}) {
  const shelves = (payload.shelves || [])
    .map(normalizeShelf)
    .sort((a, b) => HOME_SHELF_ORDER.indexOf(a.id) - HOME_SHELF_ORDER.indexOf(b.id));
  return { ...payload, shelves };
}

export function approvedListeningBooks(payload = {}) {
  return (payload.shelves || [])
    .find((shelf) => shelf.id === "selected-listening")?.books || [];
}
