import { useEffect, useRef, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, Clock3, Minus, Plus, Settings2, StickyNote, X } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import "./reader-v2.css";
import "./reader-v2.mobile.css";
import BookCoverImage from "../../components/BookCoverImage";
import { PUBLIC_PREVIEW_COPY } from "../../lib/publicAccessCopy";
import { loadReaderNotebook, readerNotebookKey, saveReaderNotebook } from "../../lib/readerNotebook";
import {
  loadReaderSettings,
  READER_SETTINGS_DEFAULTS,
  READER_TEXT_SIZE_REM_STEPS,
  READER_TYPOGRAPHY_VERSION,
  saveReaderSettings,
} from "../../lib/readerSettings";

export const READER_V2_FIXTURE = Object.freeze({
  title: "Dracula",
  author: "Bram Stoker",
  chapterEyebrow: "Chapter 1",
  chapterTitle: "Jonathan Harker’s Journal",
  chapterDateline: "3 May 1897 · Bistritz to Vienna",
  editorialQuote: "All journeys have secret destinations of which the traveller is unaware.",
  canonicalPage: 1,
  totalPublicPages: 3,
  totalPages: 4,
  visualFixture: true,
  progress: null,
  readingTime: "",
  readingPass: "Sign in to check Reading Pass balance",
  contents: ["Chapter 1 · Jonathan Harker’s Journal", "Chapter 2 · The Carpathians", "Chapter 3 · The Count’s Castle", "Chapter 4 · The Visitor’s Diary"],
  illustration: {
    src: "/assets/reference-derived/reader-castle-board-crop.png",
    alt: "A sepia castle landscape",
  },
  paragraphs: [
    "3 May. Bistritz.—Left Munich at 8.35 P.M., on 1st May, arriving in Vienna early next morning; should have arrived at 6.46, but train was an hour late.",
    "The impression I had of the papers was that the Count Dracula was a remarkable man. There was something about him which impressed me favourably.",
    "I must try to get back as soon as possible. Mina will be so anxious about me.",
  ],
  metadata: { language: "English", genre: "Gothic Fiction", year: "1897", source: "Public Domain · Verified" },
});

export function readerPageAccess({ canonicalPage = 1, authorized = false } = {}) {
  const page = Number(canonicalPage);
  if (!Number.isInteger(page) || page < 1) return { canRequest: false, reason: "not_found" };
  if (page <= 3) return { canRequest: true, reason: "public_preview" };
  return authorized ? { canRequest: true, reason: "server_authorized" } : { canRequest: false, reason: "server_authorization_required" };
}

const LINE_SPACING = {
  // Preserve each language's existing leading, reduced by exactly 0.5pt.
  comfortable: { en: "calc(1.75em - 0.5pt)", bn: "calc(1.8em - 0.5pt)" },
  relaxed: { en: 1.88, bn: 1.93 },
  airy: { en: 2.02, bn: 2.08 },
};
const LANGUAGE_TYPOGRAPHY = {
  en: { size: 1.125, fontFamily: '"EB Garamond", Georgia, serif', fontWeight: 400 },
  bn: { size: 1.125, fontFamily: '"Noto Serif Bengali", serif', fontWeight: 500 },
};

function readerLanguage(language) {
  return language === "bn" ? "bn" : "en";
}

function formatRem(value) {
  return `${Number(value).toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}rem`;
}

function textSizeIndex(value) {
  return READER_TEXT_SIZE_REM_STEPS.indexOf(value);
}

