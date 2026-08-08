import { api } from "./api";
import homeCuratedSprint1 from "../data/homeCuratedSprint1.json";

const HOME_CURATION_CACHE_KEY = "earnalism_home_curation_v3";
const HOME_CURATION_CACHE_TTL_MS = 60 * 60 * 1000;
const HOME_CURATION_LEGACY_KEYS = [
  "earnalism_home_curation_v2",
  "earnalism_home_curation",
];

let homeCurationMemoryCache = null;

export function expandCompactHomeCuration(payload = {}) {
  if (payload?.format !== "home-curation-compact-v1" || !payload.payload || !payload.books) {
    return payload;
  }
  const books = payload.books;
  const expand = (value) => {
    if (Array.isArray(value)) return value.map(expand);
    if (!value || typeof value !== "object") return value;
    if (typeof value.$book === "string") return books[value.$book] || {};
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, expand(item)]));
  };
  return expand(payload.payload);
}

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

function coverCandidates(book = {}) {
  const candidates = [
    book.front_cover_url,
    book.cover_image_url,
    book.cover_url,
    book.thumbnail_url,
    ...(Array.isArray(book.cover_candidates) ? book.cover_candidates.map((item) => (
      typeof item === "string" ? item : item?.url
    )) : []),
  ].filter((url) => typeof url === "string" && url.trim());
  return Array.from(new Set(candidates));
}

function audioEndpoint(book = {}) {
  const slug = String(book.slug || "").trim();
  const audiobookUrl = book.audiobook_url || book.audio_url || "";
  return typeof audiobookUrl === "string"
    && audiobookUrl === `/api/reader/book/${slug}/audiobook`
    && /^\/api\/reader\/book\/[^/]+\/audiobook$/.test(audiobookUrl);
}

function approvedAudio(book = {}) {
  const release = String(book.audiobook_release_gate || book.audio_release || "").toUpperCase();
  const qa = String(book.audio_qa_status || book.qa_status || "").toUpperCase();
  return Boolean(
    book.audiobook_enabled === true
      && release.includes("APPROVED")
      && ["APPROVED", "PASS", "PASSED", "QA_PASSED"].includes(qa)
      && book.reader_enabled !== false
      && audioEndpoint(book)
      && book.audio_package_valid !== false,
  );
}

export function isApprovedAudioBook(book = {}) {
  return approvedAudio(book);
}

function normalizeBooks(books = [], { audioOnly = false } = {}) {
  const normalized = [];
  const seen = new Set();
  books
    .filter((book) => validCover(book) && (!audioOnly || approvedAudio(book)))
    .forEach((book) => {
      if (seen.has(book.slug)) return;
      seen.add(book.slug);
      normalized.push({
        ...book,
        front_cover_url: book.front_cover_url || book.cover_image_url || book.cover_url,
        cover_candidates: coverCandidates(book),
        cover_alt_text: book.cover_alt_text || `${book.title} by ${book.author}`,
        book_url: book.book_url || `/book/${book.slug}`,
        reader_url: book.reader_url || `/reader/${book.slug}`,
        cta_label: approvedAudio(book) ? "Start Listening" : (book.cta_label || "Start Reading"),
        cta_kind: approvedAudio(book) ? "listen" : (book.cta_kind || "read"),
        cta_url: book.cta_url || book.primary_cta_url || (approvedAudio(book) ? `/reader/${book.slug}?listen=1` : `/book/${book.slug}`),
      });
    });
  return normalized;
}

function normalizeShelf(shelf = {}) {
  const books = normalizeBooks(shelf.visible_books || shelf.books || []);
  const reserve_books = normalizeBooks(shelf.reserve_books || shelf.reserve_items || []);
  return {
    ...shelf,
    books,
    visible_books: books,
    reserve_books,
    total_count: Number(shelf.total_count ?? shelf.book_count ?? books.length),
    mode: shelf.display_mode || shelfMode(books.length),
  };
}

