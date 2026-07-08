import { useCallback, useEffect, useMemo, useState } from "react";
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
import { languageOfBook, matchesLibraryFacets, sortLibraryBooks } from "../lib/libraryCatalog";
import { LOCAL_LIBRARY_FALLBACK_BOOKS } from "../lib/libraryFallbackBooks";
import useSEO from "../hooks/useSEO";

const FILTERS = [
  { slug: "all", name: "All" },
  { slug: "live", name: "Live" },
  { slug: "pipeline", name: "Pipeline" },
  { slug: "reading-paths", name: "Reading Paths" },
  { slug: "audiobooks", name: "Audiobooks" },
];

const LANGUAGE_FILTERS = [
  { slug: "all", name: "All" },
  { slug: "bn", name: "Bengali" },
  { slug: "en", name: "English" },
];

const AVAILABILITY_FILTERS = [
  { slug: "all", name: "All" },
  { slug: "reader-ready", name: "Reader Ready" },
  { slug: "approved-audiobook", name: "Approved Audiobook" },
  { slug: "audio-hidden", name: "Audio Hidden" },
  { slug: "in-preparation", name: "In Preparation" },
];

const SORT_OPTIONS = [
  { slug: "recently-approved", name: "Recently approved" },
  { slug: "title", name: "Title" },
  { slug: "author", name: "Author" },
  { slug: "short-reads", name: "Short reads" },
];

const VIEW_MODES = [
  { slug: "shelf", name: "Shelf" },
  { slug: "grid", name: "Grid" },
  { slug: "compact", name: "Compact" },
];

