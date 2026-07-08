import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronLeft, Clock, BookOpen, CreditCard, Sparkles, Headphones, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import ShareButtons from "../components/ShareButtons";
import BookCoverImage from "../components/BookCoverImage";
import JsonLd from "../components/JsonLd";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import {
  DRACULA_CHAPTER_COUNT,
  DRACULA_CTA_EVENTS,
  DRACULA_RIGHTS_NOTE,
  DRACULA_SOURCE_NOTE,
  DRACULA_FALLBACK_BOOK,
  LIVE_APPROVED_SLUG,
  mergeDraculaBook,
  normalizeChapterDisplayTitle,
  readingPassUrl,
} from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";
import { bookDetailPresentationForBook } from "../lib/bookDetailPresentation";

const BENGALI_RE = /[\u0980-\u09FF]/;
const SITE_URL = "https://theearnalism.com";

function isValidBookPayload(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value) && value.slug);
}

export default function BookDetail() {
  const { slug } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadStatus, setLoadStatus] = useState("idle");

  const bookNotFound = !loading && loadStatus === "not_found";
  const bookLoadError = !loading && loadStatus === "error";
  const shouldNoindex = bookNotFound || bookLoadError;
  const publicBook = book?.slug === LIVE_APPROVED_SLUG ? mergeDraculaBook(book) : book;

  useSEO({
    title: bookNotFound
      ? "Book not found — The Earnalism Digital Library"
      : publicBook?.slug === LIVE_APPROVED_SLUG
        ? "Dracula by Bram Stoker | Read Chapter 1 Free on Earnalism"
        : publicBook ? `${publicBook.title} — The Earnalism Digital Library` : "Book — The Earnalism Digital Library",
    description: bookNotFound
      ? "This Earnalism book is no longer available."
      : publicBook?.slug === LIVE_APPROVED_SLUG
        ? "Preview Dracula by Bram Stoker on Earnalism. Read Chapter 1 free and continue the approved classic reading release with flexible reading-time access."
        : publicBook?.short_description || publicBook?.subtitle || "A curated digital title from The Earnalism Digital Library — for readers who value depth, beauty, and meaning.",
    image: publicBook?.cover_image_url,
    imageAlt: publicBook?.slug === LIVE_APPROVED_SLUG ? "Custom Earnalism Dracula cover artwork" : publicBook?.title,
    type: bookNotFound ? "website" : "book",
    robots: shouldNoindex ? "noindex, nofollow" : "index, follow",
    canonicalPath: publicBook?.slug ? `/book/${publicBook.slug}` : undefined,
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadStatus("loading");
    api.get(`/books/${slug}`, { signal: controller.signal }).then((r) => {
      if (isValidBookPayload(r.data)) {
        setBook(r.data);
        setLoadStatus("ready");
        return;
      }
      if (slug === LIVE_APPROVED_SLUG) {
        setBook(DRACULA_FALLBACK_BOOK);
        setLoadStatus("ready");
        return;
      }
      setBook(null);
      setLoadStatus("not_found");
    })
      .catch((err) => {
        if (err.name !== "CanceledError") {
          if ((err.response?.status === 404 || !err.response) && slug === LIVE_APPROVED_SLUG) {
            setBook(DRACULA_FALLBACK_BOOK);
            setLoadStatus("ready");
          } else {
            setBook(null);
            setLoadStatus(err.response?.status === 404 ? "not_found" : "error");
          }
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

  useEffect(() => {
    if (!loading && book?.slug === LIVE_APPROVED_SLUG) {
      trackFunnelEvent(DRACULA_CTA_EVENTS.bookView, { book: LIVE_APPROVED_SLUG });
    }
  }, [book, loading]);

  const bookLanguage = publicBook && BENGALI_RE.test(`${publicBook.title || ""} ${publicBook.description || ""} ${publicBook.short_description || ""}`) ? "bn" : "en";
  const rights = publicBook?.rights_metadata || publicBook?.rights || {};
  const bookSchemaAllowed = publicBook?.public_json_ld_enabled === true || publicBook?.slug === LIVE_APPROVED_SLUG || (
    rights?.rights_tier === "A"
    && rights?.verification_status === "approved"
    && !rights?.blocked_reason
  );
  const bookSchema = publicBook && bookSchemaAllowed ? {
    "@context": "https://schema.org",
    "@type": "Book",
    "name": publicBook.title,
    ...(publicBook.subtitle ? { "alternativeHeadline": publicBook.subtitle } : {}),
    "description": publicBook.description || publicBook.short_description,
    ...(publicBook.cover_image_url ? { "image": publicBook.cover_image_url } : {}),
    "bookFormat": "https://schema.org/EBook",
    "inLanguage": bookLanguage,
    "author": { "@type": publicBook.author && publicBook.author !== "The Earnalism" ? "Person" : "Organization", "name": publicBook.author || "The Earnalism" },
    "publisher": { "@type": "Organization", "name": "The Earnalism" },
    "url": `${SITE_URL}/book/${publicBook.slug}`,
    "mainEntityOfPage": `${SITE_URL}/book/${publicBook.slug}`,
    "numberOfPages": publicBook.page_count || undefined,
    ...(publicBook.slug === LIVE_APPROVED_SLUG ? {
      "genre": "Gothic fiction",
      "isAccessibleForFree": true,
      "copyrightYear": 1897,
    } : { "isAccessibleForFree": true }),
  } : null;

  if (loading) return (
    <div className="book-detail-skeleton max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20" role="status" aria-live="polite" data-testid="book-loading">
      <div className="book-detail-skeleton__cover" />
      <div className="book-detail-skeleton__copy">
        <span />
        <strong />
        <p />
        <p />
      </div>
      <span className="sr-only">Preparing the Earnalism book room.</span>
    </div>
  );
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

  const isDracula = publicBook.slug === LIVE_APPROVED_SLUG;
  const chapterCount = isDracula ? DRACULA_CHAPTER_COUNT : (publicBook.chapters || []).length;
  const hasExplicitPreview = (publicBook.chapters || []).some((chapter) => chapter.is_preview === true);
  const hasFreePreview = hasExplicitPreview || chapterCount > 1;
  const readerHref = `/reader/${publicBook.slug}`;
  const passHref = isDracula ? readingPassUrl("book_detail") : "";
  const detailPresentation = bookDetailPresentationForBook(publicBook);

  return (
    <div className="book-detail-page" data-testid="book-page">
      {bookSchemaAllowed && bookSchema && <JsonLd id="book" data={bookSchema} />}
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-10">
        <Link to="/library" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-to-library">
          <ChevronLeft size={14} /> Back to Library
        </Link>
      </div>

      <section className="book-detail-hero max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
        <div className="lg:col-span-5 lg:sticky lg:top-28">
          <div className="book-detail-cover-frame aspect-[3/4] overflow-hidden max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none">
            <BookCoverImage
              book={publicBook}
              alt={isDracula ? "Custom Earnalism Dracula cover artwork" : publicBook.title}
              loading="eager"
              fetchPriority="high"
              width={640}
              widths={[420, 640, 900]}
              sizes="(min-width: 1024px) 420px, (min-width: 640px) 52vw, 90vw"
            />
          </div>
          <div className="mt-5 max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none">
            <div className="overline mb-2">Back cover</div>
            <div className="aspect-[3/4] rounded-lg overflow-hidden border border-brand-soft bg-ivory-warm">
              <BookCoverImage
                book={publicBook}
                kind="back"
                alt={`${publicBook.title} back cover`}
                loading="lazy"
                width={640}
                widths={[420, 640, 900]}
                sizes="(min-width: 1024px) 420px, (min-width: 640px) 52vw, 90vw"
              />
            </div>
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="overline mb-5">{publicBook.category_slug?.replace(/-/g, ' ')}</div>
          <h1 className={detailPresentation.titleClassName}>{publicBook.title}</h1>
          {publicBook.author && <p className="text-[0.85rem] tracking-[0.14em] uppercase text-charcoal-soft mt-4">by {publicBook.author}</p>}
          {publicBook.subtitle && <p className="font-serif-display italic text-lg sm:text-[1.32rem] text-burgundy-soft mt-5 leading-snug">{publicBook.subtitle}</p>}
          <div className="book-detail-status-row" data-testid="book-detail-status">
            <span data-testid="book-detail-reader-status">{detailPresentation.readerStateLabel}</span>
            <span data-testid="book-detail-audio-status">{detailPresentation.audioBadgeLabel}</span>
            <span data-testid="book-detail-language-status">{detailPresentation.languageLabel}</span>
          </div>
          <div className="gold-rule-thin mt-8" />
          <p className="text-charcoal-soft mt-7 leading-[1.85] font-light">{publicBook.description}</p>

          {isDracula && (
            <div id="rights-note" className="mt-8 rounded-lg border border-brand-soft bg-ivory-warm p-5 sm:p-6" data-testid="dracula-rights-note">
              <div className="italic-eyebrow mb-3">Controlled release note</div>
              <div className="grid gap-4 text-sm leading-relaxed text-charcoal-soft sm:grid-cols-2">
                <p><strong className="text-burgundy">Source:</strong> {DRACULA_SOURCE_NOTE}</p>
                <p><strong className="text-burgundy">Rights status:</strong> {DRACULA_RIGHTS_NOTE}</p>
                <p><strong className="text-burgundy">First published:</strong> 1897</p>
                <p><strong className="text-burgundy">Audio:</strong> Audiobook experience in private review</p>
              </div>
            </div>
          )}

          {/* Reader meta row */}
          <div className="flex items-center gap-8 mt-8 flex-wrap" data-testid="book-meta">
            {chapterCount > 0 && (
              <div className="flex items-center gap-2 text-charcoal">
                <BookOpen size={16} className="text-gold" strokeWidth={1.5} />
                <span className="text-[0.9rem]"><span className="font-serif-display italic">{chapterCount}</span> {chapterCount === 1 ? "chapter" : "chapters"}</span>
              </div>
            )}
            {publicBook.estimated_reading_time && (
              <div className="flex items-center gap-2 text-charcoal">
                <Clock size={16} className="text-gold" strokeWidth={1.5} />
                <span className="text-[0.9rem]">About <span className="font-serif-display italic">{publicBook.estimated_reading_time}</span></span>
              </div>
            )}
          </div>

          {/* CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row gap-3 flex-wrap items-stretch sm:items-center" data-testid="book-actions">
            {isDracula && hasFreePreview && (
              <Link to={readerHref} className="btn-secondary justify-center" data-testid="read-preview" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.previewStart, { book: publicBook.slug, cta: "book_detail_preview" })}>Read Chapter 1 Free</Link>
            )}
            <Link to={readerHref} className="btn-primary justify-center" data-testid="start-reading" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.startReading, { book: publicBook.slug, cta: isDracula ? "book_detail_continue" : "book_detail_reader" })}>
              {isDracula ? "Continue Dracula" : detailPresentation.primaryReadLabel}
            </Link>
            {isDracula && (
              <Link to={passHref} className="btn-link justify-center" data-testid="book-reading-pass" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.readingPass, { book: publicBook.slug, cta: "book_detail_pass" })}>Get 7-Day Reading Pass</Link>
            )}
            {detailPresentation.listenCtaVisible && (
              <Link to={`${readerHref}?listen=1`} className="btn-secondary justify-center" data-testid="book-listen-approved">
                <Headphones size={15} strokeWidth={1.6} /> {detailPresentation.listenCtaLabel}
              </Link>
            )}
          </div>

          <div className="book-experience-panel mt-8" data-testid="book-experience-truth">
            <div className="book-experience-panel__item">
              <BookOpen size={18} strokeWidth={1.55} aria-hidden="true" />
              <div>
                <strong>{isDracula ? "Preview opens first" : "Reader edition ready"}</strong>
                <p>{isDracula ? "Chapter 1 opens free so you can feel the room before adding reading time." : detailPresentation.readerBody}</p>
              </div>
            </div>
            <div className="book-experience-panel__item">
              <Headphones size={18} strokeWidth={1.55} aria-hidden="true" />
              <div>
                <strong data-testid="book-detail-audio-heading">{detailPresentation.audioHeading}</strong>
                <p>{detailPresentation.audioBody}</p>
                {detailPresentation.syncCopy && (
                  <p className="book-experience-panel__sync" data-testid="book-detail-sync-copy">{detailPresentation.syncCopy}</p>
                )}
              </div>
            </div>
            <div className="book-experience-panel__item">
              <ShieldCheck size={18} strokeWidth={1.55} aria-hidden="true" />
              <div>
                <strong>Release truth preserved</strong>
                <p>Reader, cover, rights, and audio states follow production metadata instead of marketing claims.</p>
              </div>
            </div>
          </div>

          <div className="mt-8" data-testid="book-share">
            <ShareButtons title={publicBook.title} variant="product" testIdPrefix="book-share" />
          </div>

          {/* Chapter list */}
          {chapterCount > 0 && (
            <div className="mt-14" data-testid="chapter-list">
              <div className="italic-eyebrow mb-3">Table of Contents</div>
            <h3 className="font-serif-light text-[1.48rem] sm:text-[1.68rem] text-burgundy mb-6 leading-snug">Chapters</h3>
              <ol className="space-y-3">
                {(publicBook.chapters || []).map((c, i) => (
                  <li key={c.id} className="flex items-baseline gap-4 text-charcoal">
                    <span className="italic-accent text-gold-deep shrink-0 w-10">{String(i + 1).padStart(2, "0")}</span>
                    <Link to={`/reader/${publicBook.slug}?c=${c.id}`} className="font-serif-display text-[1.15rem] hover:text-burgundy transition-colors">{normalizeChapterDisplayTitle(c.title)}</Link>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {publicBook.benefits?.length > 0 && (
            <div className="mt-14">
              <div className="italic-eyebrow mb-3">For the reader</div>
              <h3 className="font-serif-light text-[1.48rem] sm:text-[1.68rem] text-burgundy mb-6 leading-snug">What waits inside</h3>
              <ul className="space-y-4">
                {publicBook.benefits.map((b) => (
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
        {publicBook.who_for?.length > 0 && (
          <div className="card-elegant p-9 sm:p-11" data-testid="who-for">
            <div className="italic-eyebrow mb-3">Who this book is for</div>
            <h3 className="font-serif-light text-[1.48rem] text-burgundy mb-6 leading-snug">Written for the careful builder</h3>
            <ul className="space-y-4 text-charcoal-soft leading-relaxed font-light">
              {publicBook.who_for.map((w) => <li key={w} className="flex gap-3"><span className="text-gold">—</span>{w}</li>)}
            </ul>
          </div>
        )}
        {publicBook.learnings?.length > 0 && (
          <div className="card-elegant p-9 sm:p-11" data-testid="learnings">
            <div className="italic-eyebrow mb-3">What you will learn</div>
            <h3 className="font-serif-light text-[1.48rem] text-burgundy mb-6 leading-snug">A practical inheritance</h3>
            <ul className="space-y-4 text-charcoal-soft leading-relaxed font-light">
              {publicBook.learnings.map((l) => <li key={l} className="flex gap-3"><span className="text-gold">—</span>{l}</li>)}
            </ul>
          </div>
        )}
      </section>

      {publicBook.about_author && (
        <section className="max-w-3xl mx-auto px-5 sm:px-8 lg:px-12 py-16 text-center" data-testid="about-author">
          <div className="italic-eyebrow mb-4">About the author / publisher</div>
          <p className="font-serif-display italic text-lg sm:text-xl lg:text-[1.42rem] text-burgundy leading-[1.52]">{publicBook.about_author}</p>
          <div className="gold-rule mx-auto mt-8" />
        </section>
      )}

      {isDracula && (
      <section id="preview-payment" className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-6 pb-20 sm:pb-28" data-testid="preview-payment-section">
        <div className="preview-payment-shell">
          <div className="preview-payment-shell__cover" aria-hidden="true">
            <BookCoverImage
              book={publicBook}
              alt=""
              loading="lazy"
              width={320}
              widths={[240, 320, 420]}
              sizes="8rem"
            />
          </div>
            <div className="preview-payment-shell__copy">
              <div className="italic-eyebrow">Preview, then continue</div>
            <h2>Read Chapter 1 free. Add reading time only when Dracula has earned your next hour.</h2>
            <p>
              This controlled launch includes the Dracula core reader only. Reading time is credited to your wallet after payment confirmation and is spent only while you read. Audio, study guide, visual edition, ads, email, and social campaigns are not live in this release.
            </p>
            <div className="preview-payment-shell__proof">
              <span><Sparkles size={14} strokeWidth={1.5} /> No subscription</span>
              <span><Clock size={14} strokeWidth={1.5} /> Time runs only while reading</span>
            </div>
          </div>
          <div className="preview-payment-shell__actions">
            <Link to={`/reader/${publicBook.slug}`} className="btn-secondary w-full justify-center" data-testid="bottom-read-preview">
              <BookOpen size={15} strokeWidth={1.6} /> Read Chapter 1 Free
            </Link>
            <Link to={readingPassUrl("book_preview")} className="btn-primary w-full justify-center" data-testid="bottom-buy-reading-time">
              <CreditCard size={15} strokeWidth={1.6} /> Get Reading Pass
            </Link>
            {publicBook.buy_url && (
              <a href={publicBook.buy_url} target="_blank" rel="noreferrer" className="preview-payment-shell__external" data-testid="bottom-external-buy">
                Publisher checkout
              </a>
            )}
          </div>
        </div>
      </section>
      )}
    </div>
  );
}
