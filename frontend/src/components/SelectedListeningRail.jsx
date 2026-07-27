import { useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Headphones } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";

export default function SelectedListeningRail({ books = [] }) {
  const [failedSlugs, setFailedSlugs] = useState(() => new Set());
  const viewportRef = useRef(null);
  const visibleBooks = books.filter((book) => book?.slug && !failedSlugs.has(book.slug));
  if (!visibleBooks.length) return null;

  return (
    <section className="selected-listening-rail" aria-labelledby="selected-listening-title">
      <div className="selected-listening-rail__heading">
        <div>
          <div className="selected-listening-rail__eyebrow">
            <Headphones size={15} strokeWidth={1.55} aria-hidden="true" />
            LISTENING ROOMS
          </div>
          <h2 id="selected-listening-title" data-testid="selected-listening-title">Selected Listening</h2>
          <p className="selected-listening-rail__supporting-copy">Beautifully narrated classics ready to read and hear.</p>
        </div>
        <div className="selected-listening-rail__actions">
          {visibleBooks.length >= 5 && <>
            <button type="button" className="selected-listening-rail__control" aria-label="Previous audiobooks" onClick={() => viewportRef.current?.scrollBy({ left: -320, behavior: "smooth" })}><ArrowLeft size={16} aria-hidden="true" /></button>
            <button type="button" className="selected-listening-rail__control" aria-label="Next audiobooks" onClick={() => viewportRef.current?.scrollBy({ left: 320, behavior: "smooth" })}><ArrowRight size={16} aria-hidden="true" /></button>
          </>}
          <Link className="selected-listening-rail__browse" to="/library?format=audiobook">
            Explore all audiobooks <ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" />
          </Link>
        </div>
      </div>

      <div className="selected-listening-rail__viewport" ref={viewportRef}>
      <ul className="selected-listening-rail__items" aria-label="Selected audiobooks">
        {visibleBooks.map((book) => (
          <li className="selected-listening-card" key={book.slug}>
            <Link
              className="selected-listening-card__cover-link"
              to={book.book_url}
              aria-label={`Open ${book.title} by ${book.author}`}
            >
              <BookCoverImage
                book={book}
                alt={book.cover_alt_text}
                width={150}
                height={225}
                widths={[150, 220, 300]}
                sizes="(min-width: 768px) 10vw, 30vw"
                className="selected-listening-card__cover"
                loading="lazy"
                allowGraphicalFallback={false}
                onImageError={() => setFailedSlugs((current) => new Set([...current, book.slug]))}
              />
            </Link>
            <div className="selected-listening-card__copy">
              <span className="selected-listening-card__language">{book.language === "bn" ? "Bengali classic" : "English classic"}</span>
              <h3>{book.title}</h3>
              <p>{book.author}{book.audio_duration_ms ? ` · ${Math.round(book.audio_duration_ms / 60000)} min` : ""}</p>
              <Link className="selected-listening-card__cta" to={book.cta_url || book.primary_cta_url || `/reader/${book.slug}?listen=1`} aria-label={`Listen to ${book.title} by ${book.author} in the reader`}>
                <span aria-hidden="true">Listen in Reader</span> <ArrowRight size={14} strokeWidth={1.65} aria-hidden="true" />
              </Link>
            </div>
          </li>
        ))}
      </ul>
      </div>
    </section>
  );
}
