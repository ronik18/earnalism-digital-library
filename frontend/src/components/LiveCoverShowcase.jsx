import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";
import BookCoverImage from "./BookCoverImage";
import { LIVE_APPROVED_SLUG } from "../lib/controlledLaunch";

function LiveCoverShowcase({ books = [], featured, variant = "panel", totalBooks = 0 }) {
  const marqueeRef = useRef(null);
  const trackRef = useRef(null);
  const rafRef = useRef(0);
  const setWidthRef = useRef(0);
  const itemCountRef = useRef(0);
  const activeCountRef = useRef(0);
  const initializedRef = useRef(false);
  const pausedRef = useRef(false);
  const hoverRef = useRef(false);
  const draggingRef = useRef(false);
  const hasDraggedRef = useRef(false);
  const suppressClickRef = useRef(false);
  const dragStartXRef = useRef(0);
  const dragStartScrollRef = useRef(0);
  const pointerIdRef = useRef(null);
  const pointerCapturedRef = useRef(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const liveBooks = useMemo(() => {
    const seen = new Set();
    const candidates = [...books, featured].filter(Boolean).map((book) => ({
      ...book,
      slug: book.slug || book.id,
    }));
    return candidates
      .filter((book) => {
        const slug = book.slug;
        const cover = book.cover_image_url || book.cover_url || book.thumbnail_url;
        if (!slug || !cover || seen.has(slug)) return false;
        seen.add(slug);
        return true;
      });
  }, [books, featured]);

  const marqueeBooks = useMemo(
    () => (liveBooks.length > 0 ? [...liveBooks, ...liveBooks, ...liveBooks] : []),
    [liveBooks],
  );
  activeCountRef.current = liveBooks.length;
  const hasLiveBooks = liveBooks.length > 0;
  const visibleTotal = liveBooks.filter((book) => book.slug === LIVE_APPROVED_SLUG).length || liveBooks.length;

  useEffect(() => {
    pausedRef.current = isPaused;
  }, [isPaused]);

  const getSetWidth = useCallback(() => {
    const track = trackRef.current;
    if (!track || activeCountRef.current === 0) return 0;
    return track.scrollWidth / 3;
  }, []);

  const offsetWithinSet = useCallback((scrollLeft, oneSetWidth) => {
    if (!oneSetWidth) return 0;
    const offset = scrollLeft % oneSetWidth;
    return offset < 0 ? offset + oneSetWidth : offset;
  }, []);

  const normalizeToMiddleSet = useCallback((scrollLeft, oneSetWidth) => {
    if (!oneSetWidth) return scrollLeft;
    let nextScrollLeft = scrollLeft;

    while (nextScrollLeft >= oneSetWidth * 2) {
      nextScrollLeft -= oneSetWidth;
    }

    while (nextScrollLeft < oneSetWidth) {
      nextScrollLeft += oneSetWidth;
    }

    return nextScrollLeft;
  }, []);

  const syncRailPosition = useCallback(() => {
    const marquee = marqueeRef.current;
    const nextSetWidth = getSetWidth();
    const nextCount = activeCountRef.current;
    if (!marquee || !nextSetWidth || nextCount === 0) return;

    const previousSetWidth = setWidthRef.current;
    const previousCount = itemCountRef.current;

    if (!initializedRef.current || !previousSetWidth || previousCount === 0) {
      marquee.scrollLeft = nextSetWidth;
      initializedRef.current = true;
    } else {
      const previousOffset = offsetWithinSet(marquee.scrollLeft, previousSetWidth);
      const preserveRatio = previousCount === nextCount && previousSetWidth !== nextSetWidth;
      const nextOffset = preserveRatio
        ? previousOffset * (nextSetWidth / previousSetWidth)
        : previousOffset;
      marquee.scrollLeft = normalizeToMiddleSet(nextSetWidth + Math.min(nextOffset, nextSetWidth - 1), nextSetWidth);
    }

    setWidthRef.current = nextSetWidth;
    itemCountRef.current = nextCount;
  }, [getSetWidth, normalizeToMiddleSet, offsetWithinSet]);

  const resetToMiddleIfNeeded = useCallback((adjustDragAnchor = false) => {
    const marquee = marqueeRef.current;
    const oneSetWidth = setWidthRef.current || getSetWidth();
    if (!marquee || !oneSetWidth) return;

    const nextScrollLeft = normalizeToMiddleSet(marquee.scrollLeft, oneSetWidth);
    let anchorAdjustment = 0;

    anchorAdjustment = nextScrollLeft - marquee.scrollLeft;

    if (nextScrollLeft !== marquee.scrollLeft) {
      marquee.scrollLeft = nextScrollLeft;
      if (adjustDragAnchor) {
        dragStartScrollRef.current += anchorAdjustment;
      }
    }
  }, [getSetWidth, normalizeToMiddleSet]);

  useLayoutEffect(() => {
    const marquee = marqueeRef.current;
    if (!marquee || liveBooks.length === 0) {
      initializedRef.current = false;
      setWidthRef.current = 0;
      itemCountRef.current = 0;
      return undefined;
    }

    syncRailPosition();
    const frame = window.requestAnimationFrame(syncRailPosition);
    const observer = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(syncRailPosition)
      : null;
    if (observer) {
      observer.observe(marquee);
      if (trackRef.current) observer.observe(trackRef.current);
    }
    window.addEventListener("resize", syncRailPosition);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", syncRailPosition);
      if (observer) observer.disconnect();
    };
  }, [liveBooks.length, syncRailPosition]);

  useEffect(() => {
    const marquee = marqueeRef.current;
    if (!marquee || !hasLiveBooks) return undefined;

    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    let lastTimestamp = 0;

    const animate = (timestamp) => {
      if (!lastTimestamp) lastTimestamp = timestamp;
      const elapsed = timestamp - lastTimestamp;
      lastTimestamp = timestamp;

      if (!prefersReducedMotion && !pausedRef.current && !draggingRef.current) {
        resetToMiddleIfNeeded();
        marquee.scrollLeft += elapsed / 16;
        resetToMiddleIfNeeded();
      }

      rafRef.current = window.requestAnimationFrame(animate);
    };

    rafRef.current = window.requestAnimationFrame(animate);
    return () => {
      window.cancelAnimationFrame(rafRef.current);
    };
  }, [hasLiveBooks, resetToMiddleIfNeeded]);

  const pauseRail = useCallback(() => setIsPaused(true), []);

  const resumeRail = useCallback(() => {
    if (!hoverRef.current && !draggingRef.current) {
      setIsPaused(false);
    }
  }, []);

  const handlePointerDown = useCallback((event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const marquee = marqueeRef.current;
    if (!marquee) return;

    draggingRef.current = true;
    hasDraggedRef.current = false;
    suppressClickRef.current = false;
    pointerIdRef.current = event.pointerId;
    dragStartXRef.current = event.clientX;
    dragStartScrollRef.current = marquee.scrollLeft;
    setIsDragging(false);
    setIsPaused(true);
  }, []);

  const handlePointerMove = useCallback((event) => {
    const marquee = marqueeRef.current;
    if (!marquee || !draggingRef.current || pointerIdRef.current !== event.pointerId) return;

    const deltaX = event.clientX - dragStartXRef.current;
    if (!hasDraggedRef.current && Math.abs(deltaX) < 6) return;

    event.preventDefault();
    if (!hasDraggedRef.current) {
      hasDraggedRef.current = true;
      marquee.setPointerCapture?.(event.pointerId);
      pointerCapturedRef.current = true;
      setIsDragging(true);
    }
    marquee.scrollLeft = dragStartScrollRef.current - deltaX;
    resetToMiddleIfNeeded(true);
  }, [resetToMiddleIfNeeded]);

  const handlePointerUp = useCallback((event) => {
    const marquee = marqueeRef.current;
    if (marquee && pointerIdRef.current === event.pointerId && pointerCapturedRef.current) {
      marquee.releasePointerCapture?.(event.pointerId);
    }
    suppressClickRef.current = hasDraggedRef.current;
    draggingRef.current = false;
    hasDraggedRef.current = false;
    pointerCapturedRef.current = false;
    pointerIdRef.current = null;
    setIsDragging(false);
    resumeRail();
    window.setTimeout(() => {
      suppressClickRef.current = false;
    }, 0);
  }, [resumeRail]);

  const handleMouseEnter = useCallback(() => {
    hoverRef.current = true;
    pauseRail();
  }, [pauseRail]);

  const handleMouseLeave = useCallback(() => {
    hoverRef.current = false;
    resumeRail();
  }, [resumeRail]);

  const handleWheel = useCallback((event) => {
    const marquee = marqueeRef.current;
    if (!marquee) return;

    const horizontalIntent = Math.abs(event.deltaX) > Math.abs(event.deltaY) || event.shiftKey;
    if (!horizontalIntent) return;

    event.preventDefault();
    marquee.scrollLeft += event.deltaX || event.deltaY;
    resetToMiddleIfNeeded();
  }, [resetToMiddleIfNeeded]);

  const handleDragStart = useCallback((event) => {
    event.preventDefault();
  }, []);

  const handleClickCapture = useCallback((event) => {
    if (!suppressClickRef.current) return;
    event.preventDefault();
    event.stopPropagation();
  }, []);

  if (liveBooks.length === 0) {
    return (
      <div className={`live-cover-showcase live-cover-showcase--${variant} live-cover-showcase--loading`} data-testid="live-cover-showcase-loading" aria-label="Loading live books">
        <div className="live-cover-showcase__rail">
          {[0, 1, 2, 3].map((item) => (
            <span key={item} className="live-cover-skeleton" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <aside
      className={`live-cover-showcase live-cover-showcase--${variant}`}
      data-testid="live-cover-showcase"
      aria-label="Live Earnalism books"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="live-cover-showcase__header">
        <span className="live-cover-showcase__kicker">Live now</span>
        <span>{visibleTotal === 1 ? "1 controlled release open" : `${visibleTotal} controlled releases open`}</span>
      </div>

      <div
        ref={marqueeRef}
        className="live-cover-marquee"
        aria-label="Live book cover slideshow"
        onBlur={resumeRail}
        onFocus={pauseRail}
        onPointerCancel={handlePointerUp}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onClickCapture={handleClickCapture}
        onDragStart={handleDragStart}
        onWheel={handleWheel}
        style={{
          cursor: isDragging ? "grabbing" : "grab",
          overflowX: "hidden",
          touchAction: "pan-y",
          userSelect: isDragging ? "none" : undefined,
        }}
      >
        <div className="live-cover-marquee__edge live-cover-marquee__edge--left" aria-hidden="true" />
        <div
          ref={trackRef}
          className="live-cover-marquee__track"
          style={{ animation: "none", transform: "none" }}
        >
          {marqueeBooks.map((book, index) => {
            const copyIndex = Math.floor(index / liveBooks.length);
            const isInteractiveCopy = copyIndex === 1;
            return (
              <article
                key={`${copyIndex}-${book.slug}`}
                className="live-cover-card"
                aria-hidden={isInteractiveCopy ? undefined : "true"}
                data-testid={isInteractiveCopy ? `live-cover-card-${book.slug}` : undefined}
              >
                <Link
                  to={book.slug === LIVE_APPROVED_SLUG ? `/reader/${book.slug}` : `/book/${LIVE_APPROVED_SLUG}`}
                  tabIndex={isInteractiveCopy ? 0 : -1}
                  className="live-cover-card__link"
                  aria-label={book.slug === LIVE_APPROVED_SLUG ? `Read Chapter 1 of ${book.title}` : `${book.title} is coming soon`}
                  data-testid={isInteractiveCopy ? `live-cover-preview-${book.slug}` : undefined}
                  draggable="false"
                >
                  <span className="live-cover-card__cover">
                    <BookCoverImage
                      book={book}
                      alt={book.title}
                      loading={index < 4 ? "eager" : "lazy"}
                      fetchPriority={index < 4 ? "high" : "auto"}
                      widths={[240, 320, 420]}
                      width={320}
                      quality={84}
                      sizes="10rem"
                      draggable="false"
                    />
                    <span className="live-cover-card__preview">
                      <BookOpen size={13} strokeWidth={1.6} /> {book.slug === LIVE_APPROVED_SLUG ? "Chapter 1" : "Soon"}
                    </span>
                  </span>
                  <span className="live-cover-card__body">
                    <span className="live-cover-card__title">{book.title}</span>
                    {book.author && <span className="live-cover-card__author">{book.author}</span>}
                  </span>
                </Link>
              </article>
            );
          })}
        </div>
        <div className="live-cover-marquee__edge live-cover-marquee__edge--right" aria-hidden="true" />
      </div>
    </aside>
  );
}

export default memo(LiveCoverShowcase);
