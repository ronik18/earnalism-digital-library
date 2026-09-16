import { useEffect, useRef, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, Clock3, Minus, Plus, Settings2 } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import "./reader-v2.css";
import "./reader-v2.mobile.css";
import { PUBLIC_ACCESS_COPY, PUBLIC_PREVIEW_COPY } from "../../lib/publicAccessCopy";
import { loadReaderSettings, READER_SETTINGS_DEFAULTS, saveReaderSettings } from "../../lib/readerSettings";

export const READER_V2_FIXTURE = Object.freeze({
  title: "Dracula",
  author: "Bram Stoker",
  chapterEyebrow: "Chapter 1",
  chapterTitle: "Jonathan Harker’s Journal",
  canonicalPage: 1,
  totalPublicPages: 3,
  totalPages: 4,
  progress: 38,
  readingTime: "1h 42m",
  readingPass: "215 minutes left",
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

const FONT_SIZES = [17, 18, 20, 22];
const LINE_SPACING = { comfortable: 1.74, relaxed: 1.88, airy: 2.02 };
const READING_WIDTH = { narrow: "600px", classic: "680px", wide: "760px" };

export default function ReaderExperienceV2({ model = READER_V2_FIXTURE, access = {}, onRequestPage, onNavigate }) {
  const [settings, setSettings] = useState(() => {
    try { return loadReaderSettings(); } catch { return READER_SETTINGS_DEFAULTS; }
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const headingRef = useRef(null);
  const settingsTriggerRef = useRef(null);
  useEffect(() => {
    try { saveReaderSettings(settings); } catch { /* Reading stays usable when storage is blocked. */ }
  }, [settings]);

  const page = Number(model.canonicalPage) || 1;
  useEffect(() => {
    // This component mounts only after the selected page has been validated.
    // Balance and heartbeat updates must not move a reader's place or focus.
    headingRef.current?.focus({ preventScroll: true });
    headingRef.current?.scrollIntoView?.({ block: "start", behavior: "instant" });
  }, [page]);
  const contents = (model.contents || []).map((item, index) => typeof item === "string"
    ? { page: index + 1, label: item }
    : { page: Number(item.page), label: item.label })
    .filter((item) => Number.isInteger(item.page) && item.page > 0);
  const declaredTotal = Number(model.totalPages);
  const totalPages = Number.isInteger(declaredTotal) && declaredTotal > 0
    ? declaredTotal : Math.max(page, Number(model.totalPublicPages) || 1, ...contents.map((item) => item.page));
  const progress = Math.min(100, Math.max(0, Number(model.progress) || 0));
  const metadata = model.metadata || {};
  const busy = Boolean(access.busy);
  const atEnd = page >= totalPages;
  const nextLabel = page === 3 && !access.authorized ? "Use Reading Time to Continue" : "Next page";
  const updateSetting = (name, value) => setSettings((previous) => ({ ...previous, [name]: value }));
  const toggleSettings = (event) => {
    settingsTriggerRef.current = event.currentTarget;
    setSettingsOpen((open) => !open);
  };
  const closeSettings = () => {
    setSettingsOpen(false);
    settingsTriggerRef.current?.focus({ preventScroll: true });
  };
  const resizeText = (step) => setSettings((previous) => ({
    ...previous, fontSizeIdx: Math.max(0, Math.min(FONT_SIZES.length - 1, previous.fontSizeIdx + step)),
  }));
  const requestPage = (requestedPage) => {
    const target = Number(requestedPage);
    if (busy || !Number.isInteger(target) || target < 1 || target > totalPages || target === page) return;
    // Navigation requests never grant access. The route authorizes protected
    // pages before it fetches or displays their contents.
    onRequestPage?.(target);
  };

  return (
    <ExperienceShell className="reader-v2" labelledBy="reader-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} onNavigate={onNavigate} trailingLabel="Library" />
      <header className="reader-v2__mobile-topbar" aria-label="Reader actions">
        <button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button>
        <span><small>Page</small>{page} of {totalPages}</span>
        <div>
          <button type="button" onClick={() => resizeText(-1)} disabled={settings.fontSizeIdx === 0} aria-label="Decrease text size">A−</button>
          <button type="button" onClick={() => resizeText(1)} disabled={settings.fontSizeIdx === FONT_SIZES.length - 1} aria-label="Increase text size">A+</button>
          <button type="button" onClick={toggleSettings} aria-label="Reader settings" aria-expanded={settingsOpen} aria-controls="reader-v2-settings"><Settings2 size={17} /></button>
        </div>
      </header>
      <div className="reader-v2__layout">
        <aside className="reader-v2__rail" aria-label="Reader controls">
          <div className="reader-v2__book"><span>{model.author}</span><h2>{model.title}</h2></div>
          <div className="reader-v2__metric"><span>Reading Progress</span><strong>{progress}%</strong><i><b style={{ width: `${progress}%` }} /></i></div>
          {model.readingTime && <div className="reader-v2__metric"><span>Estimated time left</span><strong>{model.readingTime}</strong></div>}
          <ExperiencePanel eyebrow="Contents" className="reader-v2__contents"><ol>{contents.filter((item) => item.page <= totalPages).map((item) => <li key={item.page}><button type="button" aria-current={item.page === page ? "page" : undefined} disabled={busy} onClick={() => requestPage(item.page)}>{item.label}</button></li>)}</ol></ExperiencePanel>
          <ExperiencePanel eyebrow="Reading Pass"><p>{model.readingPass}</p><button type="button" onClick={() => onNavigate?.("passes")}>Extend Reading Time</button></ExperiencePanel>
        </aside>

        <article className="reader-v2__canvas" data-reader-theme={settings.theme} aria-busy={busy} lang={model.language || undefined}>
          <header className="reader-v2__chapter">
            <span>{model.chapterEyebrow}</span>
            <div className="reader-v2__toolbar">
              <ExperienceIconButton label="Decrease text size" disabled={settings.fontSizeIdx === 0} onClick={() => resizeText(-1)}><Minus size={16} /></ExperienceIconButton>
              <output aria-label="Text size">Aa · {FONT_SIZES[settings.fontSizeIdx]}px</output>
              <ExperienceIconButton label="Increase text size" disabled={settings.fontSizeIdx === FONT_SIZES.length - 1} onClick={() => resizeText(1)}><Plus size={16} /></ExperienceIconButton>
              <ExperienceIconButton label="Reader settings" pressed={settingsOpen} onClick={toggleSettings}><Settings2 size={16} /></ExperienceIconButton>
            </div>
            <h1 id="reader-v2-title" ref={headingRef} tabIndex={-1}>{model.chapterTitle}</h1>
          </header>
          {settingsOpen && <section id="reader-v2-settings" className="reader-v2__settings" aria-label="Reading preferences">
            <h2>Reading preferences</h2>
            <label>Theme<select value={settings.theme} onChange={(event) => updateSetting("theme", event.target.value)}><option value="beige">Light</option><option value="sepia">Sepia</option><option value="dark">Night</option></select></label>
            <label>Text size<select value={settings.fontSizeIdx} onChange={(event) => updateSetting("fontSizeIdx", Number(event.target.value))}>{FONT_SIZES.map((size, index) => <option key={size} value={index}>{size}px</option>)}</select></label>
            <label>Line spacing<select value={settings.lineSpacingMode} onChange={(event) => updateSetting("lineSpacingMode", event.target.value)}><option value="comfortable">Comfortable</option><option value="relaxed">Relaxed</option><option value="airy">Airy</option></select></label>
            <label>Font<select value={settings.fontFamilyMode} onChange={(event) => updateSetting("fontFamilyMode", event.target.value)}><option value="sans">Clear sans serif</option><option value="serif">Literary serif</option></select></label>
            <button type="button" onClick={closeSettings}>Close preferences</button>
          </section>}
          <label className="reader-v2__page-selector">Go to page<select aria-label="Go to page" value={page} disabled={busy} onChange={(event) => requestPage(event.target.value)}>{Array.from({ length: totalPages }, (_, index) => <option key={index + 1} value={index + 1}>Page {index + 1}</option>)}</select></label>
          {model.illustration?.src && <img className="reader-v2__illustration" src={model.illustration.src} alt={model.illustration.alt || ""} decoding="async" />}
          <div className="reader-v2__body" data-testid="reader-reading-text" style={{ fontSize: `${FONT_SIZES[settings.fontSizeIdx]}px`, lineHeight: LINE_SPACING[settings.lineSpacingMode], maxWidth: READING_WIDTH[settings.marginMode], fontFamily: settings.fontFamilyMode === "sans" ? '"Noto Sans Bengali", var(--ev2-ui)' : '"Noto Serif Bengali", var(--ev2-content)' }}>
            {model.content ?? (model.paragraphs || []).map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 16)}`}>{paragraph}</p>)}
          </div>
          {model.statusMessage && <p className="reader-v2__status" role="status">{model.statusMessage}</p>}
          <footer className="reader-v2__continuation">
            <span>{atEnd ? "You have reached the end of this book." : page <= 3 ? PUBLIC_PREVIEW_COPY : `Page ${page} of ${totalPages}`}</span>
            <nav aria-label="Page navigation">
              <button type="button" disabled={busy || page <= 1} onClick={() => requestPage(page - 1)}><ChevronLeft size={16} /> Previous page</button>
              <button type="button" disabled={busy || atEnd} onClick={() => requestPage(page + 1)}>{atEnd ? "End of book" : nextLabel} <ChevronRight size={16} /></button>
            </nav>
          </footer>
        </article>

        <aside className="reader-v2__context" aria-label="About this book"><ExperiencePanel eyebrow="About this book"><dl>{model.author && <div><dt>Author</dt><dd>{model.author}</dd></div>}{metadata.language && <div><dt>Language</dt><dd>{metadata.language}</dd></div>}{metadata.genre && <div><dt>Genre</dt><dd>{metadata.genre}</dd></div>}{metadata.year && <div><dt>First published</dt><dd>{metadata.year}</dd></div>}{metadata.source && <div><dt>Edition</dt><dd>{metadata.source}</dd></div>}</dl><p>{PUBLIC_ACCESS_COPY}</p></ExperiencePanel></aside>
      </div>
      <div className="reader-v2__mobile-actions"><button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button><span><Clock3 size={14} /> {model.readingPass}</span><button type="button" onClick={() => onNavigate?.("bookmark")} aria-label="Save current page"><Bookmark size={18} /></button></div>
      <div className="reader-v2__reader-navigation"><ExperienceBottomNavigation active="library" onNavigate={onNavigate} /></div>
    </ExperienceShell>
  );
}
