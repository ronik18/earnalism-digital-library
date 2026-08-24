import { useMemo, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, Clock3, Minus, Plus, Settings2 } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import "./reader-v2.css";

export const READER_V2_FIXTURE = Object.freeze({
  title: "Dracula",
  author: "Bram Stoker",
  chapterEyebrow: "Chapter 1",
  chapterTitle: "Jonathan Harker’s Journal",
  canonicalPage: 1,
  totalPublicPages: 3,
  progress: 38,
  readingTime: "1h 42m",
  readingPass: "215 minutes left",
  contents: ["Chapter 1 · Jonathan Harker’s Journal", "Chapter 2 · The Carpathians", "Chapter 3 · The Count’s Castle", "Chapter 4 · The Visitor’s Diary"],
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

export default function ReaderExperienceV2({ model = READER_V2_FIXTURE, access = {}, onRequestPage, onNavigate }) {
  const [fontScale, setFontScale] = useState(100);
  const currentAccess = useMemo(() => readerPageAccess({ canonicalPage: model.canonicalPage, ...access }), [model.canonicalPage, access]);
  const requestPage = (page) => {
    const nextAccess = readerPageAccess({ canonicalPage: page, ...access });
    if (nextAccess.canRequest) onRequestPage?.(page);
  };

  return (
    <ExperienceShell className="reader-v2" labelledBy="reader-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} trailingLabel="Library" />
      <div className="reader-v2__layout">
        <aside className="reader-v2__rail" aria-label="Reader controls">
          <div className="reader-v2__book"><span>{model.author}</span><h2>{model.title}</h2></div>
          <div className="reader-v2__metric"><span>Reading Progress</span><strong>{model.progress}%</strong><i><b style={{ width: `${model.progress}%` }} /></i></div>
          <div className="reader-v2__metric"><span>Estimated time left</span><strong>{model.readingTime}</strong></div>
          <ExperiencePanel eyebrow="Contents" className="reader-v2__contents"><ol>{model.contents.map((item, index) => <li key={item} aria-current={index === 0 ? "page" : undefined}>{item}</li>)}</ol></ExperiencePanel>
          <ExperiencePanel eyebrow="Reading Pass"><p>{model.readingPass}</p><button type="button" onClick={() => onNavigate?.("passes")}>Extend Reading Time</button></ExperiencePanel>
        </aside>

        <article className="reader-v2__canvas">
          <header className="reader-v2__chapter"><span>{model.chapterEyebrow}</span><div className="reader-v2__toolbar"><ExperienceIconButton label="Decrease text size" onClick={() => setFontScale((value) => Math.max(90, value - 5))}><Minus size={16} /></ExperienceIconButton><output aria-label="Text size">Aa · {fontScale}%</output><ExperienceIconButton label="Increase text size" onClick={() => setFontScale((value) => Math.min(120, value + 5))}><Plus size={16} /></ExperienceIconButton><ExperienceIconButton label="Reader settings" onClick={() => onNavigate?.("settings")}><Settings2 size={16} /></ExperienceIconButton></div><h1 id="reader-v2-title">{model.chapterTitle}</h1></header>
          {model.illustration && <img className="reader-v2__illustration" src={model.illustration.src} alt={model.illustration.alt || ""} decoding="async" />}
          <div className="reader-v2__body" style={{ fontSize: `${fontScale / 100}rem` }}>{model.paragraphs.map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 16)}`}>{paragraph}</p>)}</div>
          <footer className="reader-v2__continuation"><span>First 3 pages are free to preview.</span>{currentAccess.canRequest ? <button type="button" onClick={() => requestPage(model.canonicalPage + 1)}>Use Reading Time to Continue <ChevronRight size={16} /></button> : <button type="button" onClick={() => onNavigate?.("signin")}>Sign in to continue <ChevronRight size={16} /></button>}</footer>
        </article>

        <aside className="reader-v2__context" aria-label="About this book"><ExperiencePanel eyebrow="About this book"><dl><div><dt>Author</dt><dd>{model.author}</dd></div><div><dt>Language</dt><dd>{model.metadata.language}</dd></div><div><dt>Genre</dt><dd>{model.metadata.genre}</dd></div><div><dt>First published</dt><dd>{model.metadata.year}</dd></div><div><dt>Source & rights</dt><dd>{model.metadata.source}</dd></div></dl><p>Preview pages 1–3 are free. Reading time remains server-authoritative.</p></ExperiencePanel></aside>
      </div>
      <div className="reader-v2__mobile-actions"><button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button><span><Clock3 size={14} /> {model.readingPass}</span><button type="button" onClick={() => onNavigate?.("bookmark")} aria-label="Bookmark current page"><Bookmark size={18} /></button></div>
      <ExperienceBottomNavigation active="library" onNavigate={onNavigate} />
    </ExperienceShell>
  );
}
