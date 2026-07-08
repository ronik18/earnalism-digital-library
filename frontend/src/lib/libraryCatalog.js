import { audiobookReleaseState } from "./audioReleaseSafety";
import { BATCH_1_READER_ONLY_SLUGS } from "./controlledLaunch";

const BENGALI_RE = /[\u0980-\u09FF]/;

export function languageOfBook(book = {}) {
  const explicit = String(book.language || book.language_code || book.lang || book.locale || "").toLowerCase();
  if (explicit.startsWith("bn") || explicit.startsWith("ben")) return "bn";
  if (explicit.startsWith("en") || explicit.startsWith("eng")) return "en";
  return BENGALI_RE.test(`${book.title || ""} ${book.title_en || ""} ${book.author || ""}`) ? "bn" : "en";
}

export function availabilityOfBook(book = {}) {
  const audioState = audiobookReleaseState(book);
  if (audioState.canShowControls) return "approved-audiobook";
  if (book.publication_status === "LIVE_APPROVED" || book.status === "LIVE_APPROVED" || BATCH_1_READER_ONLY_SLUGS.includes(book.slug)) {
    return "reader-ready";
  }
  return "in-preparation";
}

export function libraryPresentationForBook(book = {}) {
  const language = languageOfBook(book);
  const availability = availabilityOfBook(book);
  const audioState = audiobookReleaseState(book);
  const readerReady = availability === "reader-ready";
  const audiobookApproved = availability === "approved-audiobook";

  return {
    language,
    isBengali: language === "bn",
    languageLabel: language === "bn" ? "Bengali" : "English",
    availability,
    availabilityLabel: audiobookApproved
      ? "Audiobook Approved"
      : readerReady
        ? "Reader Ready"
        : "In Preparation",
    audioBadgeLabel: audiobookApproved ? "Listening Live" : readerReady ? "Audio Hidden" : "Release Gated",
    availabilityNote: audiobookApproved
      ? "Provider-backed narration is live on the approved reader route."
      : readerReady
        ? "Reader edition live · audio intentionally hidden until release evidence passes."
        : "Reader and listening routes remain closed until editorial and release gates pass.",
    canShowControls: audioState.canShowControls,
  };
}

export function matchesLibraryFacets(book = {}, language = "all", availability = "all") {
  const bookLanguage = languageOfBook(book);
  const bookAvailability = availabilityOfBook(book);
  const audioState = audiobookReleaseState(book);
  if (language !== "all" && bookLanguage !== language) return false;
  if (availability === "all") return true;
  if (availability === "audio-hidden") return !audioState.canShowControls && bookAvailability === "reader-ready";
  return bookAvailability === availability;
}

export function normalizedBookTitle(book = {}) {
  return String(book.title_en || book.title || "").toLocaleLowerCase();
}

export function sortLibraryBooks(books = [], sort = "recently-approved") {
  const next = [...books];
  if (sort === "title") {
    next.sort((a, b) => normalizedBookTitle(a).localeCompare(normalizedBookTitle(b)));
  } else if (sort === "author") {
    next.sort((a, b) => String(a.author || "").localeCompare(String(b.author || "")));
  } else if (sort === "short-reads") {
    next.sort((a, b) => {
      const aMinutes = Number(String(a.estimated_reading_time || "").match(/\d+/)?.[0] || a.word_count || 999999);
      const bMinutes = Number(String(b.estimated_reading_time || "").match(/\d+/)?.[0] || b.word_count || 999999);
      return aMinutes - bMinutes;
    });
  }
  return next;
}