export default function Library() {
  const [params, setParams] = useSearchParams();
  const [dracula, setDracula] = useState(null);
  const [liveBooks, setLiveBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get("q") || "");
  const cat = params.get("category") || "all";
  const language = params.get("language") || "all";
  const availability = params.get("availability") || "all";
  const sort = params.get("sort") || "recently-approved";
  const view = params.get("view") || "shelf";
  const liveBook = mergeDraculaBook(dracula || liveBooks.find((book) => book.slug === LIVE_APPROVED_SLUG));

  useSEO({
    title: "Library | Bengali and English Classics on Earnalism",
    description:
      "Browse Earnalism's Bengali and English classics. Reader-only releases stay visible, and audiobooks appear only after source, listening, sync, and browser gates pass.",
    image: liveBook.cover_image_url,
    imageAlt: "Earnalism graphical book cover artwork",
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
        setLiveBooks(
          booksResult.status === "fulfilled" && Array.isArray(booksResult.value.data) && booksResult.value.data.length > 0
            ? booksResult.value.data
            : LOCAL_LIBRARY_FALLBACK_BOOKS,
        );
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

  const setFacet = (key, value, fallback = "all") => {
    const next = new URLSearchParams(params);
    if (value === fallback) next.delete(key);
    else next.set(key, value);
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
  const matchesQuery = useCallback((book) => {
    if (!normalizedQuery) return true;
    return `${book.title || ""} ${book.title_en || ""} ${book.author || ""} ${book.category_slug || ""} ${book.short_description || ""}`
      .toLowerCase()
      .includes(normalizedQuery);
  }, [normalizedQuery]);
  const filteredLiveReaderBooks = useMemo(
    () => sortLibraryBooks(
      liveReaderBooks.filter((book) => matchesQuery(book) && matchesLibraryFacets(book, language, availability)),
      sort,
    ),
    [availability, language, liveReaderBooks, matchesQuery, sort],
  );
  const showFeaturedEnglishClassic = filteredLiveReaderBooks.some((book) => book.slug === LIVE_APPROVED_SLUG);
  const bengaliLiveBooks = filteredLiveReaderBooks.filter((book) => languageOfBook(book) === "bn");
  const englishLiveBooks = filteredLiveReaderBooks.filter((book) => languageOfBook(book) === "en" && book.slug !== LIVE_APPROVED_SLUG);
  const visiblePipeline = useMemo(() => {
    const pipelineOnlyBooks = PIPELINE_BOOKS.filter((book) => !BATCH_1_READER_ONLY_SLUGS.includes(book.slug));
    const filtered = pipelineOnlyBooks.filter((book) => {
      const queryMatches = !normalizedQuery || `${book.title} ${book.title_en || ""} ${book.author} ${book.category_slug} ${book.short_description || ""}`.toLowerCase().includes(normalizedQuery);
      return queryMatches && matchesLibraryFacets(book, language, availability);
    });
    return sortLibraryBooks(filtered, sort);
  }, [availability, language, normalizedQuery, sort]);
  const showLive = ["all", "live"].includes(cat) && filteredLiveReaderBooks.length > 0;
  const showPipeline = ["all", "pipeline"].includes(cat) && (visiblePipeline.length > 0 || cat === "pipeline");
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
            <h1 className="font-serif-light max-w-3xl text-[2.04rem] leading-[1.04] tracking-normal sm:text-[2.86rem] lg:text-[3.42rem]">
              Bengali and English classics, opened with release truth.
            </h1>
            <p className="mt-4 max-w-2xl font-serif-display text-[0.98rem] italic leading-snug text-[#F4EFEA]/88 sm:text-[1.18rem]">
              A calm catalog where reader-only classics feel intentional and audiobooks appear only after source, listening, sync, and browser gates pass.
            </p>
            <p className="mt-5 max-w-2xl text-sm font-light leading-[1.8] text-[#F4EFEA]/76 sm:text-base">
              Explore Bengali shelves, English classics, and release-gated listening without broad catalog or audio overclaim.
            </p>
            <div className="library-hero-facts mt-6" aria-label="Library launch facts">
              <span><ShieldCheck size={14} strokeWidth={1.6} /> Reader-only releases protected</span>
              <span><BookOpen size={14} strokeWidth={1.6} /> Bengali + English shelves</span>
              <span><Sparkles size={14} strokeWidth={1.6} /> Public-domain source verified</span>
              <span><Headphones size={14} strokeWidth={1.6} /> Audiobooks gated by evidence</span>
            </div>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link
                to="/library?language=bn&availability=reader-ready"
                className="btn-primary justify-center"
                data-testid="library-hero-bengali"
                onClick={() => trackFunnelEvent("bengali_card_click", { cta: "library_hero_bengali" })}
              >
                <BookOpen size={15} /> Explore Bengali Classics
              </Link>
              <Link
                to="/library?language=en"
                className="btn-secondary justify-center !border-[var(--brand-gold)] !text-[#FDFCF8] hover:!bg-[rgba(216,185,122,0.12)]"
                data-testid="library-hero-english"
                onClick={() => trackFunnelEvent("english_card_click", { cta: "library_hero_english" })}
              >
                Browse English Classics
              </Link>
              <Link
                to="/library?availability=approved-audiobook"
                className="btn-link justify-center !text-[#FDFCF8]"
                data-testid="library-hero-approved-audio"
                onClick={() => trackFunnelEvent("approved_audio_card_click", { cta: "library_hero_audio" })}
              >
                Approved Audio Only <ArrowRight size={15} />
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
                <div className="text-[0.62rem] uppercase tracking-[0.22em] text-[var(--brand-gold-soft)]">English classics tile</div>
                <h2 className="mt-2 font-serif-display text-[1.72rem] text-[#FDFCF8]">Dracula</h2>
                <p className="mx-auto mt-3 max-w-xs text-[0.82rem] leading-relaxed text-[#F4EFEA]/72">
                  {DRACULA_CHAPTER_COUNT} chapters. A refined English reading route, not the whole library identity.
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
            <h2 className="mt-3 font-serif-light text-[1.68rem] leading-tight text-burgundy sm:text-[2.12rem]">
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
        <div className="library-discovery-panel" data-testid="library-discovery-controls">
          <div className="library-discovery-panel__header">
            <div>
              <div className="overline mb-2">Catalog controls</div>
              <h2>Browse by language, availability, and reading intent.</h2>
            </div>
            <label className="library-search-field">
              <span className="sr-only">Search title, author, language, or status</span>
              <Search className="library-search-field__icon" size={15} strokeWidth={1.5} aria-hidden="true" />
              <input
                value={q}
                onChange={(event) => setQ(event.target.value)}
                placeholder="Search title, author, language..."
                className="input-elegant !border-b !border-[var(--brand-border)] pl-9"
                data-testid="library-search"
                aria-label="Search title, author, language, or status"
              />
            </label>
          </div>

          <div className="library-discovery-grid">
            <div className="library-filter-group" data-testid="category-filters">
              <span>Section</span>
              <div className="library-chip-row">
                {FILTERS.map((filter) => (
                  <button
                    key={filter.slug}
                    type="button"
                    onClick={() => setCat(filter.slug)}
                    data-testid={`filter-${filter.slug}`}
                    aria-pressed={cat === filter.slug}
                  >
                    {filter.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="library-filter-group" data-testid="language-filters">
              <span>Language</span>
              <div className="library-chip-row">
                {LANGUAGE_FILTERS.map((filter) => (
                  <button
                    key={filter.slug}
                    type="button"
                    onClick={() => setFacet("language", filter.slug)}
                    data-testid={`filter-language-${filter.slug}`}
                    aria-pressed={language === filter.slug}
                  >
                    {filter.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="library-filter-group" data-testid="availability-filters">
              <span>Availability</span>
              <div className="library-chip-row">
                {AVAILABILITY_FILTERS.map((filter) => (
                  <button
                    key={filter.slug}
                    type="button"
                    onClick={() => setFacet("availability", filter.slug)}
                    data-testid={`filter-availability-${filter.slug}`}
                    aria-pressed={availability === filter.slug}
                  >
                    {filter.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="library-filter-group library-filter-group--selects">
              <label>
                <span>Sort</span>
                <select
                  value={sort}
                  onChange={(event) => setFacet("sort", event.target.value, "recently-approved")}
                  data-testid="library-sort"
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option.slug} value={option.slug}>{option.name}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>View</span>
                <select
                  value={view}
                  onChange={(event) => setFacet("view", event.target.value, "shelf")}
                  data-testid="library-view-mode"
                >
                  {VIEW_MODES.map((option) => (
                    <option key={option.slug} value={option.slug}>{option.name}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>
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
                    <h2 className="font-serif-light text-[1.68rem] leading-tight text-burgundy sm:text-[2.12rem]">Curated Reader-Ready Shelves</h2>
                    <p className="mt-4 max-w-2xl text-charcoal-soft leading-[1.8]">
                      Bengali reader editions stay visibly premium, English classics stay editorial, and listening appears only when the approved reader manifest proves it.
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-2 text-sm text-charcoal-soft"><ShieldCheck size={16} className="text-gold" /> Reader-only public-domain shelf</span>
                </div>
                {bengaliLiveBooks.length > 0 && (
                  <div className="library-curated-shelf mb-10" data-testid="library-bengali-classics-shelf">
                    <div className="library-curated-shelf__header">
                      <div>
                        <div className="overline mb-2">Bengali classics</div>
                        <h3>Reader editions live with audio hidden until approved.</h3>
                      </div>
                      <p>
                        These books are intentionally premium reading editions. Narration remains hidden until source, listening, sync, endpoint, and browser evidence all pass.
                      </p>
                    </div>
                    <div className={`grid grid-cols-1 gap-7 sm:grid-cols-2 ${view === "compact" ? "lg:grid-cols-5" : "lg:grid-cols-4"}`} data-testid="library-bengali-reader-grid" data-view={view}>
                      {bengaliLiveBooks.map((book) => (
                        <BookCard key={book.slug} book={book} />
                      ))}
                    </div>
                  </div>
                )}
                {(showFeaturedEnglishClassic || englishLiveBooks.length > 0) && (
                  <div className="library-curated-shelf" data-testid="library-english-classics-shelf">
                    <div className="library-curated-shelf__header">
                      <div>
                        <div className="overline mb-2">English classics</div>
                        <h3>Editorial reading routes, with Dracula as one refined classic.</h3>
                      </div>
                      <p>
                        English shelves stay grounded in classic reading comfort. Dracula remains a featured route, not the whole library identity.
                      </p>
                    </div>
                    {showFeaturedEnglishClassic && (
                      <div className="card-elegant overflow-hidden">
                        <div className="grid grid-cols-1 gap-8 p-7 sm:p-9 lg:grid-cols-12 lg:items-center">
                          <div className="lg:col-span-4">
                            <div className="mx-auto aspect-[3/4] max-w-[260px] overflow-hidden rounded-lg border border-brand-soft bg-ivory-warm">
                              <BookCoverImage book={liveBook} alt="Dracula by Bram Stoker cover" loading="eager" width={420} widths={[300, 420, 640]} sizes="260px" />
                            </div>
                          </div>
                          <div className="lg:col-span-8">
                            <span className="overline">Gothic fiction</span>
                            <h3 className="mt-4 font-serif-display text-[1.86rem] leading-tight text-burgundy">Dracula</h3>
                            <p className="mt-2 text-[0.85rem] uppercase tracking-[0.14em] text-charcoal-soft">by Bram Stoker</p>
                            <p className="mt-6 max-w-2xl text-charcoal-soft leading-[1.85]">
                              {liveBook.short_description}
                            </p>
                            <dl className="mt-6 grid gap-3 text-sm text-charcoal-soft sm:grid-cols-2">
                              <div><dt className="overline">Status</dt><dd>Reader Ready</dd></div>
                              <div><dt className="overline">Chapters</dt><dd>{DRACULA_CHAPTER_COUNT}</dd></div>
                              <div><dt className="overline">Preview</dt><dd>Chapter 1 unlocked</dd></div>
                              <div><dt className="overline">Audio</dt><dd>Audio hidden until approved</dd></div>
                              <div><dt className="overline">Rights</dt><dd>{DRACULA_RIGHTS_NOTE}</dd></div>
                              <div><dt className="overline">Source</dt><dd>Public-domain source verified</dd></div>
                            </dl>
                            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                              <Link to={`/reader/${LIVE_APPROVED_SLUG}`} className="btn-secondary justify-center" data-testid="library-dracula-preview" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.previewStart, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_preview" })}>
                                <BookOpen size={15} /> Read Chapter 1 Free
                              </Link>
                              <Link to={`/book/${LIVE_APPROVED_SLUG}`} className="btn-primary justify-center" data-testid="library-dracula-start" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.startReading, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_start" })}>
                                Read English Classic
                              </Link>
                              <Link to={readingPassUrl("library_live_shelf")} className="btn-link justify-center" data-testid="library-dracula-pass" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.readingPass, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, cta: "library_pass" })}>
                                Get 7-Day Reading Pass
                              </Link>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {englishLiveBooks.length > 0 && (
                      <div className={`mt-8 grid grid-cols-1 gap-7 sm:grid-cols-2 ${view === "compact" ? "lg:grid-cols-5" : "lg:grid-cols-4"}`} data-testid="library-english-reader-grid" data-view={view}>
                        {englishLiveBooks.map((book) => (
                          <BookCard key={book.slug} book={book} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}

            {showPipeline && (
              <section data-testid="shelf-pipeline">
                <div className="mb-7">
                  <div className="overline mb-3">Shelf 2</div>
                  <h2 className="font-serif-light text-[1.68rem] leading-tight text-burgundy sm:text-[2.12rem]">Coming Through the Rights-Safe Pipeline</h2>
                  <p className="mt-4 max-w-2xl text-charcoal-soft leading-[1.8]">These books are not live products yet. They have Notify Me CTAs only.</p>
                </div>
                {visiblePipeline.length > 0 ? (
                  <div className={`grid grid-cols-1 gap-7 sm:grid-cols-2 ${view === "compact" ? "lg:grid-cols-5" : "lg:grid-cols-4"}`} data-view={view}>
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
                <h2 className="font-serif-display text-[1.68rem] text-burgundy">Guided Reading Paths</h2>
                <p className="mt-5 max-w-2xl text-charcoal-soft leading-[1.8]">Curated reading paths are in draft. They are not live products yet.</p>
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
                  <h2 className="font-serif-display text-[1.68rem] text-burgundy">Audiobooks appear only after proof.</h2>
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
      <h3 className="font-serif-light text-[1.68rem] text-burgundy">{title}</h3>
      <p className="mx-auto mt-5 max-w-md text-charcoal-soft leading-[1.8]">Try another language or availability filter, or join the Reading Circle for future release updates.</p>
    </div>
  );
}
