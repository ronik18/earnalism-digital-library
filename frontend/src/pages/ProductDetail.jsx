import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronLeft } from "lucide-react";
import { api } from "../lib/api";
import ShareButtons from "../components/ShareButtons";
import useSEO from "../hooks/useSEO";

export default function ProductDetail() {
  const { slug } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [format, setFormat] = useState("Paperback");

  useSEO({
    title: book ? `${book.title} — The Earnalism` : "Book — The Earnalism",
    description: book?.short_description || book?.subtitle || "A curated title from The Earnalism — for readers who value depth, beauty, and meaning.",
    image: book?.cover_image_url,
  });

  useEffect(() => {
    setLoading(true);
    api.get(`/books/${slug}`).then((r) => { setBook(r.data); setFormat((r.data.formats || ["Paperback"])[0]); })
      .catch(() => setBook(null)).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="max-w-7xl mx-auto px-6 py-32 text-center text-charcoal-soft">Loading…</div>;
  if (!book) return (
    <div className="max-w-7xl mx-auto px-6 py-32 text-center" data-testid="book-not-found">
      <h1 className="font-serif-display text-4xl text-burgundy">Book not found</h1>
      <Link to="/shop" className="btn-secondary mt-6">Back to the Collection</Link>
    </div>
  );

  const price = format === "Ebook" ? book.price_ebook : book.price_paperback;

  return (
    <div data-testid="product-page">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-10">
        <Link to="/shop" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-to-shop">
          <ChevronLeft size={14} /> Back to Collection
        </Link>
      </div>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-12 sm:py-16 grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        <div className="lg:col-span-5 lg:sticky lg:top-28">
          <div className="aspect-[3/4] rounded-2xl overflow-hidden border border-brand shadow-[0_40px_70px_-30px_rgba(74,28,39,0.4)]">
            {book.cover_image_url ? (
              <img src={book.cover_image_url} alt={book.title} className="w-full h-full object-cover" />
            ) : <div className="w-full h-full bg-beige flex items-center justify-center font-serif-display text-7xl text-burgundy">E</div>}
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="overline mb-4">{book.category_slug?.replace(/-/g, ' ')}</div>
          <h1 className="font-serif-display text-4xl sm:text-5xl lg:text-6xl text-burgundy leading-[1.05] tracking-tight">{book.title}</h1>
          {book.subtitle && <p className="font-serif-display italic text-xl sm:text-2xl text-charcoal-soft mt-4">{book.subtitle}</p>}
          <div className="gold-rule mt-7" />
          <p className="text-charcoal-soft mt-6 leading-relaxed">{book.description}</p>

          {book.formats?.length > 0 && (
            <div className="mt-9">
              <div className="overline mb-3">Format</div>
              <div className="flex gap-2 flex-wrap" data-testid="format-options">
                {book.formats.map((f) => (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    data-testid={`format-${f.toLowerCase()}`}
                    className={`px-5 py-2.5 rounded-full text-sm tracking-wider transition-all ${format === f ? "bg-burgundy text-[var(--brand-ivory)]" : "border border-[var(--brand-border)] text-charcoal hover:border-[var(--brand-gold)]"}`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-9 flex items-end gap-6 flex-wrap">
            {price ? (
              <div>
                <div className="overline mb-1">Price</div>
                <div className="font-serif-display text-4xl text-burgundy">{price}</div>
              </div>
            ) : (
              <div>
                <div className="overline mb-1">Availability</div>
                <div className="font-serif-display text-2xl text-burgundy">Coming Soon</div>
              </div>
            )}
          </div>

          <div className="mt-7 flex gap-3 flex-wrap items-center" data-testid="buy-actions">
            {book.buy_url ? (
              <a href={book.buy_url} target="_blank" rel="noreferrer" className="btn-primary" data-testid="buy-now">Buy Now</a>
            ) : (
              <Link to="/contact" className="btn-primary" data-testid="request-purchase">Request Purchase Info</Link>
            )}
          </div>

          <div className="mt-7" data-testid="product-share">
            <ShareButtons title={book.title} variant="product" testIdPrefix="product-share" />
          </div>

          {book.benefits?.length > 0 && (
            <div className="mt-12">
              <div className="overline mb-3">For the reader</div>
              <h3 className="font-serif-display text-2xl text-burgundy mb-5">What waits inside</h3>
              <ul className="space-y-3">
                {book.benefits.map((b, i) => (
                  <li key={i} className="flex items-start gap-3 text-charcoal-soft">
                    <Check size={18} className="text-gold mt-1 flex-shrink-0" /><span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-12 grid grid-cols-1 md:grid-cols-2 gap-8">
        {book.who_for?.length > 0 && (
          <div className="card-elegant p-8 sm:p-10" data-testid="who-for">
            <div className="overline mb-3">Who this book is for</div>
            <h3 className="font-serif-display text-2xl text-burgundy mb-5">Written for the careful builder</h3>
            <ul className="space-y-3 text-charcoal-soft">
              {book.who_for.map((w, i) => <li key={i} className="flex gap-2"><span className="text-gold">—</span>{w}</li>)}
            </ul>
          </div>
        )}
        {book.learnings?.length > 0 && (
          <div className="card-elegant p-8 sm:p-10" data-testid="learnings">
            <div className="overline mb-3">What you will learn</div>
            <h3 className="font-serif-display text-2xl text-burgundy mb-5">A practical inheritance</h3>
            <ul className="space-y-3 text-charcoal-soft">
              {book.learnings.map((l, i) => <li key={i} className="flex gap-2"><span className="text-gold">—</span>{l}</li>)}
            </ul>
          </div>
        )}
      </section>

      {book.about_author && (
        <section className="max-w-3xl mx-auto px-5 sm:px-8 lg:px-12 py-12 text-center" data-testid="about-author">
          <div className="overline mb-3">About the author / publisher</div>
          <p className="font-serif-display italic text-2xl sm:text-3xl text-burgundy leading-snug">{book.about_author}</p>
        </section>
      )}
    </div>
  );
}
