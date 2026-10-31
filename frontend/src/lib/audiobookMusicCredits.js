import credits from "./audiobookMusicCredits.json";
export function approvedAudiobookMusicCredit(book = {}) {
  const digest = book.audiobook_release_descriptor_sha256;
  const notice = typeof digest === "string" ? credits[digest] : null;
  return notice && notice.slug === book.slug && book.audio_enabled === true
    && book.audiobook_enabled === true && book.audiobook_release_gate === "APPROVED"
    && book.audio_qa_status === "QA_PASSED" && book.audiobook_delivery_mode === "PROTECTED_PACKAGE_V2"
    && /^sha256-[a-f0-9]{64}$/.test(book.audiobook_package_version || "") ? notice : null;
}
