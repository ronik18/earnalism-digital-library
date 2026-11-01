import { audiobookNarrationDisclosure, audiobookReleaseState } from "./audioReleaseSafety";

import { languageOfBook } from "./libraryCatalog";

function text(value = "") {
  return String(value || "").trim();
}

function upper(value = "") {
  return text(value).toUpperCase();
}

// Package copy may predate the current runtime release decision. Keep editorial
// book copy intact while suppressing sentence-level audio claims unless the
// active release truth allows a Listener control.
export function releaseSafeBookCopy(value = "", audioApproved = false) {
  const copy = text(value);
  if (audioApproved || !copy) return copy;
  return copy
    .split(/(?<=[.!?])\s+/u)
    .filter((sentence) => !/\b(?:audio(?:books?)?|listen(?:ing)?|narrat(?:e|ed|ion|ing))\b/i.test(sentence))
    .join(" ")
    .trim();
}

export function languageOfBookDetail(book = {}) {
  return languageOfBook(book);
}

export function isReaderReadyBook(book = {}) {
  const status = upper(book.publication_status || book.status || book.release_status);
  if (!status) return true;
  return ["LIVE_APPROVED", "PUBLISHED", "PUBLIC", "READER_ONLY_LIVE", "READER_READY"].includes(status);
}

// Publication readiness and the active Reader runtime are distinct contracts.
// A title can remain a reader-approved edition while Reading Pass v2 is
// disabled or its canonical segments are unavailable.  Book Detail must not
// invite a customer into a route that cannot serve the approved edition.
export function readerRuntimeIsAvailable(book = {}) {
  const readingPass = book?._readerManifest?.access?.reading_pass;
  return readingPass?.enabled === true && readingPass?.segments_ready === true;
}

export function bookDetailPresentationForBook(book = {}) {
  const audioState = audiobookReleaseState(book);
  const audioReleaseApproved = audioState.releaseApproved === true;
  const audioApproved = audioState.canShowControls === true;
  const readerReady = isReaderReadyBook(book);
  const readerRuntimeAvailable = readerReady && readerRuntimeIsAvailable(book);
  const freeReading = readerRuntimeAvailable && book?._readerManifest?.access?.reading_pass?.free_entitlement === true;
  const language = languageOfBookDetail(book);
  const slug = text(book.slug || book.id);
  const readerHref = slug ? `/reader/${encodeURIComponent(slug)}` : "/library";

  return {
    readerReady,
    language,
    languageLabel: language === "bn" ? "Bengali Classic" : "English Classic",
    titleClassName: language === "bn" ? "book-detail-title book-detail-title--bengali" : "book-detail-title",
    readerRuntimeAvailable,
    freeReading,
    readerStateLabel: readerReady
      ? (readerRuntimeAvailable ? "Reader Ready" : "Reader currently unavailable")
      : "Reader In Preparation",
    readerHeading: readerReady
      ? (readerRuntimeAvailable ? "Reading edition ready" : "Reader currently unavailable")
      : "Reading edition in preparation",
    readerBody: readerRuntimeAvailable
      ? freeReading
        ? "This edition is available to you under its free Reader entitlement. Read online while that entitlement remains eligible."
        : "Open the text in Earnalism's quiet reader with the current approved edition."
      : readerReady
        ? "This edition cannot be opened right now. Explore the Library for another title."
        : "This reading edition is still in preparation.",
    audioBadgeLabel: audioApproved ? "Audiobook Approved" : "Listening unavailable",
    audioHeading: audioApproved
      ? "Listening room approved"
      : audioReleaseApproved
        ? "Listening currently unavailable"
        : "No audiobook is currently available",
    audioBody: audioApproved
      ? "Open the Listening Room to listen to this audiobook."
      : audioReleaseApproved
        ? "Listening is currently unavailable for this audiobook."
      : "An audiobook is not currently available for this edition.",
    syncCopy: audioApproved ? "Section-following narration" : "",
    listenCtaVisible: audioApproved,
    listenCtaLabel: "Open Listening Room",
    listenHref: audioApproved && slug ? `/listener/${encodeURIComponent(slug)}` : "",
    primaryReadLabel: readerRuntimeAvailable ? (freeReading ? "Start with free preview" : "Start Reading") : readerReady ? "Browse the Library" : "Back to Library",
    primaryReadHref: readerRuntimeAvailable ? readerHref : "/library",
    allowAudioStructuredData: audioApproved,
    narrationDisclosure: audioApproved ? audiobookNarrationDisclosure(book) : "",
    audioState,
  };
}

function canonicalPageNumber(page = {}) {
  const number = Number(page.page_number ?? page.page_index);
  return Number.isInteger(number) && number > 0 ? number : null;
}

// Canonical pages originate in the reader manifest.  Do not infer a chapter's
// starting page from its order, text, or any viewport-derived characteristic.
export function chapterReaderEntryForBook(book = {}, chapterId = "") {
  const slug = text(book.slug || book.id);
  const readerHref = slug ? `/reader/${encodeURIComponent(slug)}` : "/library";
  if (!isReaderReadyBook(book) || !readerRuntimeIsAvailable(book) || !slug) return { href: "", canonicalPage: null, hasCanonicalPage: false };
  const pages = Array.isArray(book?._readerManifest?.canonical_pages?.pages)
    ? book._readerManifest.canonical_pages.pages
    : [];
  const canonicalPage = pages
    .filter((page) => text(page?.chapter_id) === text(chapterId))
    .map(canonicalPageNumber)
    .filter(Boolean)
    .sort((left, right) => left - right)[0] || null;
  return {
    href: canonicalPage ? `${readerHref}?p=${canonicalPage}` : readerHref,
    canonicalPage,
    hasCanonicalPage: Boolean(canonicalPage),
  };
}
