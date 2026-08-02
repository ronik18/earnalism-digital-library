import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, BookOpen, CirclePlay, Headphones } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import "./PremiumListeningRail.css";

function listenUrl(book) {
  return book?.cta_url || book?.primary_cta_url || "";
}

function canListen(book) {
  if (book?.audio_available === false || book?.rights_restricted === true) return false;
  const url = listenUrl(book);
  return book?.cta_kind === "listen" || /[?&]listen=1(?:&|$)/.test(url);
}

function realProgress(book) {
  const value = Number(book?.listening_progress_percent ?? book?.progress_percent);
  return Number.isFinite(value) && value > 0 && value < 100 ? Math.round(value) : null;
}

function ListeningCard({ book, featured, onCoverFailure }) {
  const available = canListen(book);
  const progress = realProgress(book);
  const synchronized = book?.highlight_sync_enabled === true;
  const duration = Number(book?.audio_duration_ms);
  const narrator = String(book?.narrator || book?.narrator_name || "").trim();
  const title = book?.title || "Untitled edition";
  const author = book?.author || "";

  return (
    <li
      className={`premium-listening-card${featured ? " premium-listening-card--featured" : ""}`}
      data-book-slug={book.slug}
      data-audio-state={available ? "available" : "unavailable"}
    >
      <div className="premium-listening-card__art">
        <Link
          className="premium-listening-card__cover-link"
          to={book.book_url || `/book/${book.slug}`}
          aria-label={`Open ${title}${author ? ` by ${author}` : ""}`}
        >
          <BookCoverImage
            book={book}
            alt={book.cover_alt_text || `${title}${author ? ` by ${author}` : ""}`}
            width={180}
            height={270}
            widths={[150, 180, 240]}
            sizes="(min-width: 900px) 126px, 96px"
            className="premium-listening-card__cover"
            loading="lazy"
            allowGraphicalFallback={false}
            onPermanentFailure={onCoverFailure}
          />
        </Link>
        <span className="premium-listening-card__waveform" aria-hidden="true" />
      </div>

      <div className="premium-listening-card__copy">
        <div className="premium-listening-card__labels">
          <span>{synchronized ? "Read + Listen" : "Audiobook"}</span>
          {!available && <span className="premium-listening-card__unavailable">Audio unavailable</span>}
        </div>
        <h3>
          <Link to={book.book_url || `/book/${book.slug}`}>{title}</Link>
        </h3>
        {author && <p className="premium-listening-card__author">{author}</p>}
        {(narrator || duration > 0) && (
          <p className="premium-listening-card__meta">
            {narrator ? `Narrated by ${narrator}` : ""}
            {narrator && duration > 0 ? " · " : ""}
            {duration > 0 ? `${Math.round(duration / 60000)} min` : ""}
          </p>
        )}

        {progress !== null && (
          <div className="premium-listening-card__progress" aria-label={`${progress}% listened`}>
            <span style={{ width: `${progress}%` }} />
          </div>
        )}

        {available ? (
          <Link
            className="premium-listening-card__cta"
            to={listenUrl(book)}
            aria-label={`${progress === null ? "Play" : "Continue"} ${title}`}
          >
            <CirclePlay size={18} strokeWidth={1.55} aria-hidden="true" />
            <span>{progress === null ? "Begin listening" : "Continue listening"}</span>
          </Link>
        ) : (
          <Link className="premium-listening-card__cta premium-listening-card__cta--reader" to={book.book_url || `/book/${book.slug}`}>
            <BookOpen size={17} strokeWidth={1.55} aria-hidden="true" />
            <span>View reader edition</span>
          </Link>
        )}
      </div>
    </li>
  );
}

