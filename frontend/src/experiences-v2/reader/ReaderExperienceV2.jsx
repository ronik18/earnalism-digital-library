import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, List, Maximize, Minimize, Plus, StickyNote } from "lucide-react";
import ExperienceShell from "../shared/ExperienceShell";
import "./reader-v2.css";
import "./reader-pagination.css";
import ReaderOpening from "./ReaderOpening";
import useAuthorizedBookMap from "./useAuthorizedBookMap";
import { ReaderContent, ReaderContentLayout, copyReaderSelection, inlineEmphasis, readerIndexBoundary } from "./readerContent";
import useVisualPagination from "./useVisualPagination";
import { pageForAnchor } from "./visualPagination";
import "./reader-v2.mobile.css";
import "./reader-quiet-folio.css";
import ReaderDialog from "./ReaderDialog";
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
  // Halve extra leading while retaining language-appropriate readable spacing.
  comfortable: { en: 1.375, bn: 1.4 },
  relaxed: { en: 1.44, bn: 1.465 },
  airy: { en: 1.51, bn: 1.54 },
};
const LANGUAGE_TYPOGRAPHY = {
  en: { size: 1.25, fontFamily: '"EB Garamond", Georgia, serif', fontWeight: 400 },
  bn: { size: 1.25, fontFamily: '"Noto Serif Bengali", serif', fontWeight: 500 },
};

function readerLanguage(language) {
  return language === "bn" ? "bn" : "en";
}

function formatRem(value) {
  return `${Number(value).toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}rem`;
}

