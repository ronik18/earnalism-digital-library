import { api } from "./api";
import sprint1HomeSnapshot from "../data/homeCuratedSprint1.json";

const APPROVED_RELEASE_STATUSES = new Set(["APPROVED", "PUBLIC_AUDIO_RELEASE_APPROVED"]);
const PASSED_AUDIO_QA_STATUSES = new Set(["APPROVED", "PASS", "PASSED", "QA_PASSED"]);

export function isSafeHeroCoverUrl(value) {
  const url = String(value || "").trim();
  if (!url || /placeholder/i.test(url) || /^(data|javascript):/i.test(url)) return false;
  if (url.startsWith("/")) return !url.startsWith("/audio/");
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false;
  }
}

export function isApprovedHomeAudiobook(book = {}) {
  const slug = String(book.slug || "").trim();
  const releaseStatus = String(book.audiobook_release_gate || "").trim().toUpperCase();
  const qaStatus = String(book.audio_qa_status || "").trim().toUpperCase();
  const audiobookUrl = String(book.audiobook_url || "").trim();
  return Boolean(
    slug
    && book.audiobook_enabled === true
    && APPROVED_RELEASE_STATUSES.has(releaseStatus)
    && PASSED_AUDIO_QA_STATUSES.has(qaStatus)
    && audiobookUrl === `/api/reader/book/${slug}/audiobook`,
  );
}

export function normalizeHomeBook(book = {}) {
  const slug = String(book.slug || "").trim();
  const title = String(book.title || "").trim();
  const author = String(book.author || "").trim();
  const frontCoverUrl = String(book.front_cover_url || "").trim();
  if (!slug || !title || !author || book.reader_enabled !== true || !isSafeHeroCoverUrl(frontCoverUrl)) {
    return null;
  }

  const audiobookEnabled = isApprovedHomeAudiobook(book);
  const normalized = {
    ...book,
    slug,
    title,
    author,
    language: String(book.language || "").trim().toLowerCase() === "bn" ? "bn" : "en",
    front_cover_url: frontCoverUrl,
    back_cover_url: isSafeHeroCoverUrl(book.back_cover_url) ? String(book.back_cover_url).trim() : "",
    cover_alt_text: `${title} by ${author}`,
    reader_enabled: true,
    book_url: `/book/${slug}`,
    reader_url: `/reader/${slug}`,
    audiobook_enabled: audiobookEnabled,
    cta_label: audiobookEnabled ? "Start Listening" : "Start Reading",
    cta_url: audiobookEnabled ? `/reader/${slug}?listen=1` : `/reader/${slug}`,
    cta_kind: audiobookEnabled ? "listen" : "read",
  };

  if (!audiobookEnabled) delete normalized.audiobook_url;
  return normalized;
}

function normalizeBookList(value) {
  const books = Array.isArray(value) ? value : [];
  const bySlug = new Map();
  for (const rawBook of books) {
    const book = normalizeHomeBook(rawBook);
    if (book && !bySlug.has(book.slug)) bySlug.set(book.slug, book);
  }
  return Array.from(bySlug.values());
}

export function normalizeHomeCuration(payload = {}) {
  const hero = payload.hero && typeof payload.hero === "object" ? payload.hero : {};
  const shelves = payload.shelves && typeof payload.shelves === "object" ? payload.shelves : {};
  const source = payload.source && typeof payload.source === "object" ? payload.source : {};
  const approvedAudiobooks = normalizeBookList(shelves.approved_audiobooks)
    .filter((book) => book.audiobook_enabled);

  return {
    hero: {
      headline: String(hero.headline || "").trim(),
      subheadline: String(hero.subheadline || "").trim(),
      primary_cta: hero.primary_cta || {},
      secondary_cta: hero.secondary_cta || {},
      featured_books: normalizeBookList(hero.featured_books).slice(0, 6),
    },
    shelves: {
      reader_favorites: normalizeBookList(shelves.reader_favorites),
      bengali_classics: normalizeBookList(shelves.bengali_classics),
      english_classics: normalizeBookList(shelves.english_classics),
      approved_audiobooks: approvedAudiobooks,
    },
    source,
  };
}

const NORMALIZED_SPRINT1_HOME_SNAPSHOT = normalizeHomeCuration(sprint1HomeSnapshot);

export function getHomeCurationSnapshot() {
  return NORMALIZED_SPRINT1_HOME_SNAPSHOT;
}

export async function fetchHomeCuration(signal) {
  const response = await api.get("/home/curated", { signal });
  return normalizeHomeCuration(response.data);
}
