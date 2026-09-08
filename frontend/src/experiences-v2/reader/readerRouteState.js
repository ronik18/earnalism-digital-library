export function readerRouteState({
  loading = false,
  canonicalPage = 1,
  page = null,
  error = "",
  expectedChapterId = "",
  expectedChapterTitle = "",
  awaitingAuthorization = false,
  readingPassEnabled = true,
} = {}) {
  if (loading) return { state: "loading", message: "" };
  if (error) return { state: "unavailable", message: error };
  if (!readingPassEnabled) {
    return { state: "unavailable", message: "This reader edition is unavailable." };
  }
  if (awaitingAuthorization) {
    return {
      state: "authorization_required",
      message: "This chapter is ready to open after you confirm Reading Pass authorization.",
    };
  }
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

export function readerRecoveryPlan({ canonicalPage = 1, user = null, error = "", awaitingAuthorization = false } = {}) {
  const accessMessage = String(error || "").toLowerCase();
  const protectedPage = Number(canonicalPage) > 3;
  const needsSignIn = awaitingAuthorization && protectedPage && !user;
  const needsAuthorization = awaitingAuthorization && protectedPage && Boolean(user);
  const needsPass = !awaitingAuthorization && !needsSignIn && /current reading pass|required to continue|lease|authorization expired|access could not be verified/.test(accessMessage);
  return { needsSignIn, needsAuthorization, needsPass };
}
