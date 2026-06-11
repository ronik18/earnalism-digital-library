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

module.exports = { audioLanguage, publicAudioSlug, audioMarkedAvailable };
