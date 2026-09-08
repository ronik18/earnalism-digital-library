import { audiobookNarrationDisclosure, audiobookReleaseState } from "./audioReleaseSafety";

const BENGALI_RE = /[\u0980-\u09FF]/;

function text(value = "") {
  return String(value || "").trim();
}

function upper(value = "") {
  return text(value).toUpperCase();
}

export function languageOfBookDetail(book = {}) {
  const explicit = text(book.language || book.language_code || book.lang || book.locale).toLowerCase();
  if (explicit.startsWith("bn") || explicit.startsWith("ben")) return "bn";
  if (explicit.startsWith("en") || explicit.startsWith("eng")) return "en";
  return BENGALI_RE.test(`${book.title || ""} ${book.subtitle || ""} ${book.author || ""} ${book.description || ""}`) ? "bn" : "en";
}

export function isReaderReadyBook(book = {}) {
  const status = upper(book.publication_status || book.status || book.release_status);
  if (!status) return true;
  return ["LIVE_APPROVED", "PUBLISHED", "PUBLIC", "READER_ONLY_LIVE", "READER_READY"].includes(status);
}

export function bookDetailPresentationForBook(book = {}) {
  const audioState = audiobookReleaseState(book);
  const audioApproved = audioState.canShowControls === true;
  const readerReady = isReaderReadyBook(book);
  const language = languageOfBookDetail(book);
  const slug = text(book.slug || book.id);
  const readerHref = slug ? `/reader/${encodeURIComponent(slug)}` : "/library";

  return {
    readerReady,
    language,
    languageLabel: language === "bn" ? "Bengali Classic" : "English Classic",
    titleClassName: language === "bn" ? "book-detail-title book-detail-title--bengali" : "book-detail-title",
    readerStateLabel: readerReady ? "Reader Ready" : "Reader In Preparation",
    readerHeading: readerReady ? "Reading edition ready" : "Reading edition in preparation",
    readerBody: readerReady
      ? "Open the text in Earnalism's quiet reader with the current approved edition."
      : "This title remains in editorial preparation until source, rights, and reader gates pass.",
    audioBadgeLabel: audioApproved ? "Audiobook Approved" : readerReady ? "Audio Hidden" : "Release Gated",
    audioHeading: audioApproved ? "Listening room approved" : "Audio waits for release gates",
    audioBody: audioApproved
      ? "Open the Listening Room only because approved provider-backed audio evidence is present."
      : "No public audio controls are shown until narration, sync, metadata, endpoint, and browser gates pass.",
    syncCopy: audioApproved ? "Section-following narration" : "",
    listenCtaVisible: audioApproved,
    listenCtaLabel: "Open Listening Room",
    listenHref: audioApproved && slug ? `/listener/${encodeURIComponent(slug)}` : "",
    primaryReadLabel: readerReady ? "Start Reading" : "Back to Library",
    primaryReadHref: readerReady ? readerHref : "/library",
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
  if (!isReaderReadyBook(book) || !slug) return { href: "", canonicalPage: null, hasCanonicalPage: false };
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
