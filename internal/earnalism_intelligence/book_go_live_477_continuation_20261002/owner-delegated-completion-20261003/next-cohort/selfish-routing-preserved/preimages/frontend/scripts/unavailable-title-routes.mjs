// PR #476 intentionally retains these safe historical recovery pages.
export const unavailableTitles = [
  { slug: "the-selfish-giant", title: "The Selfish Giant" },
];
export const unavailableCopy = "This title is not part of the current public release. Its reading and listening experiences are unavailable.";
export const unavailableAccessCopy = "No book text, reader session, or audio is available from this page.";

export function unavailableTitleRoutes(liveApprovedSlugs) {
  const released = new Set(liveApprovedSlugs);
  if (unavailableTitles.some(({ slug }) => released.has(slug))) {
    throw new Error("Historical unavailable routes must be reconciled before activating their title release.");
  }
  return unavailableTitles.flatMap(({ slug, title }) => ["book", "reader", "listener"].map((kind) => ({
    path: "/" + kind + "/" + slug,
    canonicalPath: "/book/" + slug,
    slug,
    title,
  })));
}
