import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronLeft, Clock, BookOpen } from "lucide-react";
import { api } from "../lib/api";
import ShareButtons from "../components/ShareButtons";
import JsonLd from "../components/JsonLd";
import useSEO from "../hooks/useSEO";

export default function BookDetail() {
  const { slug } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);

  useSEO({
    title: book ? `${book.title} — The Earnalism Digital Library` : "Book — The Earnalism Digital Library",
    description: book?.short_description || book?.subtitle || "A curated digital title from The Earnalism Digital Library — for readers who value depth, beauty, and meaning.",
    image: book?.cover_image_url,
    type: "book",
  });

  useEffect(() => {
    setLoading(true);
    api.get(`/books/${slug}`).then((r) => setBook(r.data))
      .catch(() => setBook(null)).finally(() => setLoading(false));
  }, [slug]);

  const bookSchema = book ? {
    "@context": "https://schema.org",
    "@type": "Book",
    "name": book.title,
    ...(book.subtitle ? { "alternativeHeadline": book.subtitle } : {}),
    "description": book.description || book.short_description,
    ...(book.cover_image_url ? { "image": book.cover_image_url } : {}),
    "bookFormat": "https://schema.org/EBook",
    "inLanguage": "en",
    "author": { "@type": "Organization", "name": book.author || "The Earnalism" },
    "publisher": { "@type": "Organization", "name": "The Earnalism" },
    "url": typeof window !== "undefined" ? window.location.href : undefined,
    "numberOfPages": (book.chapters || []).length || undefined,
  } : null;

  if (loading) return <div className="max-w-7xl mx-auto px-6 py-32 text-center text-charcoal-soft">Loading…</div>;
  if (!book) return (
    <div className="max-w-7xl mx-auto px-6 py-32 text-center" data-testid="book-not-found">
      <h1 className="font-serif-light text-4xl text-burgundy">Book not found</h1>
      <Link to="/library" className="btn-secondary mt-6">Back to the Library</Link>
    </div>
  );

  const chapterCount = (book.chapters || []).length;

  return (
    <div data-testid="book-page">
      {bookSchema && <JsonLd id="book" data={bookSchema} />}
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-10">
        <Link to="/library" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-to-library">
          <ChevronLeft size={14} /> Back to Library
        </Link>
      </div>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
        <div className="lg:col-span-5 lg:sticky lg:top-28">
          <div className="aspect-[3/4] rounded-xl overflow-hidden border border-brand-soft shadow-[0_50px_90px_-40px_rgba(74,28,39,0.45)] max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none">
            {book.cover_image_url ? (
              <img src={book.cover_image_url} alt={book.title} className="w-full h-full object-cover" />
            ) : <div className="w-full h-full bg-beige-deep flex items-center justify-center font-serif-light text-7xl text-burgundy">E</div>}
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="overline mb-5">{book.category_slug?.replace(/-/g, ' ')}</div>
          <h1 className="font-serif-light text-4xl sm:text-5xl lg:text-[3.75rem] text-burgundy leading-[1.02] tracking-tight">{book.title}</h1>
          {book.author && <p className="text-[0.85rem] tracking-[0.14em] uppercase text-charcoal-soft mt-4">by {book.author}</p>}
          {book.subtitle && <p className="font-serif-display italic text-xl sm:text-2xl text-burgundy-soft mt-5 leading-snug">{book.subtitle}</p>}
          <div className="gold-rule-thin mt-8" />
          <p className="text-charcoal-soft mt-7 leading-[1.85] font-light">{book.description}</p>

          {/* Reader meta row */}
          <div className="flex items-center gap-8 mt-8 flex-wrap" data-testid="book-meta">
            {chapterCount > 0 && (
              <div className="flex items-center gap-2 text-charcoal">
                <BookOpen size={16} className="text-gold" strokeWidth={1.5} />
                <span className="text-[0.9rem]"><span className="font-serif-display italic">{chapterCount}</span> {chapterCount === 1 ? "chapter" : "chapters"}</span>
              </div>
            )}
            {book.estimated_reading_time && (
              <div className="flex items-center gap-2 text-charcoal">
                <Clock size={16} className="text-gold" strokeWidth={1.5} />
                <span className="text-[0.9rem]">About <span className="font-serif-display italic">{book.estimated_reading_time}</span></span>
              </div>
            )}
          </div>

          {/* CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row gap-3 flex-wrap items-stretch sm:items-center" data-testid="book-actions">
            <Link to={`/reader/${book.slug}`} className="btn-secondary justify-center" data-testid="read-preview">Read Preview</Link>
            <Link to={`/reader/${book.slug}`} className="btn-primary justify-center" data-testid="start-reading">Start Reading</Link>
            {book.buy_url ? (
              <a href={book.buy_url} target="_blank" rel="noreferrer" className="btn-primary justify-center" data-testid="buy-reading-time">Buy Reading Time</a>
            ) : (
              <Link to="/contact" className="inline-flex items-center justify-center px-5 py-3 rounded-full text-[0.72rem] tracking-[0.2em] uppercase text-charcoal-soft hover:text-burgundy border border-brand-soft" data-testid="request-access">Request Access</Link>
            )}
          </div>

          <div className="mt-8" data-testid="book-share">
            <ShareButtons title={book.title} variant="product" testIdPrefix="book-share" />
          </div>

          {/* Chapter list */}
          {chapterCount > 0 && (
            <div className="mt-14" data-testid="chapter-list">
              <div className="italic-eyebrow mb-3">Table of Contents</div>
              <h3 className="font-serif-light text-[1.65rem] sm:text-[1.85rem] text-burgundy mb-6 leading-snug">Chapters</h3>
              <ol className="space-y-3">
                {(book.chapters || []).map((c, i) => (
                  <li key={c.id} className="flex items-baseline gap-4 text-charcoal">
                    <span className="italic-accent text-gold-deep shrink-0 w-10">{String(i + 1).padStart(2, "0")}</span>
                    <Link to={`/reader/${book.slug}?c=${c.id}`} className="font-serif-display text-[1.15rem] hover:text-burgundy transition-colors">{c.title}</Link>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {book.benefits?.length > 0 && (
            <div className="mt-14">
              <div className="italic-eyebrow mb-3">For the reader</div>
              <h3 className="font-serif-light text-[1.65rem] sm:text-[1.85rem] text-burgundy mb-6 leading-snug">What waits inside</h3>
              <ul className="space-y-4">
                {book.benefits.map((b) => (
                  <li key={b} className="flex items-start gap-3 text-charcoal-soft leading-relaxed font-light">
                    <Check size={16} className="text-gold mt-1 flex-shrink-0" strokeWidth={1.5} /><span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 grid grid-cols-1 md:grid-cols-2 gap-8">
        {book.who_for?.length > 0 && (
          <div className="card-elegant p-9 sm:p-11" data-testid="who-for">
            <div className="italic-eyebrow mb-3">Who this book is for</div>
            <h3 className="font-serif-light text-[1.65rem] text-burgundy mb-6 leading-snug">Written for the careful builder</h3>
            <ul className="space-y-4 text-charcoal-soft leading-relaxed font-light">
              {book.who_for.map((w) => <li key={w} className="flex gap-3"><span className="text-gold">—</span>{w}</li>)}
            </ul>
          </div>
        )}
        {book.learnings?.length > 0 && (
          <div className="card-elegant p-9 sm:p-11" data-testid="learnings">
            <div className="italic-eyebrow mb-3">What you will learn</div>
            <h3 className="font-serif-light text-[1.65rem] text-burgundy mb-6 leading-snug">A practical inheritance</h3>
            <ul className="space-y-4 text-charcoal-soft leading-relaxed font-light">
              {book.learnings.map((l) => <li key={l} className="flex gap-3"><span className="text-gold">—</span>{l}</li>)}
            </ul>
          </div>
        )}
      </section>

      {book.about_author && (
        <section className="max-w-3xl mx-auto px-5 sm:px-8 lg:px-12 py-16 text-center" data-testid="about-author">
          <div className="italic-eyebrow mb-4">About the author / publisher</div>
          <p className="font-serif-display italic text-xl sm:text-2xl lg:text-[1.65rem] text-burgundy leading-[1.45]">{book.about_author}</p>
          <div className="gold-rule mx-auto mt-8" />
        </section>
      )}
    </div>
  );
}
