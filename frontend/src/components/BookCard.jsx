import { Link } from "react-router-dom";
import { Clock } from "lucide-react";
import { memo } from "react";
import { optimizedImageUrl } from "../lib/images";

function BookCard({ book }) {
  const coverSrc = optimizedImageUrl(book.cover_image_url, { width: 720 });
  return (
    <div className="card-elegant overflow-hidden flex flex-col group" data-testid={`book-card-${book.slug}`}>
      <Link to={`/book/${book.slug}`} className="block aspect-[3/4] bg-beige-deep overflow-hidden relative">
        {book.cover_image_url ? (
          <img
            src={coverSrc}
            alt={book.title}
            loading="lazy"
            decoding="async"
            className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center font-serif-light text-burgundy text-6xl">E</div>
        )}
      </Link>
      <div className="p-7 sm:p-8 flex flex-col gap-3 flex-1">
        <span className="overline">{book.category_slug?.replace(/-/g, ' ')}</span>
        <Link to={`/book/${book.slug}`} className="group/title">
          <h3 className="font-serif-display text-[1.55rem] sm:text-[1.65rem] text-burgundy leading-[1.15] group-hover/title:text-burgundy-soft transition-colors">{book.title}</h3>
        </Link>
        {book.author && (
          <p className="text-[0.85rem] tracking-[0.14em] uppercase text-charcoal-soft">by {book.author}</p>
        )}
        {book.short_description && (
          <p className="text-sm text-charcoal-soft leading-relaxed line-clamp-3 font-light">{book.short_description}</p>
        )}
        {book.estimated_reading_time && (
          <div className="inline-flex items-center gap-1.5 text-[0.72rem] tracking-[0.18em] uppercase text-gold-deep">
            <Clock size={12} strokeWidth={1.5} /> {book.estimated_reading_time}
          </div>
        )}
        <div className="mt-auto flex flex-col sm:flex-row gap-2 sm:gap-3 pt-5 border-t border-brand-soft">
          <Link to={`/reader/${book.slug}`} className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase text-burgundy border border-[var(--brand-gold)] hover:bg-[var(--brand-gold)]/10 transition-colors" data-testid={`card-preview-${book.slug}`}>Read Preview</Link>
          <Link to={`/reader/${book.slug}`} className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase bg-burgundy text-[var(--brand-ivory)] hover:bg-burgundy-deep transition-colors" data-testid={`card-start-${book.slug}`}>Start Reading</Link>
        </div>
      </div>
    </div>
  );
}

export default memo(BookCard);
