import { useEffect, useMemo, useState } from "react";
import BookCoverImage from "./BookCoverImage";

function chunkBooks(books) {
  const grouped = [];

  for (let i = 0; i < books.length; i += 5) {
    grouped.push(books.slice(i, i + 5));
  }

  return grouped;
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

export default function ShelfTwoSlideshow({ books = [] }) {
  const slides = useMemo(() => chunkBooks(books), [books]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

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
    if (slides.length <= 1) return undefined;
    if (isPaused) return undefined;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return undefined;

    const timer = window.setInterval(() => {
      setCurrentSlide((index) => (index === slides.length - 1 ? 0 : index + 1));
    }, 5200);

    return () => window.clearInterval(timer);
  }, [isPaused, slides.length]);

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
          style={{ transform: `translateX(-${currentSlide * 100}%)` }}
        >
          {slides.map((slide, slideIndex) => (
            <section
              key={`shelf-two-slide-${slideIndex}`}
              className="shelf-two-slide"
              aria-label={`Shelf 2 page ${slideIndex + 1}`}
              aria-hidden={slideIndex !== currentSlide}
              data-active={slideIndex === currentSlide ? "true" : "false"}
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
                            href={`/book/${book.id}`}
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
