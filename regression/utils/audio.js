function audioLanguage(book) {
  const text = `${book.title || ""} ${book.description || ""} ${book.short_description || ""}`;
  return /[\u0980-\u09ff]/.test(text) ? "ben" : "en";
}

function publicAudioSlug(book) {
  return book.audio_asset_slug || book.slug;
}

function audioMarkedAvailable(book) {
  return Boolean(book.audiobook_enabled || book.generate_audiobook);
}

function audioAssetCandidates(book) {
  const assets = book.audiobook_assets || {};
  const doc = book.audiobook || {};
  return {
    audio: doc.url || doc.mp3 || assets.mp3 || "",
    timestamps: doc.timestamps || assets.timestamps || "",
    vtt: doc.vtt || assets.vtt || "",
  };
}

function manifestAudio(manifest) {
  const audio = manifest?.audio || {};
  const assets = audio.assets || {};
  return {
    enabled: Boolean(audio.enabled),
    provider: audio.provider || "",
    audio: audio.url || assets.mp3 || "",
    timestamps: assets.timestamps || audio.timestamps || "",
    vtt: assets.vtt || audio.vtt || "",
  };
}

module.exports = {
  audioLanguage,
  publicAudioSlug,
  audioMarkedAvailable,
  audioAssetCandidates,
  manifestAudio,
};
