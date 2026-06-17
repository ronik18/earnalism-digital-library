import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronLeft, Clock, BookOpen, CreditCard, Sparkles, Headphones, Languages, LibraryBig } from "lucide-react";
import { api } from "../lib/api";
import ShareButtons from "../components/ShareButtons";
import BookCoverImage from "../components/BookCoverImage";
import JsonLd from "../components/JsonLd";
import useSEO, { SITE_URL, FALLBACK_OG_IMAGE, absoluteUrl } from "../hooks/useSEO";

const BENGALI_RE = /[\u0980-\u09FF]/;

function cleanText(value = "") {
  return String(value || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function truncate(value = "", maxLength = 156) {
  const text = cleanText(value);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).replace(/\s+\S*$/, "")}…`;
}

function categoryLabel(slug = "") {
  return cleanText(slug).split("-").filter(Boolean).map((word) => (
    word.length <= 2 ? word.toUpperCase() : `${word.charAt(0).toUpperCase()}${word.slice(1)}`
  )).join(" ");
}

function detectBookLanguage(book = {}) {
  const explicit = cleanText(book.language || book.language_hint || book.in_language || "");
  if (explicit) return explicit.toLowerCase().startsWith("bn") ? "bn" : "en";
  return BENGALI_RE.test(`${book.title || ""} ${book.author || ""} ${book.description || ""} ${book.short_description || ""}`) ? "bn" : "en";
}

function hasAudiobook(book = {}) {
  const assets = book.audiobook_assets || {};
  const nested = book.audiobook || {};
  return Boolean(
    book.audiobook_enabled
    || book.generate_audiobook
    || book.narration_enabled
    || book.audio_slug
    || book.audio_asset_slug
    || book.audiobook_provider
    || nested.provider
    || nested.url
    || assets.mp3
    || assets.manifest
  );
}

function audiobookDataForSeo(book = {}) {
  const assets = book.audiobook_assets || {};
  const nested = book.audiobook || {};
  const source = nested.url || assets.mp3 || assets.audio || assets.m4a || assets.ogg || book.audio_asset_slug || book.audio_slug || "";
  const sourceText = String(source || "").toLowerCase();
  const provider = cleanText(nested.provider || book.audiobook_provider || "");
  let encodingFormat = "";
  if (sourceText.includes(".m4a") || sourceText.includes(".mp4")) encodingFormat = "audio/mp4";
  else if (sourceText.includes(".ogg")) encodingFormat = "audio/ogg";
  else if (sourceText.includes(".wav")) encodingFormat = "audio/wav";
  else if (sourceText.includes(".mp3") || assets.mp3 || book.audio_asset_slug || book.audio_slug) encodingFormat = "audio/mpeg";

  return {
    hasConcreteAudio: Boolean(source || assets.manifest),
    encodingFormat,
    provider,
  };
}

function seoTitleForBook(book, audiobookAvailable) {
  if (!book) return "Book | Earnalism Digital Library";
  const action = audiobookAvailable ? "Read or Listen" : "Read";
  return book.author
    ? `${book.title} by ${book.author} | ${action} on Earnalism`
    : `${book.title} | ${action} on Earnalism`;
}

function seoDescriptionForBook(book, audiobookAvailable) {
  if (!book) return "Preview books and audiobooks on Earnalism with flexible reading-time access.";
  const authorPhrase = book.author ? ` by ${book.author}` : "";
  const actionPhrase = audiobookAvailable ? "Read or listen" : "Read";
  const base = `Preview ${book.title}${authorPhrase} on Earnalism. ${actionPhrase} through the Earnalism Digital Library with flexible reading-time access.`;
  const summary = cleanText(book.short_description || book.description || book.subtitle || "");
  return truncate(summary ? `${base} ${summary}` : base);
}

function dateOnly(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

export default function BookDetail() {
  const { slug } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadStatus, setLoadStatus] = useState("idle");

  const bookNotFound = !loading && loadStatus === "not_found";
  const bookLoadError = !loading && loadStatus === "error";
  const shouldNoindex = bookNotFound || bookLoadError;
  const bookLanguage = book ? detectBookLanguage(book) : "en";
  const audiobookAvailable = book ? hasAudiobook(book) : false;
  const audiobookSeoData = book ? audiobookDataForSeo(book) : {};
  const bookGenre = categoryLabel(book?.category_slug || "");
  const canonicalPath = `/book/${slug}`;
  const canonicalUrl = `${SITE_URL}${canonicalPath}`;
  const bookSeoTitle = bookNotFound
    ? "Book Not Found | Earnalism Digital Library"
    : book ? seoTitleForBook(book, audiobookAvailable) : "Book | Earnalism Digital Library";
  const bookSeoDescription = bookNotFound
    ? "This Earnalism book is no longer available."
    : book ? seoDescriptionForBook(book, audiobookAvailable) : "Preview books and audiobooks on Earnalism with flexible reading-time access.";
  const bookCoverImage = absoluteUrl(book?.cover_image_url || book?.cover_url || FALLBACK_OG_IMAGE);

  useSEO({
    title: bookSeoTitle,
    description: bookSeoDescription,
    image: bookCoverImage,
    imageAlt: book ? `${book.title} book cover on Earnalism` : "Earnalism Digital Library",
    type: bookNotFound ? "website" : "book",
    robots: shouldNoindex ? "noindex, nofollow" : "index, follow",
    canonicalPath,
    language: bookLanguage,
    keywords: book ? [
      book.title,
      book.author,
      bookGenre,
      audiobookAvailable ? "audiobook" : "",
      "Earnalism",
      "digital library",
      bookLanguage === "bn" ? "Bengali books" : "English books",
      "reading-time access",
    ].filter(Boolean).join(", ") : undefined,
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadStatus("loading");
    api.get(`/books/${slug}`, { signal: controller.signal }).then((r) => {
      setBook(r.data);
      setLoadStatus("ready");
    })
      .catch((err) => {
        if (err.name !== "CanceledError") {
          setBook(null);
          setLoadStatus(err.response?.status === 404 ? "not_found" : "error");
        }
      }).finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  useEffect(() => {
    if (loading || !book || window.location.hash !== "#preview-payment") return;
    window.requestAnimationFrame(() => {
      document.getElementById("preview-payment")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [book, loading]);

  const breadcrumbSchema = book ? {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": `${SITE_URL}/` },
      { "@type": "ListItem", "position": 2, "name": "Library", "item": `${SITE_URL}/library` },
      ...(book.category_slug ? [{
        "@type": "ListItem",
        "position": 3,
        "name": bookGenre,
        "item": `${SITE_URL}/library?category=${encodeURIComponent(book.category_slug)}`,
      }] : []),
      {
        "@type": "ListItem",
        "position": book.category_slug ? 4 : 3,
        "name": book.title,
        "item": canonicalUrl,
      },
    ],
  } : null;

  const bookSchema = book ? {
    "@context": "https://schema.org",
    "@type": "Book",
    "@id": `${canonicalUrl}#book`,
    "name": book.title,
    ...(book.subtitle ? { "alternativeHeadline": book.subtitle } : {}),
    "description": bookSeoDescription,
    ...(bookCoverImage ? { "image": bookCoverImage } : {}),
    ...(bookGenre ? { "genre": bookGenre } : {}),
    "bookFormat": "https://schema.org/EBook",
    "inLanguage": bookLanguage,
    "author": { "@type": book.author && book.author !== "The Earnalism" ? "Person" : "Organization", "name": book.author || "The Earnalism" },
    "publisher": { "@type": "Organization", "name": "Earnalism by Reo Enterprise", "url": SITE_URL },
    "url": canonicalUrl,
    "mainEntityOfPage": canonicalUrl,
    ...(dateOnly(book.updated_at || book.created_at) ? { "dateModified": dateOnly(book.updated_at || book.created_at) } : {}),
    ...(book.page_count ? { "numberOfPages": book.page_count } : {}),
    ...(audiobookSeoData.hasConcreteAudio ? {
      "associatedMedia": {
        "@type": "AudioObject",
        "name": `${book.title} audiobook`,
        "inLanguage": bookLanguage,
        ...(audiobookSeoData.encodingFormat ? { "encodingFormat": audiobookSeoData.encodingFormat } : {}),
        "url": canonicalUrl,
        "provider": { "@type": "Organization", "name": audiobookSeoData.provider || "Earnalism" },
      },
    } : {}),
  } : null;

  if (loading) return <div className="max-w-7xl mx-auto px-6 py-32 text-center text-charcoal-soft">Loading…</div>;
  if (bookNotFound) return (
    <div className="max-w-7xl mx-auto px-6 py-32 text-center" data-testid="book-not-found">
      <div className="italic-eyebrow mb-4">Unavailable title</div>
      <h1 className="font-serif-light text-4xl text-burgundy">Book not found</h1>
      <p className="mx-auto mt-5 max-w-xl text-charcoal-soft leading-relaxed">
        This book has been removed from Earnalism and is no longer available in the reader.
      </p>
      <Link to="/library" className="btn-secondary mt-6">Back to the Library</Link>
    </div>
  );
  if (bookLoadError || !book) return (
    <div className="max-w-7xl mx-auto px-6 py-32 text-center" data-testid="book-load-error">
      <div className="italic-eyebrow mb-4">Library connection</div>
      <h1 className="font-serif-light text-4xl text-burgundy">Book could not be opened</h1>
      <p className="mx-auto mt-5 max-w-xl text-charcoal-soft leading-relaxed">
        The title could not be loaded right now. Please return to the library and try again.
      </p>
      <Link to="/library" className="btn-secondary mt-6">Back to the Library</Link>
    </div>
  );

  const chapterCount = (book.chapters || []).length;
  const hasExplicitPreview = (book.chapters || []).some((chapter) => chapter.is_preview === true);
  const hasFreePreview = hasExplicitPreview || chapterCount > 1;
  const startReadingHref = `/pricing?pack=1h&source=book_detail&book=${book.slug}`;

  return (
    <div data-testid="book-page">
      {bookSchema && <JsonLd id="book" data={bookSchema} />}
      {breadcrumbSchema && <JsonLd id="book-breadcrumb" data={breadcrumbSchema} />}
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-10">
        <Link to="/library" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-to-library">
          <ChevronLeft size={14} /> Back to Library
        </Link>
      </div>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
        <div className="lg:col-span-5 lg:sticky lg:top-28">
          <div className="aspect-[3/4] rounded-xl overflow-hidden border border-brand-soft bg-ivory-warm shadow-[0_50px_90px_-40px_rgba(74,28,39,0.45)] max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none">
            <BookCoverImage
              book={book}
              alt={book.title}
              loading="eager"
              fetchPriority="high"
              width={640}
              widths={[420, 640, 900]}
              sizes="(min-width: 1024px) 420px, (min-width: 640px) 52vw, 90vw"
            />
          </div>
          {book.back_cover_image_url && (
            <div className="mt-5 max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none">
              <div className="overline mb-2">Back cover</div>
              <div className="aspect-[3/4] rounded-lg overflow-hidden border border-brand-soft bg-ivory-warm">
                <BookCoverImage
                  book={{
                    ...book,
                    cover_image_url: book.back_cover_image_url,
                    cover_url: book.back_cover_url,
                    thumbnail_url: book.back_cover_thumbnail_url,
                    blur_placeholder: book.back_cover_blur_placeholder,
                    dominant_color: book.back_cover_dominant_color,
                  }}
                  alt={`${book.title} back cover`}
                  loading="lazy"
                  width={640}
                  widths={[420, 640, 900]}
                  sizes="(min-width: 1024px) 420px, (min-width: 640px) 52vw, 90vw"
                />
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-7">
          <div className="overline mb-5">{bookGenre}</div>
          <h1 className="font-serif-light text-4xl sm:text-5xl lg:text-[3.75rem] text-burgundy leading-[1.02] tracking-tight">{book.title}</h1>
          {book.author && <p className="text-[0.85rem] tracking-[0.14em] uppercase text-charcoal-soft mt-4">by {book.author}</p>}
          {book.subtitle && <p className="font-serif-display italic text-xl sm:text-2xl text-burgundy-soft mt-5 leading-snug">{book.subtitle}</p>}
          <div className="gold-rule-thin mt-8" />
          <p className="text-charcoal-soft mt-7 leading-[1.85] font-light">{book.description}</p>

          {/* Reader meta row */}
          <div className="flex items-center gap-8 mt-8 flex-wrap" data-testid="book-meta">
            {bookGenre && (
              <div className="flex items-center gap-2 text-charcoal">
                <LibraryBig size={16} className="text-gold" strokeWidth={1.5} />
                <span className="text-[0.9rem]"><span className="font-serif-display italic">{bookGenre}</span></span>
              </div>
            )}
            <div className="flex items-center gap-2 text-charcoal">
              <Languages size={16} className="text-gold" strokeWidth={1.5} />
              <span className="text-[0.9rem]"><span className="font-serif-display italic">{bookLanguage === "bn" ? "Bengali" : "English"}</span> edition</span>
            </div>
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
            <div className="flex items-center gap-2 text-charcoal">
              <Headphones size={16} className="text-gold" strokeWidth={1.5} />
              <span className="text-[0.9rem]">{audiobookAvailable ? "Audiobook available" : "Reading edition"}</span>
            </div>
          </div>

          {/* CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row gap-3 flex-wrap items-stretch sm:items-center" data-testid="book-actions">
            {hasFreePreview && (
              <Link to={`/reader/${book.slug}`} className="btn-secondary justify-center" data-testid="read-preview">Read Preview</Link>
            )}
            <Link to={startReadingHref} className="btn-primary justify-center" data-testid="start-reading">Start Reading</Link>
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

      <section id="preview-payment" className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-6 pb-20 sm:pb-28" data-testid="preview-payment-section">
        <div className="preview-payment-shell">
          <div className="preview-payment-shell__cover" aria-hidden="true">
            <BookCoverImage
              book={book}
              alt=""
              loading="lazy"
              width={320}
              widths={[240, 320, 420]}
              sizes="8rem"
            />
          </div>
          <div className="preview-payment-shell__copy">
            <div className="italic-eyebrow">Preview, then continue</div>
            <h2>Open the first pages. Add reading time only when the book has earned your hour.</h2>
            <p>
              Start with the free preview, then move straight into a reading-time pack when you are ready to continue without losing the thread.
            </p>
            <div className="preview-payment-shell__proof">
              <span><Sparkles size={14} strokeWidth={1.5} /> No subscription</span>
              <span><Clock size={14} strokeWidth={1.5} /> Time runs only while reading</span>
            </div>
          </div>
          <div className="preview-payment-shell__actions">
            <Link to={`/reader/${book.slug}`} className="btn-secondary w-full justify-center" data-testid="bottom-read-preview">
              <BookOpen size={15} strokeWidth={1.6} /> Read Preview
            </Link>
            <Link to={`/pricing?pack=1h&source=book_preview&book=${book.slug}`} className="btn-primary w-full justify-center" data-testid="bottom-buy-reading-time">
              <CreditCard size={15} strokeWidth={1.6} /> Buy Reading Time
            </Link>
            {book.buy_url && (
              <a href={book.buy_url} target="_blank" rel="noreferrer" className="preview-payment-shell__external" data-testid="bottom-external-buy">
                Publisher checkout
              </a>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