export default function ReaderExperienceV2({ model = READER_V2_FIXTURE, access = {}, onRequestPage, onNavigate }) {
  const [settings, setSettings] = useState(() => {
    try { return loadReaderSettings(); } catch { return READER_SETTINGS_DEFAULTS; }
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const notebookKey = readerNotebookKey(model.slug || model.title, model.notebookOwner || "guest");
  const [savedNotebook, setSavedNotebook] = useState(() => ({ key: notebookKey, value: loadReaderNotebook(notebookKey) }));
  const notebook = savedNotebook.key === notebookKey ? savedNotebook.value : loadReaderNotebook(notebookKey);
  const [notebookOpen, setNotebookOpen] = useState(false);
  const [notebookTab, setNotebookTab] = useState("notes");
  const [noteText, setNoteText] = useState("");
  const [noteEditorOpen, setNoteEditorOpen] = useState(false);
  const [notebookNotice, setNotebookNotice] = useState("");
  const notebookTriggerRef = useRef(null);
  useEffect(() => {
    setSavedNotebook({ key: notebookKey, value: loadReaderNotebook(notebookKey) });
    setNoteText(""); setNoteEditorOpen(false); setNotebookOpen(false); setNotebookNotice("");
  }, [notebookKey]);
  const headingRef = useRef(null);
  const settingsTriggerRef = useRef(null);
  useEffect(() => {
    try { saveReaderSettings(settings); } catch { /* Reading stays usable when storage is blocked. */ }
  }, [settings]);

  const page = Number(model.canonicalPage) || 1;
  const navigationPage = Number(model.navigationPage) || page;
  useEffect(() => {
    // Keep keyboard context stable across page turns; announce only the
    // canonical page that has actually rendered.
    window.scrollTo({ top: 0, behavior: "instant" });
    headingRef.current?.focus({ preventScroll: true });
  }, []);
  const contents = (model.contents || []).map((item, index) => typeof item === "string"
    ? { page: index + 1, label: item }
    : { page: Number(item.page), label: item.label })
    .filter((item) => Number.isInteger(item.page) && item.page > 0);
  const declaredTotal = Number(model.totalPages);
  const totalPages = Number.isInteger(declaredTotal) && declaredTotal > 0
    ? declaredTotal : Math.max(page, Number(model.totalPublicPages) || 1, ...contents.map((item) => item.page));
  const progress = model.progress == null ? null : Math.min(100, Math.max(0, Number(model.progress) || 0));
  const metadata = model.metadata || {};
  const language = readerLanguage(model.language);
  const languageTypography = LANGUAGE_TYPOGRAPHY[language];
  const textSizeRem = settings.readerTextSizeRem ?? languageTypography.size;
  const textSizeStep = textSizeIndex(textSizeRem);
  const lineHeight = LINE_SPACING[settings.lineSpacingMode]?.[language] || LINE_SPACING.comfortable[language];
  const fontMode = settings.readerFontFamilyPreference || (language === "bn" ? "sans" : "serif");
  const fontFamily = fontMode === "sans"
    ? (language === "bn" ? '"Noto Sans Bengali", sans-serif' : 'Outfit, sans-serif')
    : languageTypography.fontFamily;
  const fontWeight = fontMode === "sans" ? (language === "bn" ? 500 : 400) : languageTypography.fontWeight;
  const busy = Boolean(access.busy);
  const bookmarked = notebook.bookmarks.includes(page);
  const updateNotebook = (value) => {
    const saved = saveReaderNotebook(notebookKey, value);
    setSavedNotebook({ key: notebookKey, value });
    setNotebookNotice(saved ? "Saved on this device." : "Storage is unavailable. Your changes last for this reading session only.");
  };
  const toggleBookmark = () => updateNotebook({ ...notebook, bookmarks: bookmarked
    ? notebook.bookmarks.filter((item) => item !== page) : [...notebook.bookmarks, page] });
  const addNote = (event) => {
    event.preventDefault();
    if (!noteText.trim() || notebook.notes.length >= 100) return;
    updateNotebook({ ...notebook, notes: [...notebook.notes, { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, page, text: noteText.trim(), createdAt: new Date().toISOString() }] });
    setNoteText(""); setNoteEditorOpen(false);
  };
  const closeNotebook = () => { setNotebookOpen(false); notebookTriggerRef.current?.focus(); };
  const atEnd = navigationPage >= totalPages;
  const nextLabel = navigationPage === 3 && !access.authorized
    ? (model.freeReading ? "Continue reading free" : "Use Reading Time to Continue")
    : "Next page";
  const updateSetting = (name, value) => setSettings((previous) => ({ ...previous, [name]: value }));
  const updateTextSize = (value) => setSettings((previous) => ({
    ...previous,
    readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
    readerTextSizeRem: Number(value),
  }));
  const updateFontFamily = (value) => setSettings((previous) => ({
    ...previous,
    // Preserve the existing shared field for the legacy Reader while keeping
    // V2's explicit override separate from language-specific defaults.
    fontFamilyMode: value,
    readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
    readerFontFamilyPreference: value,
  }));
  const resetTypography = () => setSettings((previous) => ({
    ...previous,
    lineSpacingMode: READER_SETTINGS_DEFAULTS.lineSpacingMode,
    readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
    readerTextSizeRem: null,
    readerFontFamilyPreference: null,
  }));
  const toggleSettings = (event) => {
    settingsTriggerRef.current = event.currentTarget;
    setSettingsOpen((open) => !open);
  };
  const closeSettings = () => {
    setSettingsOpen(false);
    settingsTriggerRef.current?.focus({ preventScroll: true });
  };
  const resizeText = (step) => {
    const next = Math.max(0, Math.min(READER_TEXT_SIZE_REM_STEPS.length - 1, textSizeStep + step));
    updateTextSize(READER_TEXT_SIZE_REM_STEPS[next]);
  };
  const requestPage = (requestedPage) => {
    const target = Number(requestedPage);
    if (busy || !Number.isInteger(target) || target < 1 || target > totalPages || target === page) return;
    // Navigation requests never grant access. The route authorizes protected
    // pages before it fetches or displays their contents.
    onRequestPage?.(target);
  };

  return (
    <ExperienceShell className="reader-v2" labelledBy="reader-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} onNavigate={onNavigate} onNavigatePath={(item) => onNavigate?.(item.key === "reading-pass" ? "passes" : item.key === "about" ? "about" : item.key, item.to)} trailingLabel="Library" showDesktopNavigation />
      <header className="reader-v2__mobile-topbar" aria-label="Reader actions">
        <button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button>
        <span><small>Page</small>{page} of {totalPages}</span>
        <div>
          <button type="button" onClick={() => resizeText(-1)} disabled={textSizeStep === 0} aria-label="Decrease text size">A−</button>
          <button type="button" onClick={() => resizeText(1)} disabled={textSizeStep === READER_TEXT_SIZE_REM_STEPS.length - 1} aria-label="Increase text size">A+</button>
          <button type="button" onClick={toggleSettings} aria-label="Reader settings" aria-expanded={settingsOpen} aria-controls="reader-v2-settings"><Settings2 size={17} /></button>
        </div>
      </header>
      <div className="reader-v2__layout">
        <aside className="reader-v2__rail" aria-label="Reader controls">
          <div className="reader-v2__book"><h2>{model.title}</h2><span>{model.author}</span></div>
          {progress !== null && <div className="reader-v2__metric"><span>Reading Progress</span><strong>{progress}%</strong><i><b style={{ width: `${progress}%` }} /></i></div>}
          {model.readingTime && <div className="reader-v2__metric"><span>Estimated time left</span><strong>{model.readingTime}</strong></div>}
          <ExperiencePanel eyebrow="Contents" className="reader-v2__contents"><ol>{contents.filter((item) => item.page <= totalPages).map((item) => <li key={item.page}><button type="button" aria-current={item.page === page ? "page" : undefined} disabled={busy} onClick={() => requestPage(item.page)}>{item.label}</button></li>)}</ol></ExperiencePanel>
          {model.freeReading
            ? <ExperiencePanel eyebrow="Free Reader access"><p>Read this complete edition without payment or Reading Pass debit.</p></ExperiencePanel>
            : <ExperiencePanel eyebrow="Reading Pass"><p>{model.readingPass}</p><button type="button" onClick={() => onNavigate?.(model.visualFixture ? "signin" : "passes")}>{model.visualFixture ? "Sign in to check balance" : "Extend Reading Time"}</button></ExperiencePanel>}
        </aside>

        <article className="reader-v2__canvas" data-reader-theme={settings.theme} data-reader-language={language} aria-busy={busy} lang={model.language || undefined}>
          <header className="reader-v2__chapter">
            <span aria-live="polite" aria-atomic="true">{model.chapterEyebrow}</span>
            <div className="reader-v2__toolbar">
              <ExperienceIconButton label="Decrease text size" disabled={textSizeStep === 0} onClick={() => resizeText(-1)}><Minus size={16} /></ExperienceIconButton>
              <output aria-label="Text size">Aa · {formatRem(textSizeRem)}</output>
              <ExperienceIconButton label="Increase text size" disabled={textSizeStep === READER_TEXT_SIZE_REM_STEPS.length - 1} onClick={() => resizeText(1)}><Plus size={16} /></ExperienceIconButton>
              <ExperienceIconButton label="Reader settings" pressed={settingsOpen} onClick={toggleSettings}><Settings2 size={16} /></ExperienceIconButton>
              <ExperienceIconButton label={bookmarked ? "Remove page bookmark" : "Bookmark this page"} pressed={bookmarked} onClick={toggleBookmark}><Bookmark size={16} /></ExperienceIconButton>
            </div>
            <h1 id="reader-v2-title" ref={headingRef} tabIndex={-1}>{model.chapterTitle}</h1>
            {model.chapterDateline && <p className="reader-v2__dateline">{model.chapterDateline}</p>}
          </header>
          {settingsOpen && <section id="reader-v2-settings" className="reader-v2__settings" aria-label="Reading preferences">
            <h2>Reading preferences</h2>
            <label>Theme<select value={settings.theme} onChange={(event) => updateSetting("theme", event.target.value)}><option value="beige">Light</option><option value="sepia">Sepia</option><option value="dark">Night</option></select></label>
            <label>Text size<select value={textSizeRem} onChange={(event) => updateTextSize(event.target.value)}>{READER_TEXT_SIZE_REM_STEPS.map((size) => <option key={size} value={size}>{formatRem(size)}</option>)}</select></label>
            <label>Line spacing<select value={settings.lineSpacingMode} onChange={(event) => updateSetting("lineSpacingMode", event.target.value)}><option value="comfortable">Comfortable</option><option value="relaxed">Relaxed</option><option value="airy">Airy</option></select></label>
            <label>Font<select value={fontMode} onChange={(event) => updateFontFamily(event.target.value)}><option value="sans">Clear sans serif</option><option value="serif">Literary serif</option></select></label>
            <button type="button" onClick={resetTypography}>Reset typography</button>
            <button type="button" onClick={closeSettings}>Close preferences</button>
          </section>}
          <label className="reader-v2__page-selector">Go to page<select aria-label="Go to page" value={page} disabled={busy} onChange={(event) => requestPage(event.target.value)}>{Array.from({ length: totalPages }, (_, index) => <option key={index + 1} value={index + 1}>Page {index + 1}</option>)}</select></label>
          {model.pendingPage && <p className="reader-v2__page-loading" role="status">Opening page {model.pendingPage}…</p>}
          <div key={page} className="reader-v2__page-content" data-testid="reader-page-content">
            <div className="reader-v2__body" data-testid="reader-reading-text" style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }}>
              {model.content ?? (model.paragraphs || []).map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 16)}`}>{paragraph}</p>)}
            </div>
          </div>
          {model.pageError && <p className="reader-v2__status" role={model.pageErrorDenied ? "alert" : "status"}>
            {model.pageError}
            {model.pageErrorRetryable && <button type="button" onClick={() => requestPage(navigationPage)}>Retry page</button>}
          </p>}
          {model.statusMessage && <p className="reader-v2__status" role="status">{model.statusMessage}</p>}
          <footer className="reader-v2__continuation">
            <span>{atEnd ? "You have reached the end of this book." : page <= 3 ? PUBLIC_PREVIEW_COPY : `Page ${page} of ${totalPages}`}</span>
            <nav aria-label="Page navigation">
              <button type="button" disabled={busy || navigationPage <= 1} onClick={() => requestPage(navigationPage - 1)}><ChevronLeft size={16} /> Previous page</button>
              <button type="button" disabled={busy || atEnd} onClick={() => requestPage(navigationPage + 1)}>{atEnd ? "End of book" : nextLabel} <ChevronRight size={16} /></button>
            </nav>
          </footer>
        </article>

        <aside id="reader-notebook" className="reader-v2__context" data-notebook-open={notebookOpen} aria-label="Notes and bookmarks" onKeyDown={(event) => { if (event.key === "Escape" && notebookOpen) closeNotebook(); }}>
          <button type="button" className="reader-v2__notebook-close" onClick={closeNotebook} aria-label="Close notes and bookmarks"><X size={18} /></button>
          {model.illustration?.src
            ? <figure className="reader-v2__artwork" data-quote={Boolean(model.editorialQuote)}><img className="reader-v2__illustration" src={model.illustration.src} alt={model.illustration.alt || ""} decoding="async" /><figcaption>{model.editorialQuote ? <><blockquote>“{model.editorialQuote}”</blockquote><cite>— {model.author}</cite></> : <>{model.title}{model.author ? ` · ${model.author}` : ""}</>}</figcaption></figure>
            : model.book && <BookCoverImage book={model.book} alt={`${model.title} cover`} className="reader-v2__book-cover" loading="lazy" width={520} widths={[280, 420, 520]} sizes="(min-width: 1280px) 16rem, 40vw" allowGraphicalFallback={false} fallback="" />}
          <section className="reader-v2__notebook" aria-label="Your reading notebook">
            <div className="reader-v2__notebook-tabs" role="tablist" aria-label="Notebook views">
              <button id="reader-notes-tab" role="tab" type="button" aria-selected={notebookTab === "notes"} aria-controls="reader-notebook-panel" onClick={() => setNotebookTab("notes")}>Notes</button>
              <button id="reader-bookmarks-tab" role="tab" type="button" aria-selected={notebookTab === "bookmarks"} aria-controls="reader-notebook-panel" onClick={() => setNotebookTab("bookmarks")}>Bookmarks</button>
            </div>
            <div id="reader-notebook-panel" role="tabpanel" aria-labelledby={`reader-${notebookTab}-tab`}>
              {notebookTab === "notes" ? <>
                {notebook.notes.length ? <ul className="reader-v2__note-list">{notebook.notes.map((note) => <li key={note.id}><button type="button" onClick={() => requestPage(note.page)}>Page {note.page}</button><p>{note.text}</p><button type="button" aria-label={`Delete note on page ${note.page}`} onClick={() => updateNotebook({ ...notebook, notes: notebook.notes.filter((item) => item.id !== note.id) })}>Delete note</button></li>)}</ul> : <p className="reader-v2__notebook-empty">Keep a thought from this page.</p>}
                {noteEditorOpen ? <form onSubmit={addNote}><label>Note for page {page}<textarea autoFocus value={noteText} maxLength={2000} onChange={(event) => setNoteText(event.target.value)} /></label><button type="submit" disabled={!noteText.trim()}>Save note</button><button type="button" onClick={() => setNoteEditorOpen(false)}>Cancel</button></form> : <button type="button" className="reader-v2__add-note" disabled={notebook.notes.length >= 100} onClick={() => setNoteEditorOpen(true)}><Plus size={15} /> New note</button>}
              </> : <>{notebook.bookmarks.length ? <ul className="reader-v2__bookmark-list">{notebook.bookmarks.map((item) => <li key={item}><button type="button" disabled={busy} onClick={() => requestPage(item)}>Page {item}</button></li>)}</ul> : <p className="reader-v2__notebook-empty">Your saved pages appear here.</p>}<button type="button" onClick={toggleBookmark}>{bookmarked ? "Remove page bookmark" : "Bookmark this page"}</button></>}
            </div>
            <p className="reader-v2__notebook-storage">Notes and bookmarks stay on this device.</p>
            {notebookNotice && <p role="status">{notebookNotice}</p>}
          </section>
          <details className="reader-v2__edition-details"><summary>About this edition</summary><dl>{model.author && <div><dt>Author</dt><dd>{model.author}</dd></div>}{metadata.language && <div><dt>Language</dt><dd>{metadata.language}</dd></div>}{metadata.genre && <div><dt>Genre</dt><dd>{metadata.genre}</dd></div>}{metadata.year && <div><dt>First published</dt><dd>{metadata.year}</dd></div>}{metadata.source && <div><dt>Edition</dt><dd>{metadata.source}</dd></div>}</dl></details>
        </aside>
      </div>
      <div className="reader-v2__mobile-actions"><button ref={notebookTriggerRef} type="button" onClick={() => setNotebookOpen((open) => !open)} aria-label="Open notes and bookmarks" aria-expanded={notebookOpen} aria-controls="reader-notebook"><StickyNote size={18} /></button><span><Clock3 size={14} /> {model.readingPass}</span><button type="button" onClick={() => { toggleBookmark(); onNavigate?.("bookmark"); }} aria-label="Save current page" aria-pressed={bookmarked}><Bookmark size={18} /></button></div>
      <div className="reader-v2__reader-navigation"><ExperienceBottomNavigation active="library" onNavigate={onNavigate} /></div>
    </ExperienceShell>
  );
}
