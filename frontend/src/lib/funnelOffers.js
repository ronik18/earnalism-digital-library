const READER_PROMPT_SESSION_KEY = "earnalism_reader_finish_prompt_shown";

export function canShowReaderFinishPrompt() {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(READER_PROMPT_SESSION_KEY) !== "1";
}

export function markReaderFinishPromptShown() {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(READER_PROMPT_SESSION_KEY, "1");
  }
}
