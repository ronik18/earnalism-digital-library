import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { BookOpen, Headphones, Search, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import BookCard from "../components/BookCard";
import BookCoverImage from "../components/BookCoverImage";
import {
  DRACULA_CHAPTER_COUNT,
  DRACULA_CTA_EVENTS,
  DRACULA_RIGHTS_NOTE,
  DRACULA_SOURCE_NOTE,
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
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get("q") || "");
  const cat = params.get("category") || "all";
  const liveBook = mergeDraculaBook(dracula);

  useSEO({
    title: "Library | Dracula Is Live on Earnalism",
    description:
      "The Earnalism library is in controlled launch: Dracula is the only live approved core reading release. Future classics are shown as Coming Soon until rights and QA are complete.",
    image: liveBook.cover_image_url,
    imageAlt: "Dracula on Earnalism",
    canonicalPath: cat === "all" ? "/library" : `/library?category=${cat}`,
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api.get(`/books/${LIVE_APPROVED_SLUG}`, { signal: controller.signal })
      .then((response) => setDracula(response.data))
      .catch(() => setDracula(null))
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
  const visiblePipeline = useMemo(() => {
    if (!normalizedQuery) return PIPELINE_BOOKS;
    return PIPELINE_BOOKS.filter((book) => `${book.title} ${book.author} ${book.category_slug}`.toLowerCase().includes(normalizedQuery));
  }, [normalizedQuery]);
  const showLive = ["all", "live"].includes(cat) && (!normalizedQuery || "dracula bram stoker gothic fiction".includes(normalizedQuery));
  const showPipeline = ["all", "pipeline"].includes(cat);
  const showReadingPaths = ["all", "reading-paths"].includes(cat);
  const showAudiobooks = ["all", "audiobooks"].includes(cat);
  const trackPipelineInterest = (event, ctaId) => {
    trackFunnelEvent(event, {
      source: "library_pipeline_shelf",
      book_slug: KSHUDHITA_PASHAN_PIPELINE.slug,
      cta_id: ctaId,
      public: false,
    });
  };

  return (
    <div data-testid="library-page">
      <section className="mx-auto max-w-7xl px-5 pb-12 pt-20 sm:px-8 sm:pb-16 sm:pt-28 lg:px-12">
        <div className="italic-eyebrow mb-4">The Library - Controlled Launch</div>
        <h1 className="font-serif-light max-w-4xl text-4xl leading-[1.03] tracking-tight text-burgundy sm:text-6xl lg:text-[4.25rem]">
          One live classic, with the next shelves moving carefully through review.
        </h1>
        <p className="mt-7 max-w-2xl text-charcoal-soft leading-[1.85] font-light">
          Dracula is the only live approved core reading release today. Other titles appear only as Coming Soon until their rights, source, QA, and publication gates pass.
        </p>
        <div className="mt-7 grid gap-3 text-sm leading-relaxed text-charcoal-soft sm:grid-cols-2">
          <div className="rounded-md border border-brand-soft bg-white/45 px-4 py-3">
            <strong className="text-burgundy">Live Controlled Release:</strong> Dracula only.
          </div>
          <div className="rounded-md border border-brand-soft bg-white/45 px-4 py-3">
            <strong className="text-burgundy">Coming Through the Rights-Safe Pipeline:</strong> future titles only. Unapproved titles show Coming Soon / Notify Me only.
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-8 sm:px-8 lg:px-12" data-testid="library-bengali-gothic-pipeline">
        <div className="rounded-lg border border-brand-soft bg-[#221017] px-6 py-7 text-[#FDFCF8] sm:px-8 sm:py-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 text-[0.64rem] uppercase tracking-[0.26em] text-[var(--brand-gold-soft)]">
                <Sparkles size={14} strokeWidth={1.6} /> Rights-Safe Pipeline
              </div>
              <h2 className="mt-3 font-serif-light text-3xl leading-tight text-[#FDFCF8] sm:text-4xl">
                {KSHUDHITA_PASHAN_PIPELINE.headline}
              </h2>
              <p className="mt-3 text-[#F4EFEA]/72 leading-[1.75] font-light">
                {KSHUDHITA_PASHAN_PIPELINE.subcopy} This candidate remains in source, rights, CC BY-SA compliance,
                pronunciation, and audio-preview planning only.
              </p>
            </div>
            <div className="flex shrink-0 flex-col gap-3 sm:flex-row">
              <Link
                to={notifyUrl(KSHUDHITA_PASHAN_PIPELINE.slug)}
                className="btn-secondary justify-center !border-[var(--brand-gold-soft)] !text-[#FDFCF8] hover:!bg-[rgba(216,185,122,0.12)]"
                data-testid="library-pipeline-notify"
                onClick={() => trackPipelineInterest("kshudhita_pashan_notify_click", "library-pipeline-notify")}
              >
                Notify Me
              </Link>
              <button
                type="button"
                className="btn-link justify-center !text-[#FDFCF8]"
                data-testid="library-pipeline-reading-circle"
                onClick={() => trackPipelineInterest("bengali_gothic_reading_circle_click", "library-pipeline-reading-circle")}
              >
                Reading Circle
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-8 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-6 border-y border-brand-soft py-6 lg:flex-row lg:items-center lg:justify-between">
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
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft" size={15} strokeWidth={1.5} />
            <input
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="Search Dracula or coming titles..."
              className="input-elegant !border-b !border-[var(--brand-border)] pl-9"
              data-testid="library-search"
            />
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
                    <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">Live Controlled Release</h2>
                  </div>
                  <span className="inline-flex items-center gap-2 text-sm text-charcoal-soft"><ShieldCheck size={16} className="text-gold" /> Dracula only</span>
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
                      <h3 className="mt-4 font-serif-display text-4xl leading-tight text-burgundy">Dracula</h3>
                      <p className="mt-2 text-[0.85rem] uppercase tracking-[0.14em] text-charcoal-soft">by Bram Stoker</p>
                      <p className="mt-6 max-w-2xl text-charcoal-soft leading-[1.85]">
                        {liveBook.short_description}
                      </p>
                      <dl className="mt-6 grid gap-3 text-sm text-charcoal-soft sm:grid-cols-2">
                        <div><dt className="overline">Status</dt><dd>Live</dd></div>
                        <div><dt className="overline">Chapters</dt><dd>{DRACULA_CHAPTER_COUNT}</dd></div>
                        <div><dt className="overline">Preview</dt><dd>Chapter 1 unlocked</dd></div>
                        <div><dt className="overline">Audio</dt><dd>Not available yet</dd></div>
                        <div><dt className="overline">Rights</dt><dd>{DRACULA_RIGHTS_NOTE}</dd></div>
                        <div><dt className="overline">Source</dt><dd>{DRACULA_SOURCE_NOTE}</dd></div>
                      </dl>
                      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                        <Link to={`/reader/${LIVE_APPROVED_SLUG}`} className="btn-secondary justify-center" data-testid="library-dracula-preview" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.previewStart, { book: LIVE_APPROVED_SLUG, cta: "library_preview" })}>
                          <BookOpen size={15} /> Read Chapter 1 Free
                        </Link>
                        <Link to={`/book/${LIVE_APPROVED_SLUG}`} className="btn-primary justify-center" data-testid="library-dracula-start" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.startReading, { book: LIVE_APPROVED_SLUG, cta: "library_start" })}>
                          Start Reading
                        </Link>
                        <Link to={readingPassUrl("library_live_shelf")} className="btn-link justify-center" data-testid="library-dracula-pass" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.readingPass, { book: LIVE_APPROVED_SLUG, cta: "library_pass" })}>
                          Get 7-Day Reading Pass
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {showPipeline && (
              <section data-testid="shelf-pipeline">
                <div className="mb-7">
                  <div className="overline mb-3">Shelf 2</div>
                  <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">Coming Through the Rights-Safe Pipeline</h2>
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
                <h2 className="font-serif-display text-3xl text-burgundy">Dracula 7-Day Reading Path</h2>
                <p className="mt-5 max-w-2xl text-charcoal-soft leading-[1.8]">The guided reading path is in draft. It is not a live product yet.</p>
                <Link to={notifyUrl("dracula-reading-path")} className="btn-secondary mt-7" data-testid="reading-path-notify" onClick={() => trackFunnelEvent(DRACULA_CTA_EVENTS.notifyMe, { future_title: "dracula-reading-path" })}>
                  <Sparkles size={15} /> Notify Me
                </Link>
              </section>
            )}

            {showAudiobooks && (
              <section className="card-elegant p-8 sm:p-10" data-testid="shelf-audiobooks">
                <div className="overline mb-3">Shelf 4</div>
                <h2 className="font-serif-display text-3xl text-burgundy">Audiobooks are not live in this launch.</h2>
                <p className="mt-5 max-w-2xl text-charcoal-soft leading-[1.8]">
                  Audio is being prepared through rights and listening QA. Dracula audiobook is not available yet, so no play buttons or waveform controls are shown.
                </p>
                <div className="mt-6 inline-flex items-center gap-2 text-sm uppercase tracking-[0.18em] text-gold-deep">
                  <Headphones size={15} /> Audio QA pending
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
      <h3 className="font-serif-light text-3xl text-burgundy">{title}</h3>
      <p className="mx-auto mt-5 max-w-md text-charcoal-soft leading-[1.8]">Try Dracula, or join the Reading Circle for future release updates.</p>
    </div>
  );
}
