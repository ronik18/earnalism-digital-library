let readerFinishPromptShown = false;

export function canShowReaderFinishPrompt() {
  return typeof window !== "undefined" && !readerFinishPromptShown;
}

export function markReaderFinishPromptShown() {
  readerFinishPromptShown = true;
}
