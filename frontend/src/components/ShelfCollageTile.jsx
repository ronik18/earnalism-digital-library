import { useState } from "react";
import { ArrowRight, BookOpen, Compass, Heart, MoonStar, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import { getShelfCountLabel, getShelfThemeChips, getShelfVariant, getUniqueShelfBooks } from "../lib/homeShelfRunway";
import { normalizeShelfArea } from "../lib/shelfGridLayout";

const ICONS = {
  "book-open": BookOpen,
  compass: Compass,
  heart: Heart,
  "moon-star": MoonStar,
  sparkles: Sparkles,
};

const LIBRARY_ROUTE_BY_SHELF = {
  "bengali-life-and-legacy": "/library?language=bn&availability=reader-ready",
  "gothic-and-the-uncanny": "/library?language=en",
  "love-society-and-human-nature": "/library?language=en",
  "adventure-nature-and-wonder": "/library?language=en",
  "short-masterpieces": "/library?language=en",
};

export default function ShelfCollageTile({ group, index = 0 }) {
  const [failedSlugs, setFailedSlugs] = useState(() => new Set());
  const candidateBooks = [
    ...(Array.isArray(group?.books) ? group.books : []),
    ...(Array.isArray(group?.reserve_books) ? group.reserve_books : []),
  ];
  const books = getUniqueShelfBooks({
    ...group,
    books: candidateBooks
      .filter((book) => book?.slug && !failedSlugs.has(book.slug)),
  }, group.display_mode === "runway" ? 6 : group.display_mode === "duo" ? 2 : group.display_mode === "spotlight" ? 1 : 3);
  const Icon = ICONS[group.icon] || BookOpen;
  const shelfArea = normalizeShelfArea(group);
  const headingId = `curated-shelf-${group.id || index}-title`;
  const variant = getShelfVariant({ ...group, books });
  const countLabel = getShelfCountLabel({ ...group, books });
  const themeChips = getShelfThemeChips(group);
  const ctaLabel = group.cta_label?.trim() || `Explore ${group.title || "this shelf"}`;
  const ctaUrl = LIBRARY_ROUTE_BY_SHELF[group.id] || group.cta_url || "/library";

  return (
    <article
      className={`curated-shelf-tile curated-shelf-tile--${variant} curated-shelf-tile--accent-${group.accent || "burgundy"}`}
      style={{ "--shelf-area": shelfArea || `shelf-${index}` }}
      data-testid={`curated-shelf-tile-${group.id || index}`}
      data-layout-area={shelfArea || `shelf-${index}`}
      data-shelf-area={shelfArea || `shelf-${index}`}
      data-variant={variant}
      data-cover-count={books.length}
      aria-labelledby={headingId}
    >
      <div className="curated-shelf-tile__body">
        <div className="curated-shelf-tile__topline" data-content-zone="meta">
          <span className="curated-shelf-tile__icon" aria-hidden="true"><Icon size={26} strokeWidth={1.35} /></span>
          <span className="curated-shelf-tile__count">{countLabel}</span>
        </div>
        <h3 id={headingId} data-content-zone="title">{group.title}</h3>
        <div className="curated-shelf-tile__description" data-content-zone="description">
          <p>{group.description}</p>
          {group.editorial_line && <p className="curated-shelf-tile__editorial-line">{group.editorial_line}</p>}
        </div>
        <ul className="curated-shelf-tile__themes" aria-label={`${group.title} themes`} data-content-zone="chips">
          {themeChips.map((theme) => <li key={theme}>{theme}</li>)}
        </ul>
        <div className="curated-shelf-tile__cover-stage" data-content-zone="covers" aria-hidden={books.length ? undefined : "true"}>
          {books.length ? <ul className="curated-shelf-tile__covers" aria-label={`${group.title} books`}>
            {books.map((book, bookIndex) => (
              <li className={`curated-shelf-tile__cover-item ${variant === "shelf-feature" && bookIndex === 1 ? "curated-shelf-tile__cover-item--dominant" : ""}`} key={book.slug}>
                <Link to={book.book_url} className="curated-shelf-tile__cover-link" aria-label={`Open ${book.title} by ${book.author}`}>
                  <BookCoverImage book={book} alt={book.cover_alt_text} width={220} height={330} widths={[180, 220, 320, 440]} sizes="(min-width: 1200px) 13vw, (min-width: 768px) 22vw, 34vw" className="curated-shelf-tile__cover" loading="lazy" allowGraphicalFallback={false} onImageError={() => setFailedSlugs((current) => new Set([...current, book.slug]))} />
                </Link>
              </li>
            ))}
          </ul> : <div className="curated-shelf-tile__editorial-mark"><Icon size={46} strokeWidth={0.9} /><span /></div>}
        </div>
        <Link className="curated-shelf-tile__cta" to={ctaUrl} data-content-zone="cta"><span>{ctaLabel}</span><ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" /></Link>
      </div>
    </article>
  );
}
