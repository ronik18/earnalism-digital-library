import { Link } from "react-router-dom";

export default function BookCard({ book }) {
  return (
    <Link
      to={`/shop/${book.slug}`}
      className="card-elegant overflow-hidden flex flex-col group"
      data-testid={`book-card-${book.slug}`}
    >
      <div className="aspect-[3/4] bg-beige overflow-hidden">
        {book.cover_image_url ? (
          <img
            src={book.cover_image_url}
            alt={book.title}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center font-serif-display text-burgundy text-5xl">E</div>
        )}
      </div>
      <div className="p-6 sm:p-7 flex flex-col gap-3 flex-1">
        <span className="overline">{book.category_slug?.replace(/-/g, ' ')}</span>
        <h3 className="font-serif-display text-2xl text-charcoal leading-snug">{book.title}</h3>
        {book.short_description && (
          <p className="text-sm text-charcoal-soft leading-relaxed line-clamp-3">{book.short_description}</p>
        )}
        <div className="mt-auto flex items-center justify-between pt-4">
          <span className="text-burgundy text-sm tracking-[0.18em] uppercase border-b border-[var(--brand-gold)] pb-[2px]">View Details</span>
          {book.price_paperback ? (
            <span className="font-serif-display text-burgundy text-xl">{book.price_paperback}</span>
          ) : (
            <span className="text-xs tracking-wider uppercase text-charcoal-soft">Coming soon</span>
          )}
        </div>
      </div>
    </Link>
  );
}
