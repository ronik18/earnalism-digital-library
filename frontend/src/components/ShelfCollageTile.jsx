import { ArrowUpRight, BookOpen, Compass, Heart, MoonStar, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";

const ICONS = {
  "book-open": BookOpen,
  compass: Compass,
  heart: Heart,
  "moon-star": MoonStar,
  sparkles: Sparkles,
};

export default function ShelfCollageTile({ group, index = 0 }) {
  if (!group?.books?.length) return null;

  const Icon = ICONS[group.icon] || BookOpen;
  const headingId = `curated-shelf-${group.id || index}-title`;

  return (
    <article
      className={`curated-shelf-tile curated-shelf-tile--${group.visual_variant || "medium"}`}
      data-testid={`curated-shelf-tile-${group.id || index}`}
      aria-labelledby={headingId}
    >
      <div className="curated-shelf-tile__topline">
        <span className="curated-shelf-tile__icon" aria-hidden="true">
          <Icon size={19} strokeWidth={1.45} />
        </span>
        <span className="curated-shelf-tile__count">
          {group.book_count || group.books.length} {group.book_count === 1 ? "book" : "books"}
        </span>
      </div>
      <h3 id={headingId}>{group.title}</h3>
      <p className="curated-shelf-tile__description">{group.description}</p>

      <ul className="curated-shelf-tile__covers" aria-label={`${group.title} books`}>
        {group.books.slice(0, 3).map((book, bookIndex) => (
          <li
            className="curated-shelf-tile__cover-item"
            key={book.slug}
            style={{ "--cover-order": bookIndex }}
          >
            <Link
              to={book.book_url}
              className="curated-shelf-tile__cover-link"
              aria-label={`Open ${book.title} by ${book.author}`}
            >
              <BookCoverImage
                book={book}
                alt={book.cover_alt_text}
                width={220}
                height={330}
                widths={[180, 220, 320, 440]}
                sizes="(min-width: 1200px) 13vw, (min-width: 768px) 22vw, 34vw"
                className="curated-shelf-tile__cover"
                loading="lazy"
              />
            </Link>
          </li>
        ))}
      </ul>

      <Link className="curated-shelf-tile__cta" to={group.cta_url}>
        <span>{group.cta_label}</span>
        <ArrowUpRight size={16} strokeWidth={1.6} aria-hidden="true" />
      </Link>
    </article>
  );
}
