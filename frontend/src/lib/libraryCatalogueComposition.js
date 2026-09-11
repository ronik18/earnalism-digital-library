import {
  BATCH_1_READER_ONLY_SLUGS,
  LIVE_APPROVED_SLUG,
  PIPELINE_CANONICAL_PUBLICATION_SLUGS,
  PIPELINE_BOOKS,
  mergeDraculaBook,
} from "./controlledLaunch";

export function composeLibraryCatalog(liveBooks = []) {
  const bySlug = new Map();
  liveBooks.forEach((book) => book?.slug && bySlug.set(book.slug, book.slug === LIVE_APPROVED_SLUG ? mergeDraculaBook(book) : book));
  if (bySlug.has(LIVE_APPROVED_SLUG)) bySlug.set(LIVE_APPROVED_SLUG, mergeDraculaBook(bySlug.get(LIVE_APPROVED_SLUG)));
  PIPELINE_BOOKS.filter((book) => !BATCH_1_READER_ONLY_SLUGS.includes(book.slug)).forEach((book) => {
    const canonicalPublicationSlug = PIPELINE_CANONICAL_PUBLICATION_SLUGS[book.slug];
    if (!bySlug.has(book.slug) && (!canonicalPublicationSlug || !bySlug.has(canonicalPublicationSlug))) {
      bySlug.set(book.slug, book);
    }
  });
  return Array.from(bySlug.values());
}
