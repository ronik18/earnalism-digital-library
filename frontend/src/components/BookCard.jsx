import { Link } from "react-router-dom";

export default function BookCard({ book }) {
  return (
    <Link
      to={`/shop/${book.slug}`}
      className="card-elegant overflow-hidden flex flex-col group"
      data-testid={`book-card-${book.slug}`}
    >
      <div className="aspect-[3/4] bg-beige-deep overflow-hidden relative">
        {book.cover_image_url ? (
          <img
            src={book.cover_image_url}
            alt={book.title}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-[900ms] group-hover:scale-[1.04]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center font-serif-light text-burgundy text-6xl">E</div>
        )}
      </div>
      <div className="p-7 sm:p-8 flex flex-col gap-3 flex-1">
        <span className="overline">{book.category_slug?.replace(/-/g, ' ')}</span>
        <h3 className="font-serif-display text-[1.55rem] sm:text-[1.65rem] text-burgundy leading-[1.15]">{book.title}</h3>
        {book.subtitle && (
          <p className="font-serif-display italic text-base text-charcoal-soft leading-snug">{book.subtitle}</p>
        )}
        {book.short_description && !book.subtitle && (
          <p className="text-sm text-charcoal-soft leading-relaxed line-clamp-3 font-light">{book.short_description}</p>
        )}
        <div className="mt-auto flex items-center justify-between pt-6 border-t border-brand-soft">
          <span className="text-burgundy text-[0.7rem] tracking-[0.22em] uppercase">Read more &rarr;</span>
          {book.price_paperback ? (
            <span className="font-serif-display text-burgundy text-xl">{book.price_paperback}</span>
          ) : (
            <span className="italic-accent text-charcoal-soft text-sm">coming soon</span>
          )}
        </div>
      </div>
    </Link>
  );
}
