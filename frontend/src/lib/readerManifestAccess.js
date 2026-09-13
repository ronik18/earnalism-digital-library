function enabledAssets(value) {
  if (!value || typeof value !== "object") return false;
  return Object.values(value).some((entry) => typeof entry === "string" && entry.trim());
}

function approved(value) {
  return String(value || "").trim().toUpperCase() === "APPROVED";
}

function qaPassed(value) {
  return ["QA_PASSED", "APPROVED", "PASS"].includes(String(value || "").trim().toUpperCase());
}

function approvedPackageManifest(book, manifestAudio) {
  const slug = String(book?.slug || "").trim();
  return Boolean(slug)
    && String(manifestAudio?.asset_slug || "").trim() === slug
    && approved(manifestAudio?.release_gate)
    && qaPassed(manifestAudio?.qa_status)
    && Boolean(String(manifestAudio?.provider || "").trim())
    && Boolean(String(manifestAudio?.version || "").trim())
    && /^sha256-[a-f0-9]{64}$/.test(String(manifestAudio?.package_version || "").trim());
}

// Manifests add metadata for an already-authorized canonical book; they do not
// supply authorization or revive stale media fields.
export function readerManifestAudioIsAuthorized(book = {}, manifestAudio = {}) {
  const canonicalReleaseApproved = book?.audio_enabled === true
    && book?.audiobook_enabled === true
    && approved(book?.audiobook_release_gate);
  if (!canonicalReleaseApproved || manifestAudio?.enabled !== true) return false;

  // Legacy releases bind their canonical and manifest asset references. Package
  // v2 intentionally omits protected media and manifest URLs from the public
  // projection. Its exact asset slug plus immutable approved package version
  // bind the public release decision; Listener obtains the protected manifest
  // only after server authorization.
  return (enabledAssets(book?.audiobook_assets) && enabledAssets(manifestAudio?.assets))
    || approvedPackageManifest(book, manifestAudio);
}
