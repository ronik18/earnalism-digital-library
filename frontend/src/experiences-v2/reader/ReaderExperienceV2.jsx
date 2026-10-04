import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, Clock3, Minus, Plus, Settings2, StickyNote, X } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import "./reader-v2.css";
import "./reader-pagination.css";
import ReaderOpening from "./ReaderOpening";
import useAuthorizedBookMap from "./useAuthorizedBookMap";
import { ReaderContent } from "./readerContent";
import useVisualPagination from "./useVisualPagination";
import { pageForAnchor } from "./visualPagination";
import "./reader-v2.mobile.css";
import BookCoverImage from "../../components/BookCoverImage";
import LicensedTextNotice from "../../components/LicensedTextNotice";
import { approvedTextLicense } from "../../lib/textLicense";
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
  const sourceRef = useRef(null);
  const viewportRef = useRef(null);
  const measureRef = useRef(null);
  const [localAnchor, setLocalAnchor] = useState(0);
  const anchor = model.visualAnchor ?? localAnchor;
  const pagination = useVisualPagination({ sourceRef, viewportRef, measureRef,
    authorizationScope: model.bookMapScope,
    revision: model.sourceRevision || `${page}:${model.chapterTitle}`,
    typography: `${textSizeRem}:${lineHeight}:${fontFamily}:${fontWeight}` });
  const visualIndex = anchor === 'end' ? Math.max(0, pagination.pages.length - 1) : pageForAnchor(pagination.pages, Number(anchor) || 0);
  const fragment = pagination.pages[visualIndex];
  const visualTotal = pagination.pages.length;
  const bookMap = useAuthorizedBookMap({ model, pagination, visualIndex, viewportRef,
    typography: `${textSizeRem}:${lineHeight}:${fontFamily}:${fontWeight}` });
  const pageIndicator = bookMap.complete && model.visualPageScope !== "chapter" ? `${bookMap.currentNumber || visualIndex + 1} of ${bookMap.total}`
    : `${visualIndex + 1} of ${visualTotal || '…'} in this chapter`;
  const mapSelection = bookMap.options.find(option => option.chapterId === model.authorizedChapter?.plan.chapterId && option.start === fragment?.start)?.key || '';
  const onVisualAnchor = model.onVisualAnchor;
  const changeAnchor = useCallback((offset) => {
    setLocalAnchor(offset);
    onVisualAnchor?.(offset);
  }, [onVisualAnchor]);
  const sourceAnchor = model.sourceAnchorForOffset?.(fragment?.start || 0);
  const readingAnchor = sourceAnchor ? { offset: sourceAnchor.offset, revision: sourceAnchor.revision } : { offset: fragment?.start || 0, revision: model.sourceRevision || '' };
  const anchorPage = sourceAnchor?.page || page;
  const windowFirst = model.windowFirst ?? navigationPage;
  const windowLast = model.windowLast ?? navigationPage;
  const hasPaginated = useRef(false);
  const openingHasFocus = useRef(false);
  const [failedLayout, setFailedLayout] = useState('');
  const layoutKey = `${pagination.signature}:${fragment?.start}`;
  const layoutError = failedLayout === layoutKey ? 'This page could not be fitted safely. Change the text setting or viewport to retry.' : pagination.error;
  useLayoutEffect(() => {
    if (pagination.pending || !fragment || !viewportRef.current) return;
    hasPaginated.current = true;
    if (openingHasFocus.current) { headingRef.current?.focus(); openingHasFocus.current = false; }
    if (viewportRef.current.scrollHeight > viewportRef.current.clientHeight + 1) {
      // Reject a mismatched rendered result before paint; never reveal clipped prose.
      viewportRef.current.setAttribute('data-pagination-overflow', 'true');
      setFailedLayout(layoutKey);
    } else viewportRef.current.removeAttribute('data-pagination-overflow');
  }, [fragment, pagination.pending, layoutKey]);
  const onVisualPageVisibility = model.onVisualPageVisibility;
  useLayoutEffect(() => {
    onVisualPageVisibility?.(!pagination.pending && fragment && !layoutError ? { start: fragment.start, end: fragment.end } : null);
    return () => onVisualPageVisibility?.(null);
  }, [fragment, pagination.pending, layoutError, onVisualPageVisibility]);
  const busy = Boolean(access.busy);
  const matchesCurrentAnchor = (item) => {
    const mapped = model.offsetForSourceAnchor?.(item.page, item.anchor.offset, item.anchor.revision);
    return mapped != null ? mapped >= (fragment?.start || 0) && mapped < Math.max(fragment?.end || 1, 1)
      : item.page === page && item.anchor.revision === readingAnchor.revision
        && item.anchor.offset >= (fragment?.start || 0) && item.anchor.offset < Math.max(fragment?.end || 1, 1);
  };
  const bookmarkAnchors = notebook.bookmarkAnchors || [];
  const bookmarked = bookmarkAnchors.some(matchesCurrentAnchor)
    || (notebook.bookmarks.includes(anchorPage) && !bookmarkAnchors.some(item => item.page === anchorPage));
  const updateNotebook = (value) => {
    const saved = saveReaderNotebook(notebookKey, value);
    setSavedNotebook({ key: notebookKey, value });
    setNotebookNotice(saved ? "Saved on this device." : "Storage is unavailable. Your changes last for this reading session only.");
  };
  const toggleBookmark = () => {
    const anchors = bookmarked ? bookmarkAnchors.filter(item => !matchesCurrentAnchor(item))
      : [...bookmarkAnchors, { page: anchorPage, anchor: readingAnchor }];
    updateNotebook({ ...notebook, bookmarkAnchors: anchors, bookmarks: bookmarked && !anchors.some(item => item.page === anchorPage)
      ? notebook.bookmarks.filter(item => item !== anchorPage) : [...new Set([...notebook.bookmarks, anchorPage])] });
  };
  const addNote = (event) => {
    event.preventDefault();
    if (!noteText.trim() || notebook.notes.length >= 100) return;
    updateNotebook({ ...notebook, notes: [...notebook.notes, { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, page: anchorPage, anchor: readingAnchor, text: noteText.trim(), createdAt: new Date().toISOString() }] });
    setNoteText(""); setNoteEditorOpen(false);
  };
  const closeNotebook = () => { setNotebookOpen(false); notebookTriggerRef.current?.focus(); };
  const atEnd = !pagination.pending && Boolean(fragment) && windowLast >= totalPages && visualIndex >= visualTotal - 1;
  const nextLabel = windowLast === (model.previewLimit || 3) && !access.authorized && visualIndex === visualTotal - 1
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
  const offsetForSourceAnchor = model.offsetForSourceAnchor;
  const previousWindow = model.previousWindow;
  const nextWindow = model.nextWindow;
  const requestPage = useCallback((requestedPage, offset = 0, revision) => {
    const target = Number(requestedPage);
    const mapped = offsetForSourceAnchor?.(target, offset, revision);
    if (!busy && mapped != null) { changeAnchor(mapped); return; }
    if (busy || !Number.isInteger(target) || target < 1 || target > totalPages || target === page) { if (target === page && (!revision || revision === readingAnchor.revision)) changeAnchor(offset); return; }
    // Navigation requests never grant access. The route authorizes protected
    // pages before it fetches or displays their contents.
    if (revision) onRequestPage?.(target, offset, revision); else if (offset) onRequestPage?.(target, offset); else onRequestPage?.(target);
  }, [busy, totalPages, page, onRequestPage, changeAnchor, readingAnchor.revision, offsetForSourceAnchor]);

  const turnVisualPage = useCallback((direction) => {
    if (busy || pagination.pending || layoutError) return;
    const next = visualIndex + direction;
    if (next >= 0 && next < visualTotal) changeAnchor(pagination.pages[next].start);
    else requestPage(direction < 0 ? (previousWindow ?? windowFirst - 1) : (nextWindow ?? windowLast + 1), direction < 0 ? 'end' : 0);
  }, [busy, pagination, visualIndex, visualTotal, changeAnchor, requestPage, layoutError, previousWindow, nextWindow, windowFirst, windowLast]);
  const [pageTurn, setPageTurn] = useState({ page, offset: fragment?.start || 0, direction: "next" });
  if (pageTurn.page !== page || pageTurn.offset !== (fragment?.start || 0)) setPageTurn({ page, offset: fragment?.start || 0, direction: page < pageTurn.page || (page === pageTurn.page && (fragment?.start || 0) < pageTurn.offset) ? "previous" : "next" });
  const canvasRef = useRef(null);
  useEffect(() => { canvasRef.current?.scrollTo?.({ top: 0, behavior: "instant" }); }, [page]);
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || settingsOpen || notebookOpen) return;
      const target = event.target;
      if (target instanceof HTMLElement && (target.isContentEditable || target.closest('input, textarea, select, button, a, [role="slider"], [role="combobox"], [role="listbox"], [role="menu"], [role="tablist"], audio, video, [contenteditable="true"]'))) return;
      if (event.key === "ArrowLeft" && (windowFirst > 1 || visualIndex > 0)) { event.preventDefault(); turnVisualPage(-1); }
      if (event.key === "ArrowRight" && !atEnd) { event.preventDefault(); turnVisualPage(1); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [turnVisualPage, navigationPage, visualIndex, atEnd, settingsOpen, notebookOpen, windowFirst]);

  return (
    <ExperienceShell className="reader-v2" labelledBy="reader-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} onNavigate={onNavigate} onNavigatePath={(item) => onNavigate?.(item.key === "reading-pass" ? "passes" : item.key === "about" ? "about" : item.key, item.to)} trailingLabel="Library" showDesktopNavigation />
      <header className="reader-v2__mobile-topbar" aria-label="Reader actions">
        <button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button>
        <span><small>Page</small>{pageIndicator}<small>Section {page} of {totalPages}</small></span>
        <div>
          <button type="button" onClick={() => resizeText(-1)} disabled={textSizeStep === 0} aria-label="Decrease text size">A−</button>
          <button type="button" onClick={() => resizeText(1)} disabled={textSizeStep === READER_TEXT_SIZE_REM_STEPS.length - 1} aria-label="Increase text size">A+</button>
          <button type="button" onClick={toggleSettings} aria-label="Reader settings" aria-expanded={settingsOpen} aria-controls="reader-v2-settings"><Settings2 size={17} /></button>
        </div>
      </header>
      <div className="reader-v2__layout">
        {pagination.pending && !hasPaginated.current && <div className="reader-v2__pagination-opening"><ReaderOpening embedded book={{ title: model.title, author: model.author }} onLibrary={() => onNavigate?.("library")} onEscapeFocus={focused => { openingHasFocus.current = focused; }} busy={busy} /></div>}
        <aside className="reader-v2__rail" aria-label="Reader controls">
          <div className="reader-v2__book"><h2>{model.title}</h2><span>{model.author}</span></div>
          {progress !== null && <div className="reader-v2__metric"><span>Reading Progress</span><strong>{progress}%</strong><i><b style={{ width: `${progress}%` }} /></i></div>}
          {model.readingTime && <div className="reader-v2__metric"><span>Estimated time left</span><strong>{model.readingTime}</strong></div>}
          <ExperiencePanel eyebrow="Contents" className="reader-v2__contents"><ol>{contents.filter((item) => item.page <= totalPages).map((item) => <li key={item.page}><button type="button" aria-current={item.page === page ? "page" : undefined} disabled={busy} onClick={() => requestPage(item.page)}>{item.label}</button></li>)}</ol></ExperiencePanel>
          {model.freeReading
            ? <ExperiencePanel eyebrow="Free Reader access"><p>Read this complete edition without payment or Reading Pass debit.</p></ExperiencePanel>
            : <ExperiencePanel eyebrow="Reading Pass"><p>{model.readingPass}</p><button type="button" onClick={() => onNavigate?.(model.visualFixture ? "signin" : "passes")}>{model.visualFixture ? "Sign in to check balance" : "Extend Reading Time"}</button></ExperiencePanel>}
        </aside>

        <div className="reader-v2__page-frame">
          <button className="reader-v2__page-arrow reader-v2__page-arrow--previous" type="button" aria-label="Previous page" disabled={busy || pagination.pending || (windowFirst <= 1 && visualIndex <= 0)} onClick={() => turnVisualPage(-1)}><ChevronLeft size={22} strokeWidth={1.6} aria-hidden="true" /></button>
          <button className="reader-v2__page-arrow reader-v2__page-arrow--next" type="button" aria-label="Next page" disabled={busy || pagination.pending || atEnd} onClick={() => turnVisualPage(1)}><ChevronRight size={22} strokeWidth={1.6} aria-hidden="true" /></button>
        <article ref={canvasRef} className="reader-v2__canvas" data-licensed-text={approvedTextLicense(model.book) ? "true" : undefined} data-reader-theme={settings.theme} data-reader-language={language} aria-busy={busy} lang={model.language || undefined}>
          <header className="reader-v2__chapter">
            <span aria-live="polite" aria-atomic="true">Page {pageIndicator} · section {page} of {totalPages}</span>
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
          <label className="reader-v2__page-selector">Go to page{bookMap.options.length ? <select aria-label="Go to page" value={mapSelection} disabled={busy || pagination.pending} onChange={event => {
            const option = bookMap.options.find(item => item.key === event.target.value);
            if (option) requestPage(option.anchor.page, option.anchor.offset, option.anchor.revision);
          }}>{bookMap.options.map(option => <option key={option.key} value={option.key}>{option.label}</option>)}</select> : <select aria-label="Go to page" value={visualIndex} disabled={busy || pagination.pending} onChange={event => pagination.pages[Number(event.target.value)] && changeAnchor(pagination.pages[Number(event.target.value)].start)}>{pagination.pages.map((_, index) => <option key={index} value={index}>Page {index + 1}</option>)}</select>}</label>
          {model.pendingPage && <p className="reader-v2__page-loading" role="status">Opening page {model.pendingPage}…</p>}
          <div ref={viewportRef} className="reader-v2__visual-viewport" data-pagination-diagnostic={process.env.NODE_ENV === 'development' ? pagination.errorReason : undefined} data-layout-width={pagination.width} data-layout-height={pagination.height} data-pagination-ready={!pagination.pending && !layoutError} data-transport-chunks={model.transportChunkCount} data-manifest-ms={model.assemblyMetrics?.manifestMs} data-network-ms={model.assemblyMetrics?.networkMs} data-verification-ms={model.assemblyMetrics?.verificationMs} data-fetch-ms={model.assemblyMetrics?.fetchMs} data-assembly-ms={model.assemblyMetrics?.assemblyMs} data-pagination-ms={pagination.durationMs} data-pagination-cached={pagination.cached} data-chapter-id={model.authorizedChapter?.plan.chapterId} data-source-page={sourceAnchor?.page} data-source-offset={sourceAnchor?.offset} data-page-start={fragment?.start} data-page-end={fragment?.end} data-book-page-count={bookMap.total ?? undefined} data-book-map-complete={bookMap.complete} data-page-count={visualTotal} data-visual-page-index={visualIndex}>
            <div ref={sourceRef} className="reader-v2__body reader-v2__pagination-source" aria-hidden="true" inert={true} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }}>
              {model.content ?? (model.paragraphs || []).map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 16)}`}>{paragraph}</p>)}
            </div>
            <div ref={bookMap.sourceRef} className="reader-v2__body reader-v2__pagination-source" aria-hidden="true" inert={true} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }}>
              {bookMap.candidate && <ReaderContent html={bookMap.candidate.html} />}
            </div>
            <div ref={bookMap.measureRef} className="reader-v2__body reader-v2__pagination-measure" aria-hidden="true" inert={true} />
            <div ref={measureRef} className="reader-v2__body reader-v2__pagination-measure" aria-hidden="true" inert={true} />
            {pagination.pending ? <p className="reader-v2__pagination-status" role={hasPaginated.current ? "status" : undefined} aria-hidden={!hasPaginated.current}>Preparing this page…</p> : layoutError ? <p role="alert">{layoutError}</p> :
              <div key={`${page}:${fragment?.start}`} className={`reader-v2__page-content reader-v2__page-content--${pageTurn.direction}`} data-testid="reader-page-content">
                <div className="reader-v2__body" data-testid="reader-reading-text" data-continuation={fragment?.start > 0} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }} dangerouslySetInnerHTML={{ __html: fragment?.html || '' }} />
              </div>}
          </div>
          {model.pageError && <p className="reader-v2__status" role={model.pageErrorDenied ? "alert" : "status"}>
            {model.pageError}
            {model.pageErrorRetryable && <button type="button" onClick={() => requestPage(navigationPage)}>Retry page</button>}
          </p>}
          {model.statusMessage && <p className="reader-v2__status" role="status">{model.statusMessage}</p>}
          <LicensedTextNotice book={model.book} />
          <footer className="reader-v2__continuation">
            <span>{atEnd ? "You have reached the end of this book." : model.windowFirst != null ? (access.authorized ? "Authorized chapter" : "Free preview") : page <= 3 ? PUBLIC_PREVIEW_COPY : `Page ${page} of ${totalPages}`}</span>
            <nav aria-label="Page navigation">
              <button type="button" disabled={busy || pagination.pending || (windowFirst <= 1 && visualIndex <= 0)} onClick={() => turnVisualPage(-1)}><ChevronLeft size={16} /> Previous page</button>
              <button type="button" disabled={busy || pagination.pending || atEnd} onClick={() => turnVisualPage(1)}>{atEnd ? "End of book" : nextLabel} <ChevronRight size={16} /></button>
            </nav>
          </footer>
        </article>
        </div>

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
                {notebook.notes.length ? <ul className="reader-v2__note-list">{notebook.notes.map((note) => <li key={note.id}><button type="button" onClick={() => requestPage(note.page, note.anchor?.offset || 0, note.anchor?.revision)}>Section {note.page}</button><p>{note.text}</p><button type="button" aria-label={`Delete note on page ${note.page}`} onClick={() => updateNotebook({ ...notebook, notes: notebook.notes.filter((item) => item.id !== note.id) })}>Delete note</button></li>)}</ul> : <p className="reader-v2__notebook-empty">Keep a thought from this page.</p>}
                {noteEditorOpen ? <form onSubmit={addNote}><label>Note for page {page}<textarea autoFocus value={noteText} maxLength={2000} onChange={(event) => setNoteText(event.target.value)} /></label><button type="submit" disabled={!noteText.trim()}>Save note</button><button type="button" onClick={() => setNoteEditorOpen(false)}>Cancel</button></form> : <button type="button" className="reader-v2__add-note" disabled={notebook.notes.length >= 100} onClick={() => setNoteEditorOpen(true)}><Plus size={15} /> New note</button>}
              </> : <>{notebook.bookmarks.length ? <ul className="reader-v2__bookmark-list">{notebook.bookmarks.map((item) => <li key={item}><button type="button" disabled={busy} onClick={() => requestPage(item)}>Page {item}</button>{bookmarkAnchors.filter(entry => entry.page === item).map(entry => <button key={entry.anchor.offset} type="button" disabled={busy} onClick={() => requestPage(item, entry.anchor.offset, entry.anchor.revision)}>Saved passage {entry.anchor.offset + 1}</button>)}</li>)}</ul> : <p className="reader-v2__notebook-empty">Your saved pages appear here.</p>}<button type="button" onClick={toggleBookmark}>{bookmarked ? "Remove page bookmark" : "Bookmark this page"}</button></>}
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