function normalizeShelfFromPayloadEntry(entry, fallbackId) {
  if (!entry || typeof entry !== "object") return null;
  const shelf = Array.isArray(entry)
    ? { id: fallbackId, books: entry }
    : entry;
  const id = shelf.id || fallbackId;
  const books = shelf.visible_books || shelf.books || [];
  return {
    ...shelf,
    id,
    visible_books: books,
    books,
  };
}

function normalizeShelfSource(payloadShelves) {
  if (Array.isArray(payloadShelves)) {
    return payloadShelves;
  }

  if (!payloadShelves || typeof payloadShelves !== "object" || Array.isArray(payloadShelves)) {
    return null;
  }

  return Object.entries(payloadShelves).flatMap(([key, value]) => {
    const normalized = normalizeShelfFromPayloadEntry(value, key);
    return normalized ? [normalized] : [];
  });
}

function extractListeningSource(payload = {}) {
  if (payload.shelves && typeof payload.shelves === "object" && !Array.isArray(payload.shelves) && Array.isArray(payload.shelves.approved_audiobooks)) {
    return payload.shelves.approved_audiobooks;
  }

  const legacy = payload.shelf_collage || {};
  const listeningRooms = payload.listening_rooms || {};
  if (Array.isArray(listeningRooms.items)) return listeningRooms.items;
  if (Array.isArray(payload.audiobook_shelf?.books)) return payload.audiobook_shelf.books;
  if (Array.isArray(payload.selected_audiobooks)) return payload.selected_audiobooks;
  if (Array.isArray(legacy.selected_audiobooks)) return legacy.selected_audiobooks;
  return [];
}

function extractListeningReserve(payload = {}) {
  const listeningRooms = payload.listening_rooms || {};
  if (Array.isArray(listeningRooms.reserve_items)) return listeningRooms.reserve_items;
  if (Array.isArray(payload.audiobook_shelf?.reserve_books)) return payload.audiobook_shelf.reserve_books;
  return [];
}

export function normalizeHomeCuration(payload = {}) {
  const legacy = payload.shelf_collage || {};
  const hero = payload.hero || {};
  const normalizedHero = {
    ...hero,
    featured_books: normalizeBooks(hero.featured_books || []),
    carousel_books: normalizeBooks(hero.carousel_books || []),
  };

  const rawShelves = Array.isArray(payload.literary_shelves) && payload.literary_shelves.length > 0
    ? payload.literary_shelves
    : Array.isArray(payload.shelves)
      ? payload.shelves
      : Array.isArray(legacy.groups) && legacy.groups.length > 0
        ? legacy.groups
        : payload.shelves || [];
  const shelfSource = normalizeShelfSource(rawShelves) || [];
  const sourceShelves = shelfSource.length > 0
    ? shelfSource
    : Array.isArray(rawShelves)
      ? rawShelves
      : [];

  const groups = sourceShelves
    .map(normalizeShelf)
    .filter((shelf) => !["selected-listening", "approved_audiobooks"].includes(shelf.id) && shelf.total_count > 0);

  const selectedAudioSource = extractListeningSource(payload);
  const reserveAudioSource = extractListeningReserve(payload);
  const selectedAudiobooks = normalizeBooks(selectedAudioSource, { audioOnly: true });
  const reserveAudiobooks = normalizeBooks(reserveAudioSource, { audioOnly: true });

  const shelfCollage = {
    ...legacy,
    groups: groups.sort((left, right) => HOME_SHELF_ORDER.indexOf(left.id) - HOME_SHELF_ORDER.indexOf(right.id)),
    selected_audiobooks: selectedAudiobooks,
    approved_audiobooks: selectedAudioSource,
    reserve_audiobooks: reserveAudiobooks,
  };

  return {
    ...payload,
    hero: normalizedHero,
    shelves: groups,
    groups: shelfCollage.groups,
    selected_audiobooks: selectedAudiobooks,
    reserve_audiobooks: reserveAudiobooks,
    shelf_collage: shelfCollage,
    audiobook_shelf: payload.audiobook_shelf ? { ...payload.audiobook_shelf, books: selectedAudiobooks, reserve_books: reserveAudiobooks } : null,
    listening_rooms: payload.listening_rooms ? { ...payload.listening_rooms, items: selectedAudiobooks, reserve_items: reserveAudiobooks } : null,
  };
}

