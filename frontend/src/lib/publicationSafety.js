export const CONTROLLED_LIVE_READING_SLUGS = new Set(["dracula"]);

export function isControlledLiveReadingBook(book) {
  const slug = String(book?.slug || book?.id || "").trim().toLowerCase();
  if (!slug) return false;
  if (CONTROLLED_LIVE_READING_SLUGS.has(slug)) return true;

  const controlledSlug = String(book?.controlled_publication_slug || "").trim().toLowerCase();
  const controlledStatus = String(book?.controlled_publication_status || "").trim().toUpperCase();
  const controlledScope = String(book?.controlled_publication_scope || "").trim().toLowerCase();
  return (
    controlledSlug === slug
    && controlledStatus === "PUBLISHED_CORE_READING_ONLY"
    && controlledScope === "core_reading_candidate_only"
    && CONTROLLED_LIVE_READING_SLUGS.has(slug)
  );
}

export function controlledReadingLabel(book) {
  return isControlledLiveReadingBook(book) && String(book?.slug || "").toLowerCase() === "dracula"
    ? "Start Dracula"
    : "Coming Soon";
}
