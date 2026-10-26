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
    && (Boolean(String(audio.provider || "").trim()) || (audio.delivery_mode === "PROTECTED_PACKAGE_V2" && audio.asset_slug === book.slug
      && /^sha256-[a-f0-9]{64}$/.test(audio.package_version || "")))
    && Boolean(String(audio.version || "").trim())
    && gate === "APPROVED"
    && ["QA_PASSED", "APPROVED", "PASS"].includes(qa);
}

export function listenerReleasePresentation(book = {}, { fixture = false } = {}) {
  if (fixture) return {
    canRender: true,
    fixture: true,
    mediaUrl: "",
    release: { status: "visual_fixture" },
    ...APPROVED_AUDIO_FIXTURE,
    chapterLabel: book.chapter_label || APPROVED_AUDIO_FIXTURE.chapterLabel,
    durationSeconds: Number(book.preview_duration_seconds) || 0,
    // A local review fixture may safely use the title/author and cover that
    // belong together; it never changes production audio approval or media.
    title: book.public_title || book.display_title || book.title || APPROVED_AUDIO_FIXTURE.title,
    author: book.author || book.author_name || APPROVED_AUDIO_FIXTURE.author,
  };
  const canary = book?._readerManifest?.audio?.transport_canary;
  const access = book?._readerManifest?.access;
  const canaryAllowed = access?.authenticated === true && access?.role === "user"
    && canary?.enabled === true && canary.slug === book.slug
    && canary.scope === "transport_canary_only_no_customer_discovery"
    && [5, 25].includes(canary.rollout_percentage)
    && /^sha256-[a-f0-9]{64}$/.test(canary.package_version || "")
    && /^[a-f0-9]{64}$/.test(canary.release_descriptor_sha256 || "");
  if (canaryAllowed) return {
    canRender: true, fixture: false, mediaUrl: "", packageManifestUrl: "",
    release: { status: "transport_canary", canShowControls: true },
    packageVersion: canary.package_version,
    title: book.title, author: book.author,
    chapterLabel: book.chapter_label || "Full audiobook",
    durationSeconds: Number(canary.duration_ms) / 1000,
    publicPreviewSeconds: 0,
  };
  const release = audiobookReleaseState(book);
  const canonicalApproval = hasCanonicalProtectedAudioApproval(book);
  if (!release.canShowControls && !canonicalApproval) return { canRender: false, fixture: false, release, mediaUrl: "" };
  const slug = String(book.slug || book.id || "").trim();
  if (!slug) return { canRender: false, fixture: false, release, mediaUrl: "" };
  return {
    canRender: true,
    fixture: false,
    release: canonicalApproval ? { ...release, status: "approved", canShowControls: true } : release,
    // The public Reader manifest may identify an immutable package, but it
    // never contains a playable provider URL.  The Listener fetches this
    // protected manifest only after the Reading Pass audio lease succeeds.
    mediaUrl: "",
    packageManifestUrl: release.packageManifestUrl || "",
    packageVersion: release.packageVersion || "",
    title: book.public_title || book.display_title || book.title || "Approved audiobook",
    author: book.author || book.author_name || "",
    chapterLabel: book.chapter_label || "Full audiobook",
    durationSeconds: Number(book?._readerManifest?.audio?.duration_ms) / 1000 || Number(book.preview_duration_seconds) || 0,
    publicPreviewSeconds: 0,
  };
}
