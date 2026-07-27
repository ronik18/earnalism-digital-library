import { useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Headphones } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import "./PremiumListeningRail.css";

function listenUrl(book) {
  return book?.cta_url || book?.primary_cta_url || `/reader/${book?.slug}?listen=1`;
}

export default function PremiumListeningRail({ books = [], reserveBooks = [] }) {
  const [failedSlugs, setFailedSlugs] = useState(() => new Set());
  const viewportRef = useRef(null);
  const visibleBooks = useMemo(() => {
    const primary = books.filter((book) => book?.slug && !failedSlugs.has(book.slug));
    const reserve = reserveBooks.filter((book) => (
      book?.slug && !failedSlugs.has(book.slug) && !primary.some((item) => item.slug === book.slug)
    ));
    return [...primary, ...reserve].slice(0, Math.max(1, Math.min(4, books.length || reserveBooks.length)));
  }, [books, reserveBooks, failedSlugs]);

  if (!visibleBooks.length) return null;

  const move = (direction) => {
    viewportRef.current?.scrollBy({ left: direction * Math.max(260, viewportRef.current.clientWidth * 0.78), behavior: "smooth" });
  };

  return (
    <section className="premium-listening-rail selected-listening-rail" aria-labelledby="premium-listening-title" data-testid="premium-listening-rail">
      <div className="premium-listening-rail__inner">
        <div className="premium-listening-rail__heading">
          <div>
            <div className="premium-listening-rail__eyebrow selected-listening-rail__eyebrow">
              <Headphones size={15} strokeWidth={1.55} aria-hidden="true" />
              LISTENING ROOMS
            </div>
            <h2 id="premium-listening-title" data-testid="premium-listening-title">Stories ready to be heard.</h2>
            <p>Step into beautifully narrated classics, then continue reading at your own pace.</p>
          </div>
          <div className="premium-listening-rail__actions selected-listening-rail__actions">
            {visibleBooks.length > 1 && (
              <>
                <button type="button" className="premium-listening-rail__control selected-listening-rail__control" aria-label="Previous audiobooks" aria-controls="premium-listening-items" onClick={() => move(-1)}>
                  <ArrowLeft size={16} aria-hidden="true" />
                </button>
                <button type="button" className="premium-listening-rail__control selected-listening-rail__control" aria-label="Next audiobooks" aria-controls="premium-listening-items" onClick={() => move(1)}>
                  <ArrowRight size={16} aria-hidden="true" />
                </button>
              </>
            )}
            <Link className="premium-listening-rail__browse selected-listening-rail__browse" to="/library?audio=approved">
              Explore all audiobooks <ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" />
            </Link>
          </div>
        </div>

        <div className="premium-listening-rail__viewport selected-listening-rail__viewport" ref={viewportRef} id="premium-listening-viewport" tabIndex="0" aria-label="Audiobook cards. Use the previous and next buttons or swipe.">
          <ul className="premium-listening-rail__items selected-listening-rail__items" id="premium-listening-items" aria-label="Audiobooks ready to be heard">
            {visibleBooks.map((book) => (
              <li className="premium-listening-card selected-listening-card" key={book.slug} data-book-slug={book.slug}>
                <Link className="premium-listening-card__cover-link selected-listening-card__cover-link" to={book.book_url || `/book/${book.slug}`} aria-label={`Open ${book.title} by ${book.author}`}>
                  <BookCoverImage
                    book={book}
                    alt={book.cover_alt_text || `${book.title} by ${book.author}`}
                    width={150}
                    height={225}
                    widths={[150, 220, 300]}
                    sizes="(min-width: 1280px) 9vw, (min-width: 768px) 16vw, 30vw"
                    className="premium-listening-card__cover selected-listening-card__cover"
                    loading="lazy"
                    allowGraphicalFallback={false}
                    onImageError={() => setFailedSlugs((current) => new Set([...current, book.slug]))}
                  />
                </Link>
                <div className="premium-listening-card__copy selected-listening-card__copy">
                  <span className="premium-listening-card__language selected-listening-card__language">{book.language === "bn" ? "Bengali classic" : "English classic"}</span>
                  <h3>{book.title}</h3>
                  <p>{book.author}{Number(book.audio_duration_ms) > 0 ? ` · ${Math.round(Number(book.audio_duration_ms) / 60000)} min` : ""}</p>
                  <Link className="premium-listening-card__cta selected-listening-card__cta" to={listenUrl(book)} aria-label={`Listen to ${book.title} by ${book.author} in the reader`}>
                    <span>Listen in Reader</span> <ArrowRight size={14} strokeWidth={1.65} aria-hidden="true" />
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
