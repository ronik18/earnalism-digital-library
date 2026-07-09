import { PIPELINE_BOOKS } from "./controlledLaunch";
import { LOCAL_LIBRARY_FALLBACK_BOOKS } from "./libraryFallbackBooks";
import { languageOfBook } from "./libraryCatalog";

const BENGALI_READER_SLUG_ORDER = [
  "book-2b9853ec52",
  "devdas",
  "pather-panchali",
  "hungry-stones",
];

const PIPELINE_SLUG_ORDER = [
  "kshudhita-pashan",
  "sultanas-dream",
  "frankenstein",
  "sherlock-holmes",
  "calculus-made-easy",
];

function findBySlug(items, slug) {
  return items.find((item) => item?.slug === slug);
}

function displayTitleForShelf(book = {}) {
  if (book.titleNative) {
    const englishTitle = book.displayTitle || book.title_en || book.title;
    return englishTitle && englishTitle !== book.titleNative
      ? `${book.titleNative} / ${englishTitle}`
      : book.titleNative;
  }
  return book.displayTitle || book.title_en || book.title || "";
}

function isBengaliReaderBook(book = {}) {
  return languageOfBook(book) === "bn" && String(book.publication_status || "").toUpperCase() === "LIVE_APPROVED";
}

function toShelfBook(book, index, status) {
  const language = languageOfBook(book);
  const isPublished = status === "published";
  return {
    id: book.slug,
    slug: book.slug,
    title: displayTitleForShelf(book),
    author: book.author,
    coverUrl: book.cover_image_url || book.thumbnail_url || book.back_cover_image_url || book.back_cover_thumbnail_url || "",
    cover_image_url: book.cover_image_url || "",
    thumbnail_url: book.thumbnail_url || "",
    back_cover_image_url: book.back_cover_image_url || "",
    back_cover_thumbnail_url: book.back_cover_thumbnail_url || "",
    description: book.short_description || "",
    statusLabel: isPublished
      ? language === "bn" ? "Bengali reader edition" : "Reader edition"
      : book.statusLabel || "Rights-safe preparation",
    dominantColor: book.dominant_color || "",
    sequence: index + 1,
    status,
    language,
    audiobook_enabled: false,
    audio_enabled: false,
  };
}

export function buildShelfTwoBooks({
  readerBooks = LOCAL_LIBRARY_FALLBACK_BOOKS,
  pipelineBooks = PIPELINE_BOOKS,
} = {}) {
  const bengaliReaderBooks = BENGALI_READER_SLUG_ORDER
    .map((slug) => findBySlug(readerBooks, slug))
    .filter(Boolean)
    .filter(isBengaliReaderBook);

  const pipelineBookMap = new Map(pipelineBooks.map((book) => [book.slug, book]));
  const orderedPipelineBooks = PIPELINE_SLUG_ORDER
    .map((slug) => pipelineBookMap.get(slug))
    .filter(Boolean);

  return [
    ...bengaliReaderBooks.map((book, index) => toShelfBook(book, index, "published")),
    ...orderedPipelineBooks.map((book, index) => toShelfBook(book, bengaliReaderBooks.length + index, "queued")),
  ];
}
