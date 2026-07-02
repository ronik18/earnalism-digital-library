import { useMemo, useState, useEffect } from "react";

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

  useEffect(() => {
    if (!slides.length) {
      setCurrentSlide(0);
      return;
    }

    if (currentSlide >= slides.length) {
      setCurrentSlide(0);
    }
  }, [slides.length, currentSlide]);

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
    <div className="shelf-two-shelf" aria-live="polite">
      <div className="shelf-two-viewport">
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
            >
              <div className="shelf-two-grid">
                {slide.map((book) => {
                  const isPublished = book.status === "published";
                  const statusClass = isPublished ? "published" : "queued";
                  return (
                    <article key={book.id} className="shelf-two-book">
                      <div className="shelf-two-book__cover-wrap">
                        {book.coverUrl ? (
                          <img
                            src={book.coverUrl}
                            alt={`${book.title} cover`}
                            loading="lazy"
                            className="shelf-two-book__cover"
                          />
                        ) : (
                          <div className="shelf-two-book__cover shelf-two-book__cover--placeholder" aria-label={`No cover available for ${book.title}`}>
                            {book.title?.slice(0, 2).toUpperCase() || "B"}
                          </div>
                        )}
                      </div>

                      <p className="shelf-two-book__title">{book.title}</p>

                      {isPublished ? (
                        <a
                          className="shelf-two-book__cta shelf-two-book__cta--published"
                          href={`/book/${book.id}`}
                          aria-label={`Start reading ${book.title}`}
                        >
                          Start Reading
                        </a>
                      ) : (
                        <button
                          type="button"
                          className="shelf-two-book__cta shelf-two-book__cta--queued"
                          aria-label={`Notify me for ${book.title}`}
                          onClick={(event) => event.preventDefault()}
                        >
                          Notify Me
                        </button>
                      )}

                      <span className={`shelf-two-book__status shelf-two-book__status--${statusClass}`}>
                        {statusClass === "published" ? "Live" : "Coming Soon"}
                      </span>
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
