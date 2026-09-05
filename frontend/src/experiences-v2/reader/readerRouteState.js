export function readerRouteState({
  loading = false,
  canonicalPage = 1,
  page = null,
  error = "",
  expectedChapterId = "",
  expectedChapterTitle = "",
} = {}) {
  if (loading) return { state: "loading", message: "" };
  if (error) return { state: "unavailable", message: error };
  if (!page || Number(page.page_index) !== Number(canonicalPage)) {
    return { state: "unavailable", message: "This reader edition cannot verify its canonical preview." };
  }
  if (
    (expectedChapterId && page.chapter_id !== expectedChapterId)
    || (expectedChapterTitle && page.chapter_title !== expectedChapterTitle)
  ) {
    return { state: "unavailable", message: "This reader edition failed its title-integrity check." };
  }
  return { state: "ready", message: "" };
}
