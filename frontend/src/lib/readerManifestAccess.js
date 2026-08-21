function enabledAssets(value) {
  if (!value || typeof value !== "object") return false;
  return Object.values(value).some((entry) => typeof entry === "string" && entry.trim());
}

function approved(value) {
  return String(value || "").trim().toUpperCase() === "APPROVED";
}

// Manifests add metadata for an already-authorized canonical book; they do not
// supply authorization or revive stale media fields.
export function readerManifestAudioIsAuthorized(book = {}, manifestAudio = {}) {
  return book?.audio_enabled === true
    && book?.audiobook_enabled === true
    && approved(book?.audiobook_release_gate)
    && enabledAssets(book?.audiobook_assets)
    && manifestAudio?.enabled === true
    && enabledAssets(manifestAudio?.assets);
}
