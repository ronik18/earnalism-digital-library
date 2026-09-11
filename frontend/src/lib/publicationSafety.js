import {
  KSHUDHITA_PASHAN_SLUG,
  isLiveApprovedBook,
  isPipelineCandidate,
} from "./controlledLaunch";

function audioQaPassed(book = {}) {
  const qaStatus = String(book?.audio_qa_status || book?.audiobook?.qa_status || "").trim().toUpperCase();
  return qaStatus === "QA_PASSED";
}

export function isControlledLiveReadingBook(book = {}) {
  return isLiveApprovedBook(book);
}

export function isPipelineOnlyBook(book = {}) {
  const slug = String(book?.slug || book?.id || "").trim().toLowerCase();
  if (!slug || isControlledLiveReadingBook(book)) return false;
  if (slug === KSHUDHITA_PASHAN_SLUG) return true;
  return isPipelineCandidate(book);
}

export function canShowStartReading(book = {}) {
  return isControlledLiveReadingBook(book);
}

export function canShowPreview(book = {}) {
  return isControlledLiveReadingBook(book);
}

export function canShowAudioCTA(book = {}) {
  if (!isControlledLiveReadingBook(book)) return false;
  if (!book?.audiobook_enabled || book?.generate_audiobook) return false;
  return audioQaPassed(book);
}

export function controlledReadingLabel(book = {}) {
  return isControlledLiveReadingBook(book) ? "Start Reading" : "Coming Soon";
}
