import { ArrowRight, Headphones } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";

export default function SelectedListeningRail({ books = [] }) {
  if (!books.length) return null;

  return (
    <section className="selected-listening-rail" aria-labelledby="selected-listening-title">
      <div className="selected-listening-rail__heading">
        <div>
          <div className="selected-listening-rail__eyebrow">
            <Headphones size={15} strokeWidth={1.55} aria-hidden="true" />
            Selected Listening
          </div>
          <h2 id="selected-listening-title" data-testid="selected-listening-title">
            Beautifully narrated classics ready to read and hear.
          </h2>
        </div>
        <Link className="selected-listening-rail__browse" to="/library?availability=approved-audiobook">
          See the listening shelf <ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" />
        </Link>
      </div>

      <ul className="selected-listening-rail__items" aria-label="Selected audiobooks">
        {books.map((book) => (
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
              />
            </Link>
            <div className="selected-listening-card__copy">
              <span className="selected-listening-card__language">{book.language === "bn" ? "Bengali classic" : "English classic"}</span>
              <h3>{book.title}</h3>
              <p>{book.author}</p>
              <Link className="selected-listening-card__cta" to={book.cta_url}>
                Listen in Reader <ArrowRight size={14} strokeWidth={1.65} aria-hidden="true" />
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
