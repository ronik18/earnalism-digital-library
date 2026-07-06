import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, BookOpen, Headphones, Search, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import BookCard from "../components/BookCard";
import BookCoverImage from "../components/BookCoverImage";
import ComingSoonBoard from "../components/ComingSoonBoard";
import ApprovedAudiobookSpotlight from "../components/ApprovedAudiobookSpotlight";
import {
  BATCH_1_READER_ONLY_SLUGS,
  DRACULA_CHAPTER_COUNT,
  DRACULA_CTA_EVENTS,
  DRACULA_RIGHTS_NOTE,
  KSHUDHITA_PASHAN_PIPELINE,
  LIVE_APPROVED_SLUG,
  PIPELINE_BOOKS,
  mergeDraculaBook,
  notifyUrl,
  readingPassUrl,
} from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";

const FILTERS = [
  { slug: "all", name: "All" },
  { slug: "live", name: "Live" },
  { slug: "pipeline", name: "Pipeline" },
  { slug: "reading-paths", name: "Reading Paths" },
  { slug: "audiobooks", name: "Audiobooks" },
];

export default function Library() {
  const [params, setParams] = useSearchParams();
  const [dracula, setDracula] = useState(null);
  const [liveBooks, setLiveBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get("q") || "");
  const cat = params.get("category") || "all";
  const liveBook = mergeDraculaBook(dracula || liveBooks.find((book) => book.slug === LIVE_APPROVED_SLUG));

  useSEO({
    title: "Library | Controlled Reader Releases on Earnalism",
    description:
      "The Earnalism library is in controlled launch: Dracula remains the featured release, with validated reader-only public-domain classics opened only after source, sanitation, and QA gates pass.",
    image: liveBook.cover_image_url,
    imageAlt: "Dracula on Earnalism",
    canonicalPath: cat === "all" ? "/library" : `/library?category=${cat}`,
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.allSettled([
      api.get(`/books/${LIVE_APPROVED_SLUG}`, { signal: controller.signal }),
      api.get("/books", { signal: controller.signal }),
    ])
      .then(([draculaResult, booksResult]) => {
        setDracula(draculaResult.status === "fulfilled" ? draculaResult.value.data : null);
        setLiveBooks(booksResult.status === "fulfilled" && Array.isArray(booksResult.value.data) ? booksResult.value.data : []);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const setCat = (slug) => {
    const next = new URLSearchParams(params);
    if (slug === "all") next.delete("category");
    else next.set("category", slug);
    setParams(next);
  };

  const normalizedQuery = q.trim().toLowerCase();
  const kshudhitaBook = PIPELINE_BOOKS.find((book) => book.slug === KSHUDHITA_PASHAN_PIPELINE.slug);
  const liveReaderBooks = useMemo(() => {
    const bySlug = new Map();
    for (const book of liveBooks) {
      if (!book?.slug) continue;
      bySlug.set(book.slug, book.slug === LIVE_APPROVED_SLUG ? mergeDraculaBook(book) : book);
    }
    bySlug.set(LIVE_APPROVED_SLUG, liveBook);
    return Array.from(bySlug.values()).filter((book) => book?.publication_status === "LIVE_APPROVED" || book?.slug === LIVE_APPROVED_SLUG);
  }, [liveBooks, liveBook]);
  const matchesQuery = (book) => {
    if (!normalizedQuery) return true;
    return `${book.title || ""} ${book.title_en || ""} ${book.author || ""} ${book.category_slug || ""} ${book.short_description || ""}`
      .toLowerCase()
      .includes(normalizedQuery);
  };
  const otherLiveBooks = liveReaderBooks.filter((book) => book.slug !== LIVE_APPROVED_SLUG && matchesQuery(book));
  const visiblePipeline = useMemo(() => {
    const pipelineOnlyBooks = PIPELINE_BOOKS.filter((book) => !BATCH_1_READER_ONLY_SLUGS.includes(book.slug));
    if (!normalizedQuery) return pipelineOnlyBooks;
    return pipelineOnlyBooks.filter((book) => `${book.title} ${book.title_en || ""} ${book.author} ${book.category_slug} ${book.short_description || ""}`.toLowerCase().includes(normalizedQuery));
  }, [normalizedQuery]);
  const showLive = ["all", "live"].includes(cat) && liveReaderBooks.some(matchesQuery);
  const showPipeline = ["all", "pipeline"].includes(cat);
  const showReadingPaths = ["all", "reading-paths"].includes(cat);
  const showAudiobooks = ["all", "audiobooks"].includes(cat);
  const trackPipelineInterest = (event, ctaId) => {
    void event;
    void ctaId;
  };

  return (
    <div className="library-room-page" data-testid="library-page">
      <section
        className="library-room-hero relative isolate overflow-hidden text-[#FDFCF8]"
        data-testid="library-hero"
      >
        <div className="mx-auto grid max-w-7xl gap-9 px-5 py-10 sm:px-8 sm:py-14 lg:grid-cols-12 lg:items-center lg:px-12 lg:py-16">
          <div className="lg:col-span-7">
            <div className="italic-eyebrow mb-4 flex items-center gap-3 text-[var(--brand-gold-soft)]">
              <span className="h-px w-8 bg-[var(--brand-gold)]/70" />
              <span>The Earnalism Library</span>
            </div>
            <h1 className="font-serif-light max-w-3xl text-[2.2rem] leading-[1.02] tracking-normal sm:text-[3.15rem] lg:text-[3.85rem]">
              The live shelf begins with <span className="italic-accent text-[var(--brand-gold-soft)]">Dracula.</span>
            </h1>
            <p className="mt-4 max-w-2xl font-serif-display text-[1.04rem] italic leading-snug text-[#F4EFEA]/88 sm:text-[1.35rem]">
              A controlled reading room: Dracula remains the featured release, and every additional classic opens only after source, sanitation, and reader QA gates pass.
            </p>
            <p className="mt-5 max-w-2xl text-sm font-light leading-[1.8] text-[#F4EFEA]/76 sm:text-base">
              Chapter 1 opens free. Reading continuation uses reading time, not a public audiobook claim or a broad catalog promise.
            </p>
            <div className="library-hero-facts mt-6" aria-label="Library launch facts">
              <span><ShieldCheck size={14} strokeWidth={1.6} /> Approved classic reading release</span>
              <span><BookOpen size={14} strokeWidth={1.6} /> Chapter 1 free</span>
              <span><Sparkles size={14} strokeWidth={1.6} /> Public-domain source verified</span>
              <span><Headphones size={14} strokeWidth={1.6} /> Audiobook experience in private review</span>
            </div>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link
                to={`/reader/${LIVE_APPROVED_SLUG}`}
                className="btn-primary justify-center"
                data-testid="library-hero-read"
                onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.previewStart, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_hero_read" })}
              >
                <BookOpen size={15} /> Read Chapter 1 Free
              </Link>
              <Link
                to={`/book/${LIVE_APPROVED_SLUG}`}
                className="btn-secondary justify-center !border-[var(--brand-gold)] !text-[#FDFCF8] hover:!bg-[rgba(216,185,122,0.12)]"
                data-testid="library-hero-start"
                onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.startReading, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_hero_start" })}
              >
                Start Dracula
              </Link>
              <Link
                to={readingPassUrl("library_hero")}
                className="btn-link justify-center !text-[#FDFCF8]"
                data-testid="library-hero-pass"
                onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.readingPass, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_hero_pass" })}
              >
                Get 7-Day Reading Pass <ArrowRight size={15} />
              </Link>
            </div>
            <p className="mt-4 font-serif-display text-base italic text-[#F4EFEA]/70">
              Reading time is used only while you read.
            </p>
          </div>

          <div className="lg:col-span-5">
            <div className="library-hero-book-object mx-auto max-w-[360px]" data-testid="library-hero-dracula-object">
              <div className="library-hero-cover-frame mx-auto aspect-[500/696] max-w-[245px] overflow-hidden">
                <BookCoverImage
                  book={liveBook}
                  alt="Custom Earnalism Dracula cover artwork"
                  loading="eager"
                  fetchPriority="high"
                  width={520}
                  widths={[360, 520, 720]}
                  sizes="(min-width: 1024px) 245px, 58vw"
                  imgClassName="premium-dracula-cover-img"
                />
              </div>
              <div className="mt-5 text-center">
                <div className="text-[0.62rem] uppercase tracking-[0.22em] text-[var(--brand-gold-soft)]">Featured controlled reading release</div>
                <h2 className="mt-2 font-serif-display text-[2rem] text-[#FDFCF8]">Dracula</h2>
                <p className="mx-auto mt-3 max-w-xs text-[0.82rem] leading-relaxed text-[#F4EFEA]/72">
                  {DRACULA_CHAPTER_COUNT} chapters. Chapter 1 free. Public audio remains blocked.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ComingSoonBoard compact />

      <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-12 lg:px-12" data-testid="library-bengali-gothic-pipeline">
        <div className="library-pipeline-feature">
          <div className="library-pipeline-feature__covers" data-testid="library-kshudhita-cover-evidence">
            {kshudhitaBook ? (
              <div className="library-kshudhita-stack" data-cover-status={kshudhitaBook.cover_status}>
                <img
                  src={KSHUDHITA_PASHAN_PIPELINE.backCoverImage}
                  alt=""
                  className="library-kshudhita-stack__back"
                  loading="lazy"
                  width="1024"
                  height="1536"
                  aria-hidden="true"
                />
                <img
                  src={KSHUDHITA_PASHAN_PIPELINE.frontCoverImage}
                  alt="Owner-provided Kshudhita Pashan front cover artwork"
                  className="library-kshudhita-stack__front"
                  loading="lazy"
                  width="1024"
                  height="1536"
                />
              </div>
            ) : (
              <div className="library-pipeline-feature__placeholder">Pipeline cover pending</div>
            )}
          </div>
          <div className="library-pipeline-feature__copy">
            <div className="inline-flex items-center gap-2 text-[0.64rem] uppercase tracking-[0.26em] text-[var(--brand-gold-deep)]">
              <Sparkles size={14} strokeWidth={1.6} /> Rights-safe pipeline
            </div>
            <h2 className="mt-3 font-serif-light text-[1.85rem] leading-tight text-burgundy sm:text-[2.35rem]">
              The Hungry Stones is visible, not open.
            </h2>
            <p className="mt-2 text-sm uppercase tracking-[0.18em] text-charcoal-soft">
              Bengali title: {KSHUDHITA_PASHAN_PIPELINE.titleBn}
            </p>
            <p className="mt-4 max-w-2xl text-charcoal-soft leading-[1.8] font-light">
              {KSHUDHITA_PASHAN_PIPELINE.subcopy} The real front and back covers are shown as owner-provided pipeline evidence, while source, rights, CC BY-SA compliance, pronunciation, and QA gates stay closed.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link
                to={notifyUrl(KSHUDHITA_PASHAN_PIPELINE.slug)}
                className="btn-secondary justify-center"
                data-testid="library-pipeline-notify"
                onClick={() => trackPipelineInterest("kshudhita_pashan_notify_click", "library-pipeline-notify")}
              >
                Notify Me
              </Link>
              <button
                type="button"
                className="btn-link justify-center"
                data-testid="library-pipeline-reading-circle"
                onClick={() => trackPipelineInterest("bengali_gothic_reading_circle_click", "library-pipeline-reading-circle")}
              >
                Reading Circle
              </button>
            </div>
            <div className="mt-5 text-xs leading-relaxed text-charcoal-soft">
              No reader, payment, or audio CTA is available for this pipeline-only title.
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-8 sm:px-8 lg:px-12">
        <div className="library-shelf-toolbar flex flex-col gap-6 py-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2" data-testid="category-filters">
            {FILTERS.map((filter) => (
              <button
                key={filter.slug}
                onClick={() => setCat(filter.slug)}
                data-testid={`filter-${filter.slug}`}
                className={`rounded-full px-4 py-2 text-[0.68rem] uppercase tracking-[0.24em] transition-colors ${cat === filter.slug ? "bg-burgundy text-[var(--brand-ivory)]" : "border border-transparent text-charcoal-soft hover:border-[var(--brand-gold)]/40 hover:text-burgundy"}`}
              >
                {filter.name}
              </button>
            ))}
          </div>
          <label className="relative block w-full max-w-sm">
            <span className="sr-only">Search Dracula or coming titles</span>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft" size={15} strokeWidth={1.5} />
            <input
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="Search Dracula or coming titles..."
              className="input-elegant !border-b !border-[var(--brand-border)] pl-9"
              data-testid="library-search"
              aria-label="Search Dracula or coming titles"
            />
          </label>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-28 sm:px-8 lg:px-12">
        {loading ? (
          <div className="card-elegant p-12 text-center text-charcoal-soft">Loading the controlled shelf...</div>
        ) : (
          <div className="space-y-16">
            {showLive && (
              <section data-testid="shelf-live-controlled-release">
                <div className="mb-7 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="overline mb-3">Shelf 1</div>
                    <h2 className="font-serif-light text-[1.85rem] leading-tight text-burgundy sm:text-[2.35rem]">Live Controlled Releases</h2>
                  </div>
                  <span className="inline-flex items-center gap-2 text-sm text-charcoal-soft"><ShieldCheck size={16} className="text-gold" /> Reader-only public-domain shelf</span>
                </div>
                <div className="card-elegant overflow-hidden">
                  <div className="grid grid-cols-1 gap-8 p-7 sm:p-9 lg:grid-cols-12 lg:items-center">
                    <div className="lg:col-span-4">
                      <div className="mx-auto aspect-[3/4] max-w-[260px] overflow-hidden rounded-lg border border-brand-soft bg-ivory-warm">
                        <BookCoverImage book={liveBook} alt="Dracula by Bram Stoker cover" loading="eager" width={420} widths={[300, 420, 640]} sizes="260px" />
                      </div>
                    </div>
                    <div className="lg:col-span-8">
                      <span className="overline">Gothic fiction</span>
                      <h3 className="mt-4 font-serif-display text-[2.15rem] leading-tight text-burgundy">Dracula</h3>
                      <p className="mt-2 text-[0.85rem] uppercase tracking-[0.14em] text-charcoal-soft">by Bram Stoker</p>
                      <p className="mt-6 max-w-2xl text-charcoal-soft leading-[1.85]">
                        {liveBook.short_description}
                      </p>
                      <dl className="mt-6 grid gap-3 text-sm text-charcoal-soft sm:grid-cols-2">
                        <div><dt className="overline">Status</dt><dd>Live</dd></div>
                        <div><dt className="overline">Chapters</dt><dd>{DRACULA_CHAPTER_COUNT}</dd></div>
                        <div><dt className="overline">Preview</dt><dd>Chapter 1 unlocked</dd></div>
                        <div><dt className="overline">Audio</dt><dd>Audiobook experience in private review</dd></div>
                        <div><dt className="overline">Rights</dt><dd>{DRACULA_RIGHTS_NOTE}</dd></div>
                        <div><dt className="overline">Source</dt><dd>Public-domain source verified</dd></div>
                      </dl>
                      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                        <Link to={`/reader/${LIVE_APPROVED_SLUG}`} className="btn-secondary justify-center" data-testid="library-dracula-preview" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.previewStart, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_preview" })}>
                          <BookOpen size={15} /> Read Chapter 1 Free
                        </Link>
                        <Link to={`/book/${LIVE_APPROVED_SLUG}`} className="btn-primary justify-center" data-testid="library-dracula-start" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.startReading, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_start" })}>
                          Start Dracula
                        </Link>
                        <Link to={readingPassUrl("library_live_shelf")} className="btn-link justify-center" data-testid="library-dracula-pass" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.readingPass, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_pass" })}>
                          Get 7-Day Reading Pass
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
                {otherLiveBooks.length > 0 && (
                  <div className="mt-8 grid grid-cols-1 gap-7 sm:grid-cols-2 lg:grid-cols-4" data-testid="library-live-reader-only-grid">
                    {otherLiveBooks.map((book) => (
                      <BookCard key={book.slug} book={book} />
                    ))}
                  </div>
                )}
              </section>
            )}

            {showPipeline && (
              <section data-testid="shelf-pipeline">
                <div className="mb-7">
                  <div className="overline mb-3">Shelf 2</div>
                  <h2 className="font-serif-light text-[1.85rem] leading-tight text-burgundy sm:text-[2.35rem]">Coming Through the Rights-Safe Pipeline</h2>
                  <p className="mt-4 max-w-2xl text-charcoal-soft leading-[1.8]">These books are not live products yet. They have Notify Me CTAs only.</p>
                </div>
                {visiblePipeline.length > 0 ? (
                  <div className="grid grid-cols-1 gap-7 sm:grid-cols-2 lg:grid-cols-4">
                    {visiblePipeline.map((book) => <BookCard key={book.slug} book={book} />)}
                  </div>
                ) : (
                  <EmptyShelf title="No pipeline title matches this search." />
                )}
              </section>
            )}

            {showReadingPaths && (
              <section className="card-elegant p-8 sm:p-10" data-testid="shelf-reading-paths">
                <div className="overline mb-3">Shelf 3</div>
                <h2 className="font-serif-display text-[1.85rem] text-burgundy">Dracula 7-Day Reading Path</h2>
                <p className="mt-5 max-w-2xl text-charcoal-soft leading-[1.8]">The guided reading path is in draft. It is not a live product yet.</p>
                <Link to={notifyUrl("dracula-reading-path")} className="btn-secondary mt-7" data-testid="reading-path-notify" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.notifyMe, { future_title: "dracula-reading-path" })}>
                  <Sparkles size={15} /> Notify Me
                </Link>
              </section>
            )}

            {showAudiobooks && (
              <section data-testid="shelf-audiobooks">
                <ApprovedAudiobookSpotlight compact />
                <div className="card-elegant p-8 sm:p-10">
                  <div className="overline mb-3">Shelf 4</div>
                  <h2 className="font-serif-display text-[1.85rem] text-burgundy">Audiobooks appear only after proof.</h2>
                  <p className="mt-5 max-w-2xl text-charcoal-soft leading-[1.8]">
                    If an approved listening room is available, it is shown above from the production reader manifest. Every other audiobook remains hidden through rights, sync, accessibility, and listening QA.
                  </p>
                  <div className="mt-6 inline-flex items-center gap-2 text-sm uppercase tracking-[0.18em] text-gold-deep">
                    <Headphones size={15} /> Release-gate controlled
                  </div>
                </div>
              </section>
            )}

            {!showLive && !showPipeline && !showReadingPaths && !showAudiobooks && (
              <EmptyShelf title="This shelf is not live yet." />
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function EmptyShelf({ title }) {
  return (
    <div className="card-elegant p-12 text-center" data-testid="library-empty">
      <div className="italic-eyebrow mb-4">Controlled shelf</div>
      <h3 className="font-serif-light text-[1.85rem] text-burgundy">{title}</h3>
      <p className="mx-auto mt-5 max-w-md text-charcoal-soft leading-[1.8]">Try Dracula, or join the Reading Circle for future release updates.</p>
    </div>
  );
}
