import { api } from "./api";

export const HOME_SHELF_ORDER = [
  "bengali-life-and-legacy",
  "gothic-and-the-uncanny",
  "love-society-and-human-nature",
  "adventure-nature-and-wonder",
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

function validCover(book = {}) {
  return Boolean(
    book.slug
      && (book.front_cover_url || book.cover_image_url || book.cover_url)
      && book.cover_valid !== false
      && book.is_placeholder !== true
      && book.is_typographic_only !== true,
  );
}

function approvedAudio(book = {}) {
  const release = String(book.audiobook_release_gate || book.audio_release || "").toUpperCase();
  const qa = String(book.audio_qa_status || book.qa_status || "").toUpperCase();
  return Boolean(
    book.audiobook_enabled === true
      && release.includes("APPROVED")
      && ["APPROVED", "PASS", "PASSED", "QA_PASSED"].includes(qa)
      && (book.audiobook_url || book.audio_url || book.cta_url),
  );
}

export function isApprovedAudioBook(book = {}) {
  return approvedAudio(book);
}

function normalizeBooks(books = [], { audioOnly = false } = {}) {
  return Array.from(new Map(
    books
      .filter((book) => validCover(book) && (!audioOnly || approvedAudio(book)))
      .map((book) => [book.slug, {
        ...book,
        front_cover_url: book.front_cover_url || book.cover_image_url || book.cover_url,
        cover_alt_text: book.cover_alt_text || `${book.title} by ${book.author}`,
        cta_label: approvedAudio(book) ? "Start Listening" : (book.cta_label || "Start Reading"),
        cta_kind: approvedAudio(book) ? "listen" : (book.cta_kind || "read"),
        cta_url: book.cta_url || book.primary_cta_url || (approvedAudio(book) ? `/reader/${book.slug}?listen=1` : `/book/${book.slug}`),
      }]),
  ).values());
}

function normalizeShelf(shelf = {}) {
  const books = normalizeBooks(shelf.visible_books || shelf.books || []);
  return {
    ...shelf,
    books,
    visible_books: books,
    total_count: Number(shelf.total_count ?? shelf.book_count ?? books.length),
    mode: shelf.display_mode || shelfMode(books.length),
  };
}

export function normalizeHomeCuration(payload = {}) {
  const legacy = payload.shelf_collage || {};
  const sourceShelves = Array.isArray(payload.literary_shelves)
    ? payload.literary_shelves
    : Array.isArray(payload.shelves)
      ? payload.shelves.filter((shelf) => shelf.id !== "selected-listening")
      : legacy.groups || [];
  const groups = sourceShelves.map(normalizeShelf).filter((shelf) => shelf.total_count > 0 && shelf.books.length > 0);
  const audioSource = payload.audiobook_shelf?.books || payload.selected_audiobooks || legacy.selected_audiobooks || [];
  const selectedAudiobooks = normalizeBooks(audioSource, { audioOnly: true });
  const shelfCollage = {
    ...legacy,
    groups: groups.sort((left, right) => HOME_SHELF_ORDER.indexOf(left.id) - HOME_SHELF_ORDER.indexOf(right.id)),
    selected_audiobooks: selectedAudiobooks,
  };
  return {
    ...payload,
    shelves: groups,
    shelf_collage: shelfCollage,
    audiobook_shelf: payload.audiobook_shelf ? { ...payload.audiobook_shelf, books: selectedAudiobooks } : null,
  };
}

export function approvedListeningBooks(payload = {}) {
  return normalizeHomeCuration(payload).shelf_collage.selected_audiobooks;
}

export function getHomeCurationSnapshot() {
  return normalizeHomeCuration({ literary_shelves: [], audiobook_shelf: null, source: { truth_source: "runtime_endpoint_pending" } });
}

export async function fetchHomeCuration(signal) {
  const { data } = await api.get("/home/curated", { signal });
  return normalizeHomeCuration(data);
}