export default function PremiumListeningRail({ books = [], reserveBooks = [], loading = false, error = false }) {
  const [failedSlugs, setFailedSlugs] = useState(() => new Set());
  const [scrollState, setScrollState] = useState({ previous: false, next: false });
  const viewportRef = useRef(null);
  const visibleBooks = useMemo(() => {
    const primary = books.filter((book) => book?.slug && !failedSlugs.has(book.slug));
    const reserve = reserveBooks.filter((book) => (
      book?.slug && !failedSlugs.has(book.slug) && !primary.some((item) => item.slug === book.slug)
    ));
    const targetCount = Math.max(1, books.length || reserveBooks.length);
    return [...primary, ...reserve].slice(0, targetCount);
  }, [books, reserveBooks, failedSlugs]);

  const updateScrollState = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const maxScroll = Math.max(0, viewport.scrollWidth - viewport.clientWidth);
    const nextState = {
      previous: viewport.scrollLeft > 8,
      next: viewport.scrollLeft < maxScroll - 8,
    };
    setScrollState((current) => (
      current.previous === nextState.previous && current.next === nextState.next ? current : nextState
    ));
  }, []);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;
    let frame = 0;
    const schedule = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        updateScrollState();
      });
    };
    schedule();
    viewport.addEventListener("scroll", schedule, { passive: true });
    const resizeObserver = typeof ResizeObserver === "function" ? new ResizeObserver(schedule) : null;
    resizeObserver?.observe(viewport);
    return () => {
      viewport.removeEventListener("scroll", schedule);
      resizeObserver?.disconnect();
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [updateScrollState, visibleBooks.length]);

  const move = (direction) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    viewport.scrollBy({
      left: direction * Math.max(280, viewport.clientWidth * 0.72),
      behavior: reduceMotion ? "auto" : "smooth",
    });
  };

  const onRailKeyDown = (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    move(event.key === "ArrowLeft" ? -1 : 1);
  };

  const status = loading && !visibleBooks.length
    ? "loading"
    : error && !visibleBooks.length
      ? "error"
      : !visibleBooks.length
        ? "empty"
        : "ready";

  return (
    <section
      className="premium-listening-rail selected-listening-rail"
      aria-labelledby="premium-listening-title"
      aria-busy={status === "loading"}
      data-state={status}
      data-testid="premium-listening-rail"
    >
      <div className="premium-listening-rail__inner">
        <div className="premium-listening-rail__heading">
          <div className="premium-listening-rail__intro">
            <div className="premium-listening-rail__eyebrow selected-listening-rail__eyebrow">
              <Headphones size={15} strokeWidth={1.55} aria-hidden="true" />
              THE LISTENING ROOM
            </div>
            <h2 id="premium-listening-title" data-testid="premium-listening-title">Literature, in a more intimate form.</h2>
            <p>Curated performances with seamless read-along listening.</p>
          </div>
          <div className="premium-listening-rail__actions selected-listening-rail__actions">
            {visibleBooks.length > 1 && (
              <div className="premium-listening-rail__controls" aria-label="Audiobook gallery controls">
                <button type="button" className="premium-listening-rail__control selected-listening-rail__control" aria-label="Previous audiobooks" aria-controls="premium-listening-viewport" disabled={!scrollState.previous} onClick={() => move(-1)}>
                  <ArrowLeft size={16} aria-hidden="true" />
                </button>
                <button type="button" className="premium-listening-rail__control selected-listening-rail__control" aria-label="Next audiobooks" aria-controls="premium-listening-viewport" disabled={!scrollState.next} onClick={() => move(1)}>
                  <ArrowRight size={16} aria-hidden="true" />
                </button>
              </div>
            )}
            <Link className="premium-listening-rail__browse selected-listening-rail__browse" to="/library?audio=approved">
              Explore audiobooks <ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" />
            </Link>
          </div>
        </div>

        {status === "ready" ? (
          <div className="premium-listening-rail__viewport selected-listening-rail__viewport" ref={viewportRef} id="premium-listening-viewport" tabIndex="0" onKeyDown={onRailKeyDown} aria-label="Audiobook cards. Use arrow keys, the previous and next buttons, or swipe.">
            <ul className="premium-listening-rail__items selected-listening-rail__items" id="premium-listening-items" aria-label="Curated audiobooks">
              {visibleBooks.map((book, index) => (
                <ListeningCard
                  book={book}
                  featured={index === 0}
                  key={book.slug}
                  onCoverFailure={() => setFailedSlugs((current) => new Set([...current, book.slug]))}
                />
              ))}
            </ul>
          </div>
        ) : status === "loading" ? (
          <div className="premium-listening-rail__skeleton" role="status" aria-label="Loading audiobooks">
            <span /><span /><span />
          </div>
        ) : (
          <div className="premium-listening-rail__status" role="status">
            <Headphones size={20} strokeWidth={1.45} aria-hidden="true" />
            <p>{status === "error" ? "The listening room could not be refreshed." : "More listening editions are being prepared."}</p>
            <Link to="/library">Browse the library</Link>
          </div>
        )}
      </div>
    </section>
  );
}
