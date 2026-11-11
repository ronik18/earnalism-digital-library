import { audiobookReleaseState } from "./audioReleaseSafety";
import { canShowStartReading, PUBLIC_AUDIO_EXPOSURE_ENABLED, PUBLIC_PROTECTED_PACKAGE_SLUGS } from "./controlledLaunch";

import { discoveryMetadataForBook, readingFormOfBook, genresOfBook } from "./libraryDiscovery";

const BENGALI_RE = /[\u0980-\u09FF]/;

export { listeningFilterFromSearch } from "./libraryFilterState";

export function languageOfBook(book = {}) {
  const curated = discoveryMetadataForBook(book)?.language;
  if (curated) return curated;
  return BENGALI_RE.test(`${book.title || ""} ${book.title_en || ""} ${book.author || ""}`) ? "bn" : "en";
}

function publicListeningEnabled(book, audioState) {
  return PUBLIC_AUDIO_EXPOSURE_ENABLED || (
    PUBLIC_PROTECTED_PACKAGE_SLUGS.includes(book?.slug)
    && book?.audiobook_delivery_mode === "PROTECTED_PACKAGE_V2"
    && audioState.canShowControls === true
  );
}

export function availabilityOfBook(book = {}) {
  if (!canShowStartReading(book)) return "in-preparation";
  const audioState = audiobookReleaseState(book);
  if (publicListeningEnabled(book, audioState) && audioState.releaseApproved) return "approved-audiobook";
  return "reader-ready";
}

export function libraryPresentationForBook(book = {}) {
  const language = languageOfBook(book);
  const availability = availabilityOfBook(book);
  const audioState = audiobookReleaseState(book);
  const readerReady = availability === "reader-ready";
  const audiobookApproved = availability === "approved-audiobook";
  const listeningAvailable = publicListeningEnabled(book, audioState) && audioState.canShowControls;

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
    audioBadgeLabel: audiobookApproved
      ? (listeningAvailable ? "Listening Live" : "Listening unavailable")
      : readerReady ? "Audio Hidden" : "Release Gated",
    availabilityNote: audiobookApproved
      ? (listeningAvailable
        ? "This audiobook is ready to accompany your reading life. An active Reading Pass is required to listen."
        : "Listening is not available for this edition right now.")
      : readerReady
        ? "Read this edition online. An audiobook is not currently offered."
        : "This edition is still in preparation and is not available to read or listen to.",
    canShowControls: listeningAvailable,
  };
}

export function matchesLibraryFacets(book = {}, language = "all", availability = "all") {
  const bookLanguage = languageOfBook(book);
  const bookAvailability = availabilityOfBook(book);
  if (language !== "all" && bookLanguage !== language) return false;
  if (availability === "all") return true;
  if (availability === "audio-hidden") return bookAvailability === "reader-ready";
  return bookAvailability === availability;
}

export function normalizedBookTitle(book = {}) {
  return String(book.title_en || book.title || "").toLocaleLowerCase();
}

// Discovery estimate only; never used for playback, lease or billing timing.
function estimatedReadingMinutes(book) {
  const value = String(book.estimated_reading_time || "").trim().toLowerCase();
  const hours = value.match(/(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b/);
  const minutes = value.match(/(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)\b/);
  if (hours || minutes) return Number(hours?.[1] || 0) * 60 + Number(minutes?.[1] || 0);
  if (/^\d+(?:\.\d+)?$/.test(value) && Number(value) > 0) return Number(value);
  return Number(book.word_count) > 0 ? Number(book.word_count) / 200 : Number.POSITIVE_INFINITY;
}

export function sortLibraryBooks(books = [], sort = "recently-approved") {
  const next = [...books];
  if (sort === "title") {
    next.sort((a, b) => normalizedBookTitle(a).localeCompare(normalizedBookTitle(b)));
  } else if (sort === "author") {
    next.sort((a, b) => String(a.author || "").localeCompare(String(b.author || "")));
  } else if (sort === "short-reads") {
    next.sort((a, b) => estimatedReadingMinutes(a) - estimatedReadingMinutes(b));
  }

  return next;
}


export function selectLibraryBooks(books, { query = "", language = "all", reading = "all", listening = "all", genre = "all", sort = "recently-approved", stage = "all" } = {}) {
  const needle = query.trim().normalize("NFC").toLocaleLowerCase();
  return sortLibraryBooks(books.filter((book) => {
    const text = `${book.title || ""} ${book.title_en || ""} ${book.author || ""} ${book.short_description || ""}`.normalize("NFC").toLocaleLowerCase();
    return (!needle || text.includes(needle))
      && matchesLibraryFacets(book, language, listening === "available" ? "approved-audiobook" : listening === "hidden" ? "audio-hidden" : "all")
      && (reading === "all" || readingFormOfBook(book) === reading)
      && (genre === "all" || genresOfBook(book).includes(genre))
      && (stage === "all" || (stage === "live" ? canShowStartReading(book) : !canShowStartReading(book)));
  }), sort);
}
