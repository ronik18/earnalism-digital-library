import { audiobookReleaseState } from "../../lib/audioReleaseSafety";

export const APPROVED_AUDIO_FIXTURE = Object.freeze({
  title: "The Count’s Arrival",
  author: "Bram Stoker",
  chapterLabel: "Chapter 3 of 27",
  durationSeconds: 1145,
  publicPreviewSeconds: 0,
  fixture: true,
});

function hasCanonicalProtectedAudioApproval(book = {}) {
  const audio = book?._readerManifest?.audio || {};
  const gate = String(audio.release_gate || "").trim().toUpperCase();
  const qa = String(audio.qa_status || "").trim().toUpperCase();
  // Public reader manifests intentionally omit asset URLs.  The protected,
  // same-origin endpoint is derived only after these canonical gates pass.
  return audio.enabled === true
    && Boolean(String(audio.asset_slug || book.slug || "").trim())
    && Boolean(String(audio.provider || "").trim())
    && Boolean(String(audio.version || "").trim())
    && gate === "APPROVED"
    && ["QA_PASSED", "APPROVED", "PASS"].includes(qa);
}

export function listenerReleasePresentation(book = {}, { fixture = false } = {}) {
  if (fixture) return { canRender: true, fixture: true, mediaUrl: "", release: { status: "approved" }, ...APPROVED_AUDIO_FIXTURE };
  const release = audiobookReleaseState(book);
  const canonicalApproval = hasCanonicalProtectedAudioApproval(book);
  if (!release.canShowControls && !canonicalApproval) return { canRender: false, fixture: false, release, mediaUrl: "" };
  const slug = String(book.slug || book.id || "").trim();
  if (!slug) return { canRender: false, fixture: false, release, mediaUrl: "" };
  return {
    canRender: true,
    fixture: false,
    release: canonicalApproval ? { ...release, status: "approved", canShowControls: true } : release,
    // The server proxies protected media after it authorizes a Reading Pass
    // lease. Never surface a provider URL from release metadata.
    mediaUrl: `/api/reader/book/${encodeURIComponent(slug)}/audiobook`,
    title: book.public_title || book.display_title || book.title || "Approved audiobook",
    author: book.author || book.author_name || "",
    chapterLabel: book.chapter_label || "Approved narration",
    durationSeconds: Number(book.preview_duration_seconds) || 0,
    publicPreviewSeconds: 0,
  };
}
