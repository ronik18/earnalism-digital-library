import { audiobookReleaseState } from "../../lib/audioReleaseSafety";

export const APPROVED_AUDIO_FIXTURE = Object.freeze({
  title: "The Count’s Arrival",
  author: "Bram Stoker",
  chapterLabel: "Chapter 3 of 27",
  durationSeconds: 1145,
  previewSeconds: 180,
  fixture: true,
});

export function listenerReleasePresentation(book = {}, { fixture = false } = {}) {
  if (fixture) return { canRender: true, fixture: true, mediaUrl: "", release: { status: "approved" }, ...APPROVED_AUDIO_FIXTURE };
  const release = audiobookReleaseState(book);
  if (!release.canShowControls) return { canRender: false, fixture: false, release, mediaUrl: "" };
  const slug = String(book.slug || book.id || "").trim();
  if (!slug) return { canRender: false, fixture: false, release, mediaUrl: "" };
  return {
    canRender: true,
    fixture: false,
    release,
    // The server proxies protected media after it authorizes a Reading Pass
    // lease. Never surface a provider URL from release metadata.
    mediaUrl: `/api/reader/book/${encodeURIComponent(slug)}/audiobook`,
    title: book.public_title || book.display_title || book.title || "Approved audiobook",
    author: book.author || book.author_name || "",
    chapterLabel: book.chapter_label || "Approved narration",
    durationSeconds: Number(book.preview_duration_seconds) || 0,
    previewSeconds: 0,
  };
}
