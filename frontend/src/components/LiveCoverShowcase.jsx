import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen } from "lucide-react";
import { optimizedImageUrl } from "../lib/images";

function LiveCoverShowcase({ books = [], featured, variant = "panel" }) {
  const marqueeRef = useRef(null);
  const trackRef = useRef(null);
  const rafRef = useRef(0);
  const setWidthRef = useRef(0);
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
  const measureSetWidth = useCallback(() => {
    const marquee = marqueeRef.current;
    if (!marquee || liveBooks.length === 0) return 0;
    const oneSetWidth = marquee.scrollWidth / 3;
    setWidthRef.current = oneSetWidth;
    return oneSetWidth;
  }, [liveBooks.length]);

  const resetToMiddleIfNeeded = useCallback((adjustDragAnchor = false) => {
    const marquee = marqueeRef.current;
    const oneSetWidth = setWidthRef.current || measureSetWidth();
    if (!marquee || !oneSetWidth) return;

    let nextScrollLeft = marquee.scrollLeft;
    let anchorAdjustment = 0;

    while (nextScrollLeft >= oneSetWidth * 2) {
      nextScrollLeft -= oneSetWidth;
      anchorAdjustment -= oneSetWidth;
    }

    while (nextScrollLeft <= 0) {
      nextScrollLeft += oneSetWidth;
      anchorAdjustment += oneSetWidth;
    }

    if (nextScrollLeft !== marquee.scrollLeft) {
      marquee.scrollLeft = nextScrollLeft;
      if (adjustDragAnchor) {
        dragStartScrollRef.current += anchorAdjustment;
      }
    }
  }, [measureSetWidth]);

  useLayoutEffect(() => {
    const marquee = marqueeRef.current;
    if (!marquee || liveBooks.length === 0) return undefined;

    let frame = 0;
    const centerRail = () => {
      const oneSetWidth = measureSetWidth();
      if (oneSetWidth) {
        marquee.scrollLeft = oneSetWidth;
      }
    };

    frame = window.requestAnimationFrame(centerRail);
    const observer = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(centerRail)
      : null;
    if (observer) {
      observer.observe(marquee);
      if (trackRef.current) observer.observe(trackRef.current);
    }
    window.addEventListener("resize", centerRail);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", centerRail);
      if (observer) observer.disconnect();
    };
  }, [liveBooks.length, measureSetWidth]);

  useEffect(() => {
    const marquee = marqueeRef.current;
    if (!marquee || liveBooks.length === 0) return undefined;

    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    let lastTimestamp = 0;

    const animate = (timestamp) => {
      if (!lastTimestamp) lastTimestamp = timestamp;
      const elapsed = timestamp - lastTimestamp;
      lastTimestamp = timestamp;

      if (!prefersReducedMotion && !isPaused && !draggingRef.current) {
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
  }, [isPaused, liveBooks.length, resetToMiddleIfNeeded]);

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
        <span>{liveBooks.length} reading rooms open</span>
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
            const cover = book.cover_image_url || book.cover_url || book.thumbnail_url;
            const copyIndex = Math.floor(index / liveBooks.length);
            const isInteractiveCopy = copyIndex === 1;
            return (
              <article
                key={`${book.slug}-${index}`}
                className="live-cover-card"
                aria-hidden={isInteractiveCopy ? undefined : "true"}
                data-testid={isInteractiveCopy ? `live-cover-card-${book.slug}` : undefined}
              >
                <Link
                  to={`/reader/${book.slug}`}
                  tabIndex={isInteractiveCopy ? 0 : -1}
                  className="live-cover-card__link"
                  aria-label={`Read preview of ${book.title}`}
                  data-testid={isInteractiveCopy ? `live-cover-preview-${book.slug}` : undefined}
                  draggable="false"
                >
                  <span className="live-cover-card__cover">
                    <img
                      src={optimizedImageUrl(cover, { width: 420, quality: 88 })}
                      alt={book.title}
                      loading={index < 4 ? "eager" : "lazy"}
                      decoding="async"
                      draggable="false"
                    />
                    <span className="live-cover-card__preview">
                      <BookOpen size={13} strokeWidth={1.6} /> Preview
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

      <div className="live-cover-showcase__cta">
        <Link to="/library" className="live-cover-showcase__library" data-testid="live-cover-library">
          All books <ArrowRight size={13} strokeWidth={1.6} />
        </Link>
      </div>
    </aside>
  );
}

export default memo(LiveCoverShowcase);