export function approvedListeningBooks(payload = {}) {
  const normalized = normalizeHomeCuration(payload);
  return normalized.listening_rooms?.items || normalized.shelf_collage.selected_audiobooks;
}

export function getHomeCurationSnapshot() {
  return normalizeHomeCuration({
    ...homeCuratedSprint1,
    source: {
      ...(homeCuratedSprint1.source || {}),
      truth_source: "bundled_sprint1_release_snapshot",
    },
  });
}

function getStorage() {
  return typeof window === "undefined" ? null : window.localStorage;
}

function getSessionStorage() {
  return typeof window === "undefined" ? null : window.sessionStorage;
}

function isRecentCache(payload = {}) {
  const age = Date.now() - Number(payload.cached_at || 0);
  return Number.isFinite(age) && age >= 0 && age <= HOME_CURATION_CACHE_TTL_MS;
}

function parseCachePayload(raw) {
  try {
    const parsed = typeof raw === "string" ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== "object" || !parsed.payload) return null;
    const cachedAt = Number(parsed.cached_at);
    if (!Number.isFinite(cachedAt) || cachedAt > Date.now()) return null;
    return { cached_at: cachedAt, payload: parsed.payload };
  } catch {
    return null;
  }
}

function getCacheCandidates() {
  const stores = [getSessionStorage(), getStorage()].filter(Boolean);
  const keys = [HOME_CURATION_CACHE_KEY, ...HOME_CURATION_LEGACY_KEYS];
  const candidates = [];

  for (const storage of stores) {
    for (const key of keys) {
      try {
        const raw = storage.getItem(key);
        const parsed = parseCachePayload(raw);
        if (parsed && isRecentCache(parsed)) {
          candidates.push(parsed);
        }
      } catch {
        // ignore storage read failures
      }
    }
  }
  return candidates;
}

function pickNewestCache(candidates = []) {
  if (candidates.length === 0) return null;
  return candidates.reduce((newest, candidate) => (
    !newest || candidate.cached_at > newest.cached_at ? candidate : newest
  ), null);
}

export function getHomeCurationCache() {
  if (homeCurationMemoryCache && isRecentCache(homeCurationMemoryCache)) {
    return homeCurationMemoryCache.payload;
  }

  const newest = pickNewestCache(getCacheCandidates());
  if (!newest) return null;

  homeCurationMemoryCache = newest;
  return newest.payload;
}

export function setHomeCurationCache(payload = null) {
  if (!payload) return null;
  const record = { cached_at: Date.now(), payload };
  homeCurationMemoryCache = record;

  const storage = getStorage() || getSessionStorage();
  if (storage) {
    try {
      storage.setItem(HOME_CURATION_CACHE_KEY, JSON.stringify(record));
      HOME_CURATION_LEGACY_KEYS.forEach((key) => storage.removeItem(key));
    } catch {
      // ignore quota / private-mode failures
    }
  }
  return record.payload;
}

export function clearHomeCurationCache() {
  homeCurationMemoryCache = null;
  const keys = [HOME_CURATION_CACHE_KEY, ...HOME_CURATION_LEGACY_KEYS];
  for (const storage of [getSessionStorage(), getStorage()].filter(Boolean)) {
    for (const key of keys) {
      try {
        storage.removeItem(key);
      } catch {
        // ignore
      }
    }
  }
}

export async function fetchHomeCuration(signal) {
  const { data } = await api.get("/home/curated?compact=true", { signal });
  const normalized = normalizeHomeCuration(expandCompactHomeCuration(data));
  setHomeCurationCache(normalized);
  return normalized;
}
