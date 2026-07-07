import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Headphones, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";

const DEFAULT_SLUG = process.env.REACT_APP_APPROVED_AUDIO_SPOTLIGHT_SLUG || "";

function runAfterIdle(callback) {
  if (typeof window === "undefined") return () => {};
  let timeoutId;
  let idleId;
  if ("requestIdleCallback" in window) {
    idleId = window.requestIdleCallback(callback, { timeout: 2200 });
  } else {
    timeoutId = window.setTimeout(callback, 1200);
  }
  return () => {
    if (idleId && "cancelIdleCallback" in window) window.cancelIdleCallback(idleId);
    if (timeoutId) window.clearTimeout(timeoutId);
  };
}

function bookFromReaderManifest(data = {}) {
  if (!data?.book) return null;
  const book = {
    ...data.book,
    _readerManifest: {
      version: data.version || "",
      audio: data.audio || {},
      access: data.access || {},
    },
  };
  if (data.audio?.assets) {
    book.audiobook_assets = {
      ...(book.audiobook_assets || {}),
      ...data.audio.assets,
    };
    book.audiobook_enabled = data.audio.enabled;
  }
  return book;
}

export default function ApprovedAudiobookSpotlight({ slug = DEFAULT_SLUG, compact = false }) {
  const [book, setBook] = useState(null);

  useEffect(() => {
    if (!slug) {
      setBook(null);
      return undefined;
    }
    const controller = new AbortController();
    const cancelIdle = runAfterIdle(() => {
      api.get(`/reader/book/${slug}/manifest`, { signal: controller.signal, skipAuthRedirect: true })
        .then((response) => {
          const nextBook = bookFromReaderManifest(response.data);
          const state = audiobookReleaseState(nextBook || {});
          setBook(state.canShowControls ? nextBook : null);
        })
        .catch(() => setBook(null));
    });
    return () => {
      cancelIdle();
      controller.abort();
    };
  }, [slug]);

  if (!book) return null;

  const audioState = audiobookReleaseState(book);
  if (!audioState.canShowControls) return null;

  return (
    <section
      className={`approved-audio-spotlight ${compact ? "approved-audio-spotlight--compact" : ""}`}
      data-testid="approved-audiobook-spotlight"
      aria-labelledby="approved-audiobook-spotlight-title"
    >
      <div className="approved-audio-spotlight__shell">
        <div className="approved-audio-spotlight__seal" aria-hidden="true">
          <Headphones size={21} strokeWidth={1.55} />
        </div>
        <div className="approved-audio-spotlight__copy">
          <div className="approved-audio-spotlight__eyebrow">
            <ShieldCheck size={14} strokeWidth={1.6} /> Approved listening room
          </div>
          <h2 id="approved-audiobook-spotlight-title">
            Listen where the release gate is already proven.
          </h2>
          <p>
            {book.title} by {book.author} is available with provider-backed audio, measured sync assets, and production reader-manifest approval. Other titles remain reader-only until their evidence passes.
          </p>
        </div>
        <div className="approved-audio-spotlight__actions">
          <Link to={`/reader/${book.slug}?listen=1`} className="btn-primary">
            <Headphones size={15} strokeWidth={1.7} /> Open Audiobook
          </Link>
          <Link to={`/book/${book.slug}`} className="btn-secondary">
            <Sparkles size={15} strokeWidth={1.7} /> View Edition
          </Link>
        </div>
      </div>
    </section>
  );
}
