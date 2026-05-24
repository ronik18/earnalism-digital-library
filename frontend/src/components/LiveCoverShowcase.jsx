import { memo, useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, CreditCard } from "lucide-react";
import { optimizedImageUrl } from "../lib/images";

function LiveCoverShowcase({ books = [], featured }) {
  const liveBooks = useMemo(() => {
    const seen = new Set();
    const candidates = [...books, featured].filter(Boolean).map((book) => ({
      ...book,
      slug: book.slug || book.id,
    }));
    return candidates
      .filter((book) => {
        const slug = book.slug;
        const cover = book.cover_image_url || book.cover_url || book.thumbnail_url;
        if (!slug || !cover || seen.has(slug)) return false;
        seen.add(slug);
        return true;
      });
  }, [books, featured]);

  const marqueeBooks = liveBooks.length > 0 ? [...liveBooks, ...liveBooks] : [];
  const primaryBook = liveBooks[0] || featured;

  if (!primaryBook && liveBooks.length === 0) {
    return (
      <div className="live-cover-showcase live-cover-showcase--loading" data-testid="live-cover-showcase-loading" aria-label="Loading live books">
        <div className="live-cover-showcase__rail">
          {[0, 1, 2, 3].map((item) => (
            <span key={item} className="live-cover-skeleton" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <aside className="live-cover-showcase" data-testid="live-cover-showcase" aria-label="Live Earnalism books">
      <div className="live-cover-showcase__header">
        <span className="live-cover-showcase__kicker">Live now</span>
        <span>{liveBooks.length} reading rooms open</span>
      </div>

      <div className="live-cover-marquee" aria-label="Live book cover slideshow">
        <div className="live-cover-marquee__edge live-cover-marquee__edge--left" aria-hidden="true" />
        <div className="live-cover-marquee__track">
          {marqueeBooks.map((book, index) => {
            const cover = book.cover_image_url || book.cover_url || book.thumbnail_url;
            const isDuplicate = index >= liveBooks.length;
            return (
              <article
                key={`${book.slug}-${index}`}
                className="live-cover-card"
                aria-hidden={isDuplicate ? "true" : undefined}
                data-testid={isDuplicate ? undefined : `live-cover-card-${book.slug}`}
              >
                <Link
                  to={`/book/${book.slug}#preview-payment`}
                  tabIndex={isDuplicate ? -1 : 0}
                  className="live-cover-card__cover"
                  aria-label={`Open ${book.title} preview and reading time options`}
                >
                  <img
                    src={optimizedImageUrl(cover, { width: 420, quality: 88 })}
                    alt={book.title}
                    loading={index < 4 ? "eager" : "lazy"}
                    decoding="async"
                  />
                </Link>
                <div className="live-cover-card__body">
                  <h3>{book.title}</h3>
                  {book.author && <p>{book.author}</p>}
                </div>
              </article>
            );
          })}
        </div>
        <div className="live-cover-marquee__edge live-cover-marquee__edge--right" aria-hidden="true" />
      </div>

      {primaryBook && (
        <div className="live-cover-showcase__cta">
          <Link to={`/reader/${primaryBook.slug}`} className="live-cover-action live-cover-action--preview" data-testid="live-cover-primary-preview">
            <BookOpen size={15} strokeWidth={1.6} /> Read Preview
          </Link>
          <Link to={`/book/${primaryBook.slug}#preview-payment`} className="live-cover-action live-cover-action--pay" data-testid="live-cover-primary-payment">
            <CreditCard size={15} strokeWidth={1.6} /> Preview & Pay
          </Link>
          <Link to="/library" className="live-cover-showcase__library" data-testid="live-cover-library">
            All books <ArrowRight size={13} strokeWidth={1.6} />
          </Link>
        </div>
      )}
    </aside>
  );
}

export default memo(LiveCoverShowcase);
