import { useEffect, useMemo, useState } from "react";
import BookCoverImage from "./BookCoverImage";

export const SHELF_TWO_ITEMS_PER_SLIDE = 5;
export const SHELF_TWO_AUTOPLAY_INTERVAL_MS = 5200;

export function chunkBooks(books, size = SHELF_TWO_ITEMS_PER_SLIDE) {
  const grouped = [];

  for (let i = 0; i < books.length; i += size) {
    grouped.push(books.slice(i, i + size));
  }

  return grouped;
}

export function shouldAutoplayShelfTwo({ slideCount, isPaused, prefersReducedMotion }) {
  return slideCount > 1 && !isPaused && !prefersReducedMotion;
}

function ArrowChevron({ direction }) {
  return (
    <svg
      className="shelf-two-arrow__icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      {direction === "left" ? (
        <path
          d="M15 18L9 12L15 6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M9 18L15 12L9 6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

function prefersReducedMotion() {
  return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
}

export default function ShelfTwoSlideshow({ books = [], autoplayIntervalMs = SHELF_TWO_AUTOPLAY_INTERVAL_MS }) {
  const slides = useMemo(() => chunkBooks(books), [books]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(() => (
    typeof window === "undefined" ? false : prefersReducedMotion()
  ));

  useEffect(() => {
    if (!slides.length) {
      setCurrentSlide(0);
      return;
    }

    if (currentSlide >= slides.length) {
      setCurrentSlide(0);
    }
  }, [slides.length, currentSlide]);

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!media) return undefined;

    const syncReducedMotion = () => setIsReducedMotion(Boolean(media.matches));
    syncReducedMotion();
    media.addEventListener?.("change", syncReducedMotion);
    return () => media.removeEventListener?.("change", syncReducedMotion);
  }, []);

  useEffect(() => {
    if (!shouldAutoplayShelfTwo({ slideCount: slides.length, isPaused, prefersReducedMotion: isReducedMotion })) return undefined;

    const timer = window.setInterval(() => {
      setCurrentSlide((index) => (index === slides.length - 1 ? 0 : index + 1));
    }, autoplayIntervalMs);

    return () => window.clearInterval(timer);
  }, [autoplayIntervalMs, isPaused, isReducedMotion, slides.length]);

  const goToPrevSlide = () => {
    if (!slides.length) return;
    setCurrentSlide((index) => (index === 0 ? slides.length - 1 : index - 1));
  };

  const goToNextSlide = () => {
    if (!slides.length) return;
    setCurrentSlide((index) => (index === slides.length - 1 ? 0 : index + 1));
  };

  const hasMultipleSlides = slides.length > 1;

  return (
    <div
      className="shelf-two-shelf"
      aria-live="polite"
      aria-atomic="true"
      data-testid="shelf-two-slideshow"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
    >
      <div className="shelf-two-viewport">
        <div className="shelf-two-stage-copy" aria-hidden="true">
          <span className="shelf-two-stage-copy__eyebrow">Editorial shelf sequence</span>
          <span className="shelf-two-stage-copy__count">{slides.length} curated page{slides.length === 1 ? "" : "s"}</span>
        </div>
        <div
          className="shelf-two-track"
          data-testid="shelf-two-track"
          style={{ transform: `translateX(-${currentSlide * 100}%)` }}
        >
          {slides.map((slide, slideIndex) => (
            <section
              key={`shelf-two-slide-${slideIndex}`}
              className="shelf-two-slide"
              aria-label={`Shelf 2 page ${slideIndex + 1}`}
              aria-hidden={slideIndex !== currentSlide}
              data-active={slideIndex === currentSlide ? "true" : "false"}
              data-testid="shelf-two-slide"
            >
              <div className="shelf-two-grid">
                {slide.map((book, bookIndex) => {
                  const isPublished = book.status === "published";
                  const statusClass = isPublished ? "published" : "queued";
                  const sequenceLabel = String(book.sequence || (slideIndex * 5) + bookIndex + 1).padStart(2, "0");
                  const statusLabel = book.statusLabel || (statusClass === "published" ? "Live" : "Rights-safe preparation");
                  return (
                    <article
                      key={book.id}
                      className="shelf-two-book"
                      style={{ "--shelf-two-order": bookIndex }}
                    >
                      <div className="shelf-two-book__cover-wrap">
                        <BookCoverImage
                          book={{
                            ...book,
                            cover_image_url: book.coverUrl || book.cover_image_url,
                            thumbnail_url: book.thumbnail_url || book.coverUrl,
                          }}
                          alt={`${book.title} cover`}
                          loading="lazy"
                          width={260}
                          height={390}
                          widths={[220, 260, 360]}
                          sizes="(min-width: 1024px) 17vw, (min-width: 768px) 30vw, 42vw"
                          className="shelf-two-book__cover"
                        />
                        <span className={`shelf-two-book__status-pill shelf-two-book__status-pill--${statusClass}`}>
                          {statusLabel}
                        </span>
                      </div>

                      <div className="shelf-two-book__copy">
                        <div className="shelf-two-book__sequence">Shelf II . {sequenceLabel}</div>
                        <p className="shelf-two-book__title">{book.title}</p>
                        {book.author ? <p className="shelf-two-book__author">{book.author}</p> : null}
                        {book.description ? <p className="shelf-two-book__description">{book.description}</p> : null}
                      </div>

                      <div className="shelf-two-book__footer">
                        {isPublished ? (
                          <a
                            className="shelf-two-book__cta shelf-two-book__cta--published"
                            href={`/book/${book.id || book.slug}`}
                            aria-label={`Start reading ${book.title}`}
                          >
                            Start Reading
                          </a>
                        ) : (
                          <a
                            href={`/contact?interest=${encodeURIComponent(book.id || book.slug || book.title)}`}
                            className="shelf-two-book__cta shelf-two-book__cta--queued"
                            aria-label={`Request an update for ${book.title}`}
                          >
                            Request Update
                          </a>
                        )}
                        <span className={`shelf-two-book__status shelf-two-book__status--${statusClass}`}>
                          {statusClass === "published" ? "Live" : "Coming Soon"}
                        </span>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        {slides[currentSlide]?.[0]?.title ? (
          <span className="sr-only" data-testid="shelf-two-live-status">
            Showing Shelf II page {currentSlide + 1} starting with {slides[currentSlide][0].title}.
          </span>
        ) : null}

        {hasMultipleSlides ? (
          <>
            <button
              className="shelf-two-arrow shelf-two-arrow--prev"
              type="button"
              onClick={goToPrevSlide}
              aria-label="Previous slide"
            >
              <ArrowChevron direction="left" />
            </button>
            <button
              className="shelf-two-arrow shelf-two-arrow--next"
              type="button"
              onClick={goToNextSlide}
              aria-label="Next slide"
            >
              <ArrowChevron direction="right" />
            </button>
          </>
        ) : null}
      </div>

      {hasMultipleSlides && (
        <div className="shelf-two-dots" aria-hidden="true">
          {slides.map((_, dotIndex) => (
            <span
              key={`shelf-two-dot-${dotIndex}`}
              className={`shelf-two-dot${currentSlide === dotIndex ? " shelf-two-dot--active" : ""}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
