const PREFIX = "earnalism:reader-notebook:v1:";

export function readerNotebookKey(edition, owner = "guest") {
  return `${PREFIX}${encodeURIComponent(owner)}:${encodeURIComponent(edition)}`;
}

export function normalizeNotebook(value) {
  return {
    notes: (Array.isArray(value?.notes) ? value.notes : []).filter((note) =>
      typeof note?.id === "string" && Number.isInteger(note.page) && note.page > 0
      && typeof note.text === "string" && note.text.trim()
    ).slice(0, 100).map((note) => ({ id: note.id, page: note.page, text: note.text.slice(0, 2000), createdAt: String(note.createdAt || "") })),
    bookmarks: [...new Set((Array.isArray(value?.bookmarks) ? value.bookmarks : [])
      .filter((page) => Number.isInteger(page) && page > 0))].sort((a, b) => a - b).slice(0, 100),
  };
}

export function loadReaderNotebook(key) {
  try { return normalizeNotebook(JSON.parse(window.localStorage.getItem(key))); }
  catch { return normalizeNotebook(null); }
}

export function saveReaderNotebook(key, notebook) {
  try { window.localStorage.setItem(key, JSON.stringify(normalizeNotebook(notebook))); return true; }
  catch { return false; }
}
