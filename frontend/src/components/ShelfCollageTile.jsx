import { useState } from "react";
import { ArrowRight, BookOpen, Compass, Heart, MoonStar, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import { getShelfCountLabel, getShelfThemeChips, getShelfVariant, getUniqueShelfBooks } from "../lib/homeShelfRunway";

const ICONS = {
  "book-open": BookOpen,
  compass: Compass,
  heart: Heart,
  "moon-star": MoonStar,
  sparkles: Sparkles,
};

export default function ShelfCollageTile({ group, index = 0 }) {
  const [failedSlugs, setFailedSlugs] = useState(() => new Set());
  const books = getUniqueShelfBooks({
    ...group,
    books: (Array.isArray(group?.books) ? group.books : [])
      .filter((book) => book?.slug && !failedSlugs.has(book.slug)),
  });
  if (!books.length) return null;

  const Icon = ICONS[group.icon] || BookOpen;
  const headingId = `curated-shelf-${group.id || index}-title`;
  const variant = getShelfVariant({ ...group, books });
  const countLabel = getShelfCountLabel({ ...group, books });
  const themeChips = getShelfThemeChips(group);

  return (
    <article
      className={`curated-shelf-tile curated-shelf-tile--${variant} curated-shelf-tile--accent-${group.accent || "burgundy"}`}
      style={{ "--shelf-area": group.layout_area || group.id || `shelf-${index}` }}
      data-testid={`curated-shelf-tile-${group.id || index}`}
      data-layout-area={group.layout_area || group.id || `shelf-${index}`}
      data-shelf-area={group.layout_area || group.id || `shelf-${index}`}
      data-variant={variant}
      aria-labelledby={headingId}
    >
      <div className="curated-shelf-tile__topline">
        <span className="curated-shelf-tile__icon" aria-hidden="true">
          <Icon size={26} strokeWidth={1.35} />
        </span>
        <span className="curated-shelf-tile__count">{countLabel}</span>
      </div>
      <h3 id={headingId}>{group.title}</h3>
      <p className="curated-shelf-tile__description">{group.description}</p>
      {group.editorial_line && <p className="curated-shelf-tile__editorial-line">{group.editorial_line}</p>}
      <ul className="curated-shelf-tile__themes" aria-label={`${group.title} themes`}>
        {themeChips.map((theme) => <li key={theme}>{theme}</li>)}
      </ul>

      <div className="curated-shelf-tile__cover-stage">
        <ul className="curated-shelf-tile__covers" aria-label={`${group.title} books`}>
        {books.map((book, bookIndex) => (
          <li
            className={`curated-shelf-tile__cover-item ${variant === "shelf-feature" && bookIndex === 1 ? "curated-shelf-tile__cover-item--dominant" : ""}`}
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
                allowGraphicalFallback={false}
                onImageError={() => setFailedSlugs((current) => new Set([...current, book.slug]))}
              />
            </Link>
          </li>
        ))}
        </ul>
        <span className="curated-shelf-tile__plinth" aria-hidden="true" />
      </div>

      <Link className="curated-shelf-tile__cta" to={group.cta_url}>
        <span>{group.cta_label}</span>
        <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
      </Link>
    </article>
  );
}