export default function ReaderExperienceV2({ model = READER_V2_FIXTURE, access = {}, onRequestPage, onNavigate }) {
  const [settings, setSettings] = useState(() => {
    try { return loadReaderSettings(); } catch { return READER_SETTINGS_DEFAULTS; }
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [contentsOpen, setContentsOpen] = useState(false);
  const [libraryQuery, setLibraryQuery] = useState("");
  const [creditsOpen, setCreditsOpen] = useState(false);
  const folioRef = useRef(null);
  const fullscreenTriggerRef = useRef(null);
  const showControlsRef = useRef(null);
  const focusWasEnabled = useRef(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenPending, setFullscreenPending] = useState(false);
  const [fullscreenNotice, setFullscreenNotice] = useState("");
  const nativeFullscreenEntered = useRef(false);
  useEffect(() => {
    const syncFullscreen = () => {
      const entered = document.fullscreenElement === folioRef.current;
      setFullscreen(entered);
      if (entered) {
        nativeFullscreenEntered.current = true;
        setSettings(previous => ({ ...previous, focusMode: true }));
      } else if (nativeFullscreenEntered.current) {
        nativeFullscreenEntered.current = false;
        setSettings(previous => ({ ...previous, focusMode: false }));
      }
    };
    document.addEventListener('fullscreenchange', syncFullscreen);
    return () => document.removeEventListener('fullscreenchange', syncFullscreen);
  }, []);
  const notebookKey = readerNotebookKey(model.slug || model.title, model.notebookOwner || "guest");
  const [savedNotebook, setSavedNotebook] = useState(() => ({ key: notebookKey, value: loadReaderNotebook(notebookKey) }));
  const notebook = savedNotebook.key === notebookKey ? savedNotebook.value : loadReaderNotebook(notebookKey);
  const [notebookOpen, setNotebookOpen] = useState(false);
  const overlayOpen = settingsOpen || contentsOpen || creditsOpen || notebookOpen;
  useLayoutEffect(() => {
    if (settings.focusMode && !focusWasEnabled.current) showControlsRef.current?.focus({ preventScroll: true });
    else if (!settings.focusMode && focusWasEnabled.current) fullscreenTriggerRef.current?.focus({ preventScroll: true });
    focusWasEnabled.current = settings.focusMode;
  }, [settings.focusMode]);
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
    : { page: Number(item.page), label: item.label, chapterId: item.chapterId })
    .filter((item) => Number.isInteger(item.page) && item.page > 0);
  const declaredTotal = Number(model.totalPages);
  const totalPages = Number.isInteger(declaredTotal) && declaredTotal > 0
    ? declaredTotal : Math.max(page, Number(model.totalPublicPages) || 1, ...contents.map((item) => item.page));
  const metadata = model.metadata || {};
  const language = readerLanguage(model.language);
  const languageTypography = LANGUAGE_TYPOGRAPHY[language];
  const textSizeRem = settings.readerTextSizeRem ?? languageTypography.size;
  const lineHeight = LINE_SPACING[settings.lineSpacingMode]?.[language] || LINE_SPACING.comfortable[language];
  const fontMode = settings.readerFontFamilyPreference || "serif";
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
    pageBreaks: model.pageBreaks,
    revision: model.sourceRevision || `${page}:${model.chapterTitle}`,
    typography: `${textSizeRem}:${lineHeight}:${fontFamily}:${fontWeight}` });
  const visualIndex = anchor === 'end' ? Math.max(0, pagination.pages.length - 1) : pageForAnchor(pagination.pages, anchor);
  const fragment = pagination.pages[visualIndex];
  const publicVisualPreview = !access.authorized && model.visualFixture !== true;
  const previewBlocked = publicVisualPreview && visualIndex >= 3;
  const visualTotal = pagination.pages.length;
  const bookMap = useAuthorizedBookMap({ model, pagination, visualIndex, viewportRef,
    typography: `${textSizeRem}:${lineHeight}:${fontFamily}:${fontWeight}` });
  const pageIndicator = previewBlocked ? "Preview limit reached" : publicVisualPreview
    ? `${visualIndex + 1} of ${Math.min(3, visualTotal) || '…'} in free preview`
    : bookMap.complete && model.visualPageScope !== "chapter" ? `${bookMap.currentNumber || visualIndex + 1} of ${bookMap.total}`
    : `${visualIndex + 1} of ${visualTotal || '…'} in this chapter`;
  const sourceAnchor = model.sourceAnchorForOffset?.(fragment?.anchor ?? fragment?.start ?? 0);
  const indexBoundary = useMemo(() => readerIndexBoundary(model.authorizedChapter?.html || ''), [model.authorizedChapter?.html]);
  const referenceSection = indexBoundary && fragment && fragment.end > indexBoundary.offset ? indexBoundary : null;
  const indexAnchor = indexBoundary && model.sourceAnchorForOffset?.(indexBoundary.offset);
  const activeChapterId = model.authorizedChapter?.plan.chapterId;
  const selectedChapter = activeChapterId
    ? contents.find(item => item.chapterId === activeChapterId)
    : [...contents].reverse().find(item => item.page <= (sourceAnchor?.page || page));

  const pageOptions = publicVisualPreview ? bookMap.options.slice(0, 3) : bookMap.options;
  const selectablePages = publicVisualPreview ? pagination.pages.slice(0, 3) : pagination.pages;
  const mapSelection = pageOptions.find(option => option.chapterId === model.authorizedChapter?.plan.chapterId && option.anchor.page === sourceAnchor?.page && option.anchor.offset === sourceAnchor?.offset && option.anchor.revision === sourceAnchor?.revision)?.key || '';
  const onVisualAnchor = model.onVisualAnchor;
  const requestProtectedContent = model.onRequestProtectedContent;
  const sourceAnchorForOffset = model.sourceAnchorForOffset;
  const previewLayout = JSON.stringify([pagination.width, pagination.height, textSizeRem, lineHeight, fontFamily, fontWeight]);
  const fourthPreviewPage = publicVisualPreview ? pagination.pages[3] : null;
  const publicPreviewEnd = useMemo(() => fourthPreviewPage && sourceAnchorForOffset ? {
    ...sourceAnchorForOffset(fourthPreviewPage.anchor ?? fourthPreviewPage.start),
    layout: previewLayout, revisionOfBook: model.previewContentRevision || '',
  } : null, [fourthPreviewPage, sourceAnchorForOffset, previewLayout, model.previewContentRevision]);
  const retainedPreviewEnd = model.publicPreviewEnd;
  const measuredPreviewMatches = retainedPreviewEnd?.layout === previewLayout
    && retainedPreviewEnd?.revisionOfBook === (model.previewContentRevision || '');
  const numericPreviewEnd = Number.isFinite(retainedPreviewEnd?.offset) && Number.isFinite(sourceAnchor?.offset);
  const withinMeasuredPreview = measuredPreviewMatches && sourceAnchor && (
    sourceAnchor.page < retainedPreviewEnd.page || (sourceAnchor.page === retainedPreviewEnd.page
      && numericPreviewEnd && sourceAnchor.offset < retainedPreviewEnd.offset));
  // This only classifies billable activity under an already verified lease.
  // Missing/stale layout evidence never charges an ambiguous public prefix.
  const ordinaryPublicSource = !model.protectedTextContinuation && (sourceAnchor?.page || page) <= (model.previewLimit || 3);
  const unmeasuredPublicPrefix = model.protectedTextContinuation && !measuredPreviewMatches
    && (model.windowFirst || page) !== 1 && (sourceAnchor?.page || page) <= (model.previewLimit || 3);
  const publicPreviewVisible = ordinaryPublicSource || unmeasuredPublicPrefix || withinMeasuredPreview
    || ((model.windowFirst || page) === 1 && visualIndex < 3);
  const changeAnchor = useCallback((offset) => {
    const index = offset === 'end' ? pagination.pages.length - 1 : pageForAnchor(pagination.pages, offset);
    if (publicVisualPreview && index >= 3) {
      const target = sourceAnchorForOffset?.(offset) || { page, offset };
      requestProtectedContent?.(target.page, target.offset, target.revision, publicPreviewEnd);
      return;
    }
    setLocalAnchor(offset);
    onVisualAnchor?.(offset);
  }, [onVisualAnchor, pagination.pages, publicVisualPreview, sourceAnchorForOffset, requestProtectedContent, page, publicPreviewEnd]);
  const readingAnchor = sourceAnchor ? { offset: sourceAnchor.offset, revision: sourceAnchor.revision } : { offset: fragment?.anchor ?? fragment?.start ?? 0, revision: model.sourceRevision || '' };
  const anchorPage = sourceAnchor?.page || page;
  const windowFirst = model.windowFirst ?? navigationPage;
  const windowLast = model.windowLast ?? navigationPage;
  const hasPaginated = useRef(false);
  const openingHasFocus = useRef(false);
  const [failedLayout, setFailedLayout] = useState('');
  const refitLayout = pagination.refit;
  const layoutKey = `${pagination.signature}:${fragment?.anchor ?? fragment?.start}`;
  const layoutError = model.sourceAnchorError || (failedLayout === layoutKey ? 'This page could not be fitted safely. Change the text setting or viewport to retry.' : pagination.error);
  useLayoutEffect(() => {
    if (pagination.pending) {
      setFailedLayout('');
      viewportRef.current?.removeAttribute('data-pagination-overflow');
      return;
    }
    if (!fragment || !viewportRef.current) return;
    hasPaginated.current = true;
    if (openingHasFocus.current) { headingRef.current?.focus(); openingHasFocus.current = false; }
    if (viewportRef.current.scrollHeight > viewportRef.current.clientHeight + 1) {
      // Reject a mismatched rendered result before paint; never reveal clipped prose.
      viewportRef.current.setAttribute('data-pagination-overflow', 'true');
      if (!refitLayout?.(viewportRef.current.scrollHeight - viewportRef.current.clientHeight)) setFailedLayout(layoutKey);
    } else viewportRef.current.removeAttribute('data-pagination-overflow');
  }, [fragment, pagination.pending, refitLayout, layoutKey]);
  const onVisualPageVisibility = model.onVisualPageVisibility;
  const onPreparationFailure = model.onPreparationFailure;
  useEffect(() => { if (layoutError) onPreparationFailure?.(); }, [layoutError, onPreparationFailure]);
  useLayoutEffect(() => {
    onVisualPageVisibility?.(!overlayOpen && !pagination.pending && fragment && !layoutError && !previewBlocked ? { start: fragment.start, end: fragment.end, media: fragment.media || [], publicPreview: publicPreviewVisible } : null);
    return () => onVisualPageVisibility?.(null);
  }, [fragment, pagination.pending, layoutError, previewBlocked, onVisualPageVisibility, publicPreviewVisible, overlayOpen]);
  const busy = Boolean(access.busy);
  const matchesCurrentAnchor = (item) => {
    if (typeof item.anchor.offset === 'string') return item.anchor.revision === readingAnchor.revision && (fragment?.structures?.includes(item.anchor.offset) || (item.anchor.offset.startsWith('media:') && fragment?.media?.includes(Number(item.anchor.offset.split(':')[1]))));
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
  const closeNotebook = () => setNotebookOpen(false);
  const atEnd = !previewBlocked && !pagination.pending && Boolean(fragment) && windowLast >= totalPages && visualIndex >= visualTotal - 1;
  const nextLabel = !access.authorized && ((publicVisualPreview && visualIndex >= 2) || (windowLast === (model.previewLimit || 3) && visualIndex === visualTotal - 1))
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
  };
  const enterFocus = () => {
    setSettings(previous => ({ ...previous, focusMode: true }));
    setSettingsOpen(false);
  };
  const showControls = useCallback(async () => {
    if (document.fullscreenElement === folioRef.current && document.exitFullscreen) {
      try { await document.exitFullscreen(); } catch { setFullscreenNotice("Use your browser’s fullscreen control to exit fullscreen."); return; }
    }
    setSettings(previous => ({ ...previous, focusMode: false }));
    setFullscreenNotice("");
  }, []);
  const toggleFullscreen = async () => {
    if (fullscreenPending) return;
    if (document.fullscreenElement === folioRef.current) { await showControls(); return; }
    setFullscreenNotice("");
    if (!folioRef.current?.requestFullscreen) {
      setSettings(previous => ({ ...previous, focusMode: true }));
      setFullscreenNotice("Fullscreen is unavailable in this browser. Focus reading is on; Show reader controls restores navigation.");
      return;
    }
    setFullscreenPending(true);
    try {
      await folioRef.current.requestFullscreen();
      // fullscreenchange is the authority. A resolved request alone does not
      // claim native fullscreen or change the reading geometry.
    } catch {
      setSettings(previous => ({ ...previous, focusMode: true }));
      setFullscreenNotice("Fullscreen was not opened. Focus reading is on; Show reader controls restores navigation.");
    } finally { setFullscreenPending(false); }
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
    // A larger font can move a retained free-preview anchor beyond its three
    // visual pages. Back must return to the last free page, not ask to buy
    // access to another still-blocked page on the way back.
    const next = publicVisualPreview && direction < 0 && visualIndex >= 3 ? 2 : visualIndex + direction;
    if (next >= 0 && next < visualTotal) changeAnchor(pagination.pages[next].anchor ?? pagination.pages[next].start);
    else requestPage(direction < 0 ? (previousWindow ?? windowFirst - 1) : (nextWindow ?? windowLast + 1), direction < 0 ? 'end' : 0);
  }, [busy, pagination, visualIndex, visualTotal, publicVisualPreview, changeAnchor, requestPage, layoutError, previousWindow, nextWindow, windowFirst, windowLast]);
  const [pageTurn, setPageTurn] = useState({ page, index: visualIndex, direction: "next" });
  if (pageTurn.page !== page || pageTurn.index !== visualIndex) setPageTurn({ page, index: visualIndex, direction: page < pageTurn.page || (page === pageTurn.page && visualIndex < pageTurn.index) ? "previous" : "next" });
  const canvasRef = useRef(null);
  useEffect(() => { canvasRef.current?.scrollTo?.({ top: 0, behavior: "instant" }); }, [page]);
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape' && settings.focusMode && !overlayOpen) { event.preventDefault(); void showControls(); return; }
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || overlayOpen) return;
      const target = event.target;
      const focusControl = settings.focusMode && target === showControlsRef.current;
      if (!focusControl && target instanceof HTMLElement && (target.isContentEditable || target.closest('input, textarea, select, button, a, [role="slider"], [role="combobox"], [role="listbox"], [role="menu"], [role="tablist"], audio, video, [contenteditable="true"]'))) return;
      if (event.key === "ArrowLeft" && (windowFirst > 1 || visualIndex > 0)) { event.preventDefault(); turnVisualPage(-1); }
      if (event.key === "ArrowRight" && !atEnd) { event.preventDefault(); turnVisualPage(1); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [turnVisualPage, navigationPage, visualIndex, atEnd, overlayOpen, windowFirst, settings.focusMode, showControls]);

  const compactPageIndicator = atEnd && access.authorized ? "End of book" : publicVisualPreview
    ? `Preview · ${previewBlocked ? 'limit reached' : `${visualIndex + 1} of ${Math.min(3, visualTotal) || '…'}`}`
    : bookMap.complete && model.visualPageScope !== "chapter"
      ? `${bookMap.currentNumber || visualIndex + 1} of ${bookMap.total}`
      : `${visualIndex + 1} of ${visualTotal || '…'} in this chapter`;
  const meterValue = publicVisualPreview ? Math.min(3, visualIndex + 1) : bookMap.complete ? bookMap.currentNumber : visualIndex + 1;
  const meterMax = publicVisualPreview ? Math.min(3, Math.max(1, visualTotal)) : bookMap.complete ? bookMap.total : Math.max(1, visualTotal);

  return (
    <ReaderContentLayout.Provider value={{ genre: metadata.genre || model.book?.category_slug || "", layout: model.book?.reader_layout || "" }}>
    <ExperienceShell className="reader-v2 reader-quiet-folio" labelledBy="reader-v2-title">
      <div ref={folioRef} className="reader-folio" data-reader-theme={settings.theme} data-focus-mode={settings.focusMode} data-native-fullscreen={fullscreen}>
        <div className="reader-folio__surface" inert={overlayOpen ? true : undefined}>
          <header className="reader-folio__bar" aria-label="Reader actions">
            <button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft aria-hidden="true" /></button>
            <span className="reader-folio__book-title">{model.title}</span>
            <div className="reader-v2__toolbar reader-folio__tools">
              <button type="button" className="reader-folio__aa" onClick={toggleSettings} aria-label="Reader settings" aria-haspopup="dialog" aria-expanded={settingsOpen}>Aa</button>
              <button ref={fullscreenTriggerRef} type="button" onClick={toggleFullscreen} aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"} disabled={fullscreenPending}>{fullscreen ? <Minimize aria-hidden="true" /> : <Maximize aria-hidden="true" />}</button>
            </div>
          </header>
          <div className="reader-v2__layout">
            {pagination.pending && !hasPaginated.current && <div className="reader-v2__pagination-opening"><ReaderOpening embedded book={{ title: model.title, author: model.author }} onLibrary={() => onNavigate?.("library")} onEscapeFocus={focused => { openingHasFocus.current = focused; }} busy={busy} /></div>}
            <div className="reader-v2__page-frame">
              <article ref={canvasRef} className="reader-v2__canvas" data-licensed-text={approvedTextLicense(model.book) ? "true" : undefined} data-reader-theme={settings.theme} data-reader-language={language} aria-busy={busy} lang={model.language || undefined}>
                <header className="reader-v2__chapter"><h1 id="reader-v2-title" ref={headingRef} tabIndex={-1}>{referenceSection?.title || model.chapterTitle}</h1></header>
          {model.pendingPage && <p className="reader-v2__page-loading" role="status">Opening page {model.pendingPage}…</p>}
          <div ref={viewportRef} className="reader-v2__visual-viewport" data-pagination-diagnostic={process.env.NODE_ENV === 'development' ? pagination.errorReason : undefined} data-layout-width={pagination.width} data-layout-height={pagination.height} data-pagination-ready={!pagination.pending && !layoutError} data-transport-chunks={model.transportChunkCount} data-manifest-ms={model.assemblyMetrics?.manifestMs} data-network-ms={model.assemblyMetrics?.networkMs} data-verification-ms={model.assemblyMetrics?.verificationMs} data-fetch-ms={model.assemblyMetrics?.fetchMs} data-assembly-ms={model.assemblyMetrics?.assemblyMs} data-pagination-ms={pagination.durationMs} data-pagination-cached={pagination.cached} data-chapter-id={model.authorizedChapter?.plan.chapterId} data-source-page={sourceAnchor?.page} data-source-offset={sourceAnchor?.offset} data-page-start={fragment?.start} data-page-end={fragment?.end} data-book-page-count={bookMap.total ?? undefined} data-book-map-complete={bookMap.complete} data-page-count={visualTotal} data-visual-page-index={visualIndex}>
            <div ref={sourceRef} className="reader-v2__body reader-v2__pagination-source" aria-hidden="true" inert={true} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }}>
              {model.content ?? (model.paragraphs || []).map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 16)}`}>{inlineEmphasis(paragraph, String(index))}</p>)}
            </div>
            <div ref={bookMap.sourceRef} className="reader-v2__body reader-v2__pagination-source" aria-hidden="true" inert={true} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }}>
              {bookMap.candidate && <ReaderContent html={bookMap.candidate.html} />}
            </div>
            <div ref={bookMap.measureRef} className="reader-v2__body reader-v2__pagination-measure" aria-hidden="true" inert={true} />
            <div ref={measureRef} className="reader-v2__body reader-v2__pagination-measure" aria-hidden="true" inert={true} />
            {pagination.pending ? <p className="reader-v2__pagination-status" role={hasPaginated.current ? "status" : undefined} aria-hidden={!hasPaginated.current}>Preparing this page…</p> : layoutError ? <p role="alert">{layoutError}</p> : previewBlocked ? <section role="alert" data-testid="reader-preview-limit">
                <h2>Your three-page preview has ended</h2>
                <p>{model.freeReading ? "Sign in to continue with this edition’s approved free access." : "A valid Reading Pass is required to continue reading."}</p>
                <button type="button" onClick={() => requestProtectedContent?.(sourceAnchor?.page || page, sourceAnchor?.offset || 0, sourceAnchor?.revision, publicPreviewEnd)} disabled={busy}>{model.freeReading ? "Continue reading free" : "Continue with Reading Pass"}</button>
              </section> :
              <div key={`${page}:${visualIndex}`} className={`reader-v2__page-content reader-v2__page-content--${pageTurn.direction}`} data-testid="reader-page-content">
                <div className="reader-v2__body" data-testid="reader-reading-text" onCopy={copyReaderSelection} data-continuation={fragment?.start > 0} style={{ fontSize: formatRem(textSizeRem), lineHeight, fontFamily, fontWeight }} dangerouslySetInnerHTML={{ __html: fragment?.html || '' }} />
              </div>}
          </div>
          {model.pageError && <p className="reader-v2__status" role={model.pageErrorDenied ? "alert" : "status"}>
            {model.pageError}
            {model.pageErrorRetryable && <button type="button" onClick={() => requestPage(navigationPage)}>Retry page</button>}
          </p>}
          {model.statusMessage && <p className="reader-v2__status" role="status">{model.statusMessage}</p>}


              </article>
            </div>
          </div>
          <footer className="reader-folio__footer">
            <div className="reader-folio__footer-tools">
              <button type="button" className="reader-folio__credits" onClick={() => setCreditsOpen(true)} aria-haspopup="dialog">Edition &amp; credits</button>
              <div>
                <button ref={notebookTriggerRef} type="button" onClick={() => setNotebookOpen(true)} aria-label="Open notes and bookmarks" aria-haspopup="dialog"><StickyNote size={18} aria-hidden="true" /></button>
                <button type="button" onClick={() => { toggleBookmark(); onNavigate?.("bookmark"); }} aria-label="Save current page" aria-pressed={bookmarked}><Bookmark size={18} aria-hidden="true" /></button>
              </div>
            </div>
            <progress className="reader-folio__progress" value={meterValue || 0} max={meterMax} aria-label={publicVisualPreview ? "Preview progress" : bookMap.complete ? "Book progress" : "Chapter progress"} />
            <nav className="reader-folio__navigation" aria-label="Page navigation">
              <button className="reader-v2__page-arrow reader-v2__page-arrow--previous" type="button" aria-label="Previous page" disabled={busy || pagination.pending || (windowFirst <= 1 && visualIndex <= 0)} onClick={() => turnVisualPage(-1)}><ChevronLeft size={24} aria-hidden="true" /></button>
              <span className="reader-folio__page-context" aria-live="polite" aria-atomic="true" title={pageIndicator}>{compactPageIndicator}</span>
              <button type="button" className="reader-folio__contents-trigger" onClick={() => setContentsOpen(true)} aria-haspopup="dialog"><List size={19} aria-hidden="true" /><span>Contents</span></button>
              <button className="reader-v2__page-arrow reader-v2__page-arrow--next" type="button" aria-label="Next page" title={nextLabel} disabled={busy || pagination.pending || atEnd} onClick={() => turnVisualPage(1)}><ChevronRight size={24} aria-hidden="true" /></button>
            </nav>
          </footer>
        </div>
        {settings.focusMode && <button ref={showControlsRef} type="button" className="reader-folio__show-controls" onClick={showControls} aria-label="Show reader controls">Show controls</button>}
        {fullscreenNotice && <p className="reader-folio__fullscreen-notice" role="status">{fullscreenNotice}</p>}
        {contentsOpen && <ReaderDialog id="reader-contents" label="Contents and page navigation" onClose={() => setContentsOpen(false)}>
          <div className="reader-v2__navigation-selectors">
            <label className="reader-v2__compact-contents">Contents
              <select aria-label="Contents" value="" disabled={busy || pagination.pending || !!layoutError} onChange={event => {
                if (busy || pagination.pending || layoutError) return;
                if (event.target.value === "index") { if (indexAnchor) requestPage(indexAnchor.page, indexAnchor.offset, indexAnchor.revision); return; }
                const item = contents.find(item => item.page <= totalPages && `chapter:${item.page}` === event.target.value);
                if (item) requestPage(item.page);
              }}>
                <option value="" disabled>{referenceSection && indexAnchor ? "Current: Index" : selectedChapter ? `Current: ${selectedChapter.label}` : "Choose a chapter"}</option>
                {contents.filter(item => item.page <= totalPages).map(item => <option key={item.page} value={`chapter:${item.page}`}>{item.label}</option>)}
                {indexAnchor && <option value="index">Index</option>}
              </select>
            </label>
          <label className="reader-v2__page-selector">Go to page{pageOptions.length ? <select aria-label="Go to page" value={mapSelection} disabled={busy || pagination.pending} onChange={event => {
            const option = pageOptions.find(item => item.key === event.target.value);
            if (option) requestPage(option.anchor.page, option.anchor.offset, option.anchor.revision);
          }}>{pageOptions.map(option => <option key={option.key} value={option.key}>{option.label}</option>)}</select> : <select aria-label="Go to page" value={previewBlocked ? "" : visualIndex} disabled={busy || pagination.pending} onChange={event => selectablePages[Number(event.target.value)] && changeAnchor(selectablePages[Number(event.target.value)].anchor ?? selectablePages[Number(event.target.value)].start)}>{selectablePages.map((_, index) => <option key={index} value={index}>Page {index + 1}</option>)}</select>}</label>
          </div>

          <ol className="reader-folio__contents-list">{contents.filter(item => item.page <= totalPages).map(item => <li key={item.page}><button type="button" aria-current={!referenceSection && item === selectedChapter ? "page" : undefined} disabled={busy} onClick={() => { requestPage(item.page); setContentsOpen(false); }}>{item.label}</button></li>)}{indexAnchor && <li><button type="button" aria-current={referenceSection ? "page" : undefined} disabled={busy} onClick={() => { requestPage(indexAnchor.page, indexAnchor.offset, indexAnchor.revision); setContentsOpen(false); }}>Index</button></li>}</ol>
          <form className="reader-folio__library-search" onSubmit={event => { event.preventDefault(); onNavigate?.("search", `/library?q=${encodeURIComponent(libraryQuery.trim())}`); }}><label>Search the library<input aria-label="Search books, authors, topics" value={libraryQuery} onChange={event => setLibraryQuery(event.target.value)} /></label><button type="submit">Search library</button></form>
          <button type="button" onClick={() => onNavigate?.("library", "/library")}>Library</button>
        </ReaderDialog>}
        {settingsOpen && <ReaderDialog id="reader-v2-settings" label="Reading preferences" onClose={closeSettings} returnFocus={settingsTriggerRef}>
          <section className="reader-v2__settings">
            <label>Theme<select value={settings.theme} onChange={(event) => updateSetting("theme", event.target.value)}><option value="beige">Light</option><option value="sepia">Sepia</option><option value="dark">Night</option></select></label>
            <label>Text size<select value={textSizeRem} onChange={(event) => updateTextSize(event.target.value)}>{READER_TEXT_SIZE_REM_STEPS.map((size) => <option key={size} value={size}>{formatRem(size)}</option>)}</select></label>
            <label>Line spacing<select value={settings.lineSpacingMode} onChange={(event) => updateSetting("lineSpacingMode", event.target.value)}><option value="comfortable">Comfortable</option><option value="relaxed">Relaxed</option><option value="airy">Airy</option></select></label>
            <label>Font<select value={fontMode} onChange={(event) => updateFontFamily(event.target.value)}><option value="sans">Clear sans serif</option><option value="serif">Literary serif</option></select></label>
            <button type="button" onClick={resetTypography}>Reset typography</button>
            <button type="button" onClick={closeSettings}>Close preferences</button>
            <button type="button" onClick={enterFocus}>Focus reading</button>
          </section>

        </ReaderDialog>}
        {notebookOpen && <ReaderDialog id="reader-notebook" label="Notes and bookmarks" onClose={closeNotebook} returnFocus={notebookTriggerRef}>
          <section className="reader-v2__notebook" aria-label="Your reading notebook">
            <div className="reader-v2__notebook-tabs" role="tablist" aria-label="Notebook views" onKeyDown={event => {
              if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
              event.preventDefault();
              const tab = event.key === 'Home' ? 'notes' : event.key === 'End' ? 'bookmarks' : notebookTab === 'notes' ? 'bookmarks' : 'notes';
              setNotebookTab(tab); event.currentTarget.querySelector(`#reader-${tab}-tab`)?.focus();
            }}>
              <button id="reader-notes-tab" role="tab" type="button" tabIndex={notebookTab === "notes" ? 0 : -1} aria-selected={notebookTab === "notes"} aria-controls="reader-notebook-panel" onClick={() => setNotebookTab("notes")}>Notes</button>
              <button id="reader-bookmarks-tab" role="tab" type="button" tabIndex={notebookTab === "bookmarks" ? 0 : -1} aria-selected={notebookTab === "bookmarks"} aria-controls="reader-notebook-panel" onClick={() => setNotebookTab("bookmarks")}>Bookmarks</button>
            </div>
            <div id="reader-notebook-panel" role="tabpanel" aria-labelledby={`reader-${notebookTab}-tab`}>
              {notebookTab === "notes" ? <>
                {notebook.notes.length ? <ul className="reader-v2__note-list">{notebook.notes.map((note) => <li key={note.id}><button type="button" onClick={() => requestPage(note.page, note.anchor?.offset || 0, note.anchor?.revision)}>Section {note.page}</button><p>{note.text}</p><button type="button" aria-label={`Delete note on page ${note.page}`} onClick={() => updateNotebook({ ...notebook, notes: notebook.notes.filter((item) => item.id !== note.id) })}>Delete note</button></li>)}</ul> : <p className="reader-v2__notebook-empty">Keep a thought from this page.</p>}
                {noteEditorOpen ? <form onSubmit={addNote}><label>Note for page {page}<textarea autoFocus value={noteText} maxLength={2000} onChange={(event) => setNoteText(event.target.value)} /></label><button type="submit" disabled={!noteText.trim()}>Save note</button><button type="button" onClick={() => setNoteEditorOpen(false)}>Cancel</button></form> : <button type="button" className="reader-v2__add-note" disabled={notebook.notes.length >= 100} onClick={() => setNoteEditorOpen(true)}><Plus size={15} /> New note</button>}
              </> : <>{notebook.bookmarks.length ? <ul className="reader-v2__bookmark-list">{notebook.bookmarks.map((item) => <li key={item}><button type="button" disabled={busy} onClick={() => requestPage(item)}>Page {item}</button>{bookmarkAnchors.filter(entry => entry.page === item).map(entry => <button key={`${entry.anchor.revision}:${entry.anchor.offset}`} type="button" disabled={busy} onClick={() => requestPage(item, entry.anchor.offset, entry.anchor.revision)}>Saved passage {typeof entry.anchor.offset === 'string' ? 'illustration' : entry.anchor.offset + 1}</button>)}</li>)}</ul> : <p className="reader-v2__notebook-empty">Your saved pages appear here.</p>}<button type="button" onClick={toggleBookmark}>{bookmarked ? "Remove page bookmark" : "Bookmark this page"}</button></>}
            </div>
            <p className="reader-v2__notebook-storage">Notes and bookmarks stay on this device.</p>
            {notebookNotice && <p role="status">{notebookNotice}</p>}
          </section>

        </ReaderDialog>}
        {creditsOpen && <ReaderDialog id="reader-edition" label="Edition and credits" onClose={() => setCreditsOpen(false)}>
          <h3>{model.title}</h3>
          <dl className="reader-folio__edition">{model.author && <div><dt>Author</dt><dd>{model.author}</dd></div>}{metadata.language && <div><dt>Language</dt><dd>{metadata.language}</dd></div>}{metadata.genre && <div><dt>Genre</dt><dd>{metadata.genre}</dd></div>}{metadata.year && <div><dt>First published</dt><dd>{metadata.year}</dd></div>}{metadata.source && <div><dt>Edition</dt><dd>{metadata.source}</dd></div>}</dl>
          <section aria-label="Reading access"><h3>{model.freeReading ? "Free Reader access" : "Reading Pass"}</h3><p>{model.freeReading ? "Read this complete edition without payment or Reading Pass debit." : model.readingPass}</p>{!model.freeReading && <button type="button" onClick={() => onNavigate?.(model.visualFixture ? "signin" : "passes")}>{model.visualFixture ? "Sign in to check balance" : "Extend Reading Time"}</button>}</section>
          <LicensedTextNotice book={model.book} />
          {model.book && <figure className="reader-v2__front-cover" aria-label="Front cover"><BookCoverImage book={model.book} alt={`${model.title} front cover`} loading="lazy" width={520} widths={[280, 420, 520]} sizes="(min-width: 768px) 24rem, 86vw" allowGraphicalFallback={false} fallback="" /><figcaption>Front cover · {model.title}</figcaption></figure>}
          {atEnd && access.authorized && !layoutError && (model.book?.back_cover_url || model.book?.back_cover_image_url || model.book?.back_cover_thumbnail_url) && <figure className="reader-v2__back-cover" aria-label="Back cover"><BookCoverImage book={model.book} kind="back" alt={`${model.title} back cover`} loading="lazy" width={520} widths={[280, 420, 520]} sizes="(min-width: 768px) 24rem, 86vw" allowGraphicalFallback={false} fallback="" /><figcaption>Back cover · {model.title}</figcaption></figure>}
        </ReaderDialog>}
        <div className="reader-folio__print-license"><LicensedTextNotice book={model.book} /></div>
      </div>
    </ExperienceShell>
    </ReaderContentLayout.Provider>
  );
}
