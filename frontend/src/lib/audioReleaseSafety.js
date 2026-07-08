function clean(value = "") {
  return String(value || "").trim();
}

function upper(value = "") {
  return clean(value).toUpperCase();
}

export function isStaticAudiobookAssetPath(value = "") {
  return /^\/audio\//i.test(clean(value));
}

export function audiobookAssetsForBook(book = {}) {
  return book?.audiobook_assets
    || book?.audiobookAssets
    || book?.audio_assets
    || book?._readerManifest?.audio?.assets
    || book?.audiobook?.assets
    || {};
}

export function audiobookReleaseState(book = {}) {
  const assets = audiobookAssetsForBook(book);
  const manifestAudio = book?._readerManifest?.audio || {};
  const releaseGate = upper(
    book?.audiobook_release_gate
      || book?.audiobookreleasegate
      || book?.audiobookReleaseGate
      || book?.audiobook?.release_gate
      || book?._readerManifest?.audio?.release_gate
      || "",
  );
  const qaStatus = upper(
    book?.audio_qa_status
      || book?.audiobook?.qa_status
      || book?._readerManifest?.audio?.qa_status
      || "",
  );
  const audioUrl = clean(
    assets.mp3
      || assets.audio
      || assets.url
      || book?.final_audio_url
      || book?.audio_url
      || book?.audiobook?.final_audio_url
      || "",
  );
  const enabled = book?.audiobook_enabled === true
    || book?.audio_enabled === true
    || manifestAudio?.enabled === true;
  const hasReleaseApproval = releaseGate === "APPROVED";
  const hasQaApproval = ["QA_PASSED", "APPROVED", "PASS"].includes(qaStatus);
  const hasStaticAudioAsset = isStaticAudiobookAssetPath(audioUrl);
  const hasAudioAsset = Boolean(audioUrl) && !hasStaticAudioAsset;
  const hasReaderManifestApproval = manifestAudio?.enabled === true
    && Boolean(manifestAudio?.provider)
    && Boolean(manifestAudio?.version)
    && Boolean(assets.mp3 || manifestAudio?.url)
    && !hasStaticAudioAsset;
  const blocked = upper(book?.audio_status) === "BLOCKED"
    || book?.audio_disabled === true
    || upper(book?.audiobook?.status) === "BLOCKED";

  if (enabled && hasAudioAsset && !blocked && ((hasReleaseApproval && hasQaApproval) || hasReaderManifestApproval)) {
    return {
      status: "approved",
      canShowControls: true,
      label: "Audiobook approved",
      reason: hasReaderManifestApproval && !(hasReleaseApproval && hasQaApproval)
        ? "Reader manifest exposes an approved provider-backed audiobook endpoint."
        : "Release gate, listening QA, and audio asset are approved.",
      releaseGate,
      qaStatus,
      audioUrl,
      hasAudioAsset,
      syncMode: book?.sync_mode || book?.audiobook?.sync_mode || book?._readerManifest?.audio?.sync_mode || "",
      highlightSyncEnabled: book?.highlight_sync_enabled === true
        || book?.audiobook?.highlight_sync_enabled === true
        || book?._readerManifest?.audio?.highlight_sync_enabled === true,
    };
  }

  if (enabled || audioUrl || releaseGate || qaStatus) {
    return {
      status: "private_review",
      canShowControls: false,
      label: "Audiobook held for QA",
      reason: hasStaticAudioAsset
        ? "Same-origin static audiobook assets are not public release evidence."
        : "Audio exists or is configured, but public release approval is incomplete.",
      releaseGate,
      qaStatus,
      audioUrl,
      hasAudioAsset,
      syncMode: "",
      highlightSyncEnabled: false,
    };
  }

  return {
    status: "reader_only",
    canShowControls: false,
    label: "Reader-only edition",
    reason: "No approved public audiobook is attached to this title.",
    releaseGate,
    qaStatus,
    audioUrl,
    hasAudioAsset,
    syncMode: "",
    highlightSyncEnabled: false,
  };
}

export function canExposeAudiobookControls(book = {}) {
  return audiobookReleaseState(book).canShowControls;
}
