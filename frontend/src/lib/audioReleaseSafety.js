function clean(value = "") {
  return String(value || "").trim();
}

function upper(value = "") {
  return clean(value).toUpperCase();
}

export const READER_MANIFEST_RELEASE_TRUTH_VERSION = "audio-release-evidence-v6";

export function readerManifestPath(slug, { adminPreview = false } = {}) {
  const params = new URLSearchParams({
    release_truth: READER_MANIFEST_RELEASE_TRUTH_VERSION,
  });
  if (adminPreview) params.set("preview", "admin");
  return `/reader/book/${encodeURIComponent(clean(slug))}/manifest?${params.toString()}`;
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
      || manifestAudio?.url
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
    && hasReleaseApproval
    && hasQaApproval
    && !hasStaticAudioAsset;
  const blocked = upper(book?.audio_status) === "BLOCKED"
    || book?.audio_disabled === true
    || upper(book?.audiobook?.status) === "BLOCKED";

  if (enabled && hasAudioAsset && !blocked && hasReleaseApproval && hasQaApproval) {
    return {
      status: "approved",
      canShowControls: true,
      label: "Audiobook available",
      reason: hasReaderManifestApproval
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
      label: "Reader edition available",
      reason: hasStaticAudioAsset
        ? "Same-origin static audiobook assets are not public release evidence."
        : "Audio will appear only after narration, sync, and browser gates pass.",
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
